import re
import uuid
from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.dialects import mysql
from app.main import app
from app.database import SessionLocal
from app.crud import consultations as crud
from app.models.consultation import ConsultationChallenge, ConsultationLead, ConsultationRateBucket


@pytest.fixture
def ctx(monkeypatch):
    run = uuid.uuid4().hex
    clock = [datetime(2026, 10, 7, 2, 0, 0)]
    monkeypatch.setattr(crud, 'utcnow', lambda: clock[0])
    clients, hosts, phones = [], [], set()

    def client():
        host = 'test-' + run + '-' + str(len(clients))
        connection = TestClient(app, client=(host, 12345))
        clients.append(connection); hosts.append(host)
        return connection

    def phone():
        value = '09' + str(uuid.uuid4().int % 100000000).zfill(8)
        phones.add(value)
        return value

    context = {'client': client(), 'new_client': client, 'phones': phones, 'phone': phone, 'clock': clock, 'run': run, 'host': hosts[0]}
    yield context
    for connection in clients:
        connection.close()
    with SessionLocal() as db:
        db.query(ConsultationChallenge).filter(ConsultationChallenge.client_key.in_([crud.fingerprint('client:' + host) for host in hosts])).delete(synchronize_session=False)
        db.query(ConsultationLead).filter(ConsultationLead.phone.in_(phones)).delete(synchronize_session=False)
        keys = [crud.fingerprint(action + ':' + host) for action in ['challenge', 'submission'] for host in hosts]
        keys += [crud.fingerprint('phone:' + value) for value in phones]
        db.query(ConsultationRateBucket).filter(ConsultationRateBucket.key.in_(keys)).delete(synchronize_session=False)
        db.commit()


def advance(ctx, seconds):
    ctx['clock'][0] += timedelta(seconds=seconds)


def challenge(ctx, client=None, ready=True):
    result = (client or ctx['client']).get('/api/public/consultations/challenge')
    assert result.status_code == 200, result.text
    info = result.json()
    answer = sum(map(int, re.findall(r'\d+', info['question'])))
    if ready:
        advance(ctx, info['min_wait_seconds'])
    return info, str(answer)


def payload(ctx, proof=None, **changes):
    info, answer = proof or challenge(ctx)
    return {'full_name': '  Khách tư vấn  ', 'phone': ctx['phone'](), 'email': 'khach@example.com',
            'interest': '  Lập trình Python  ', 'message': '  Muốn học buổi tối\nCần tư vấn lộ trình  ',
            'challenge_token': info['challenge_token'], 'challenge_answer': answer, **changes}


def submit(ctx, body, client=None, **kwargs):
    return (client or ctx['client']).post('/api/public/consultations', json=body, **kwargs)


def leads(ctx):
    with SessionLocal() as db:
        return [(l.full_name,l.phone,l.email,l.interest,l.message,l.status,l.created_at)
                for l in db.query(ConsultationLead).filter(ConsultationLead.phone.in_(ctx['phones'])).order_by(ConsultationLead.lead_id)]


def test_public_submission_creates_new_lead_without_login(ctx):
    phone = ctx['phone']()
    body = payload(ctx, phone='+84' + phone[1:])
    response = submit(ctx, body, headers={'Authorization': 'Bearer invalid-does-not-require-login'})
    assert response.status_code == 201
    result = response.json()
    assert result['status'] == 'new' and result['status_label'] == 'Mới'
    assert 'Cảm ơn' in result['message'] and '1 ngày làm việc' in result['contact_promise']
    assert set(result) == {'status','status_label','message','contact_promise'}
    assert leads(ctx) == [('Khách tư vấn',phone,'khach@example.com','Lập trình Python',
                          'Muốn học buổi tối\nCần tư vấn lộ trình','new',ctx['clock'][0])]
    assert response.headers['cache-control'] == 'no-store'


def test_optional_fields_blank_and_omitted(ctx):
    body = payload(ctx, email=' ', interest=' ', message=' ')
    assert submit(ctx, body).status_code == 201
    assert leads(ctx)[0][2:5] == (None,None,None)
    body = payload(ctx)
    for field in ['email', 'interest', 'message']:
        del body[field]
    assert submit(ctx, body).status_code == 201
    assert leads(ctx)[1][2:5] == (None,None,None)


@pytest.mark.parametrize('field,value', [('full_name',' '),('full_name','A'*101),('full_name','A\nB'),('full_name',None),
    ('phone','123456789'),('phone','0123456789'),('phone','09123456789'),('phone','+84123456789'),('phone',''),('phone',None),
    ('email','not-email'),('email','a'*256+'@example.com'),('interest','A'*256),('message','A'*2001),
    ('challenge_token','short'),('challenge_token','!'+ 'A'*42),('challenge_token',None),
    ('challenge_answer','abc'),('challenge_answer','-1'),('challenge_answer','1234'),('challenge_answer',1),
    ('status','qualified'),('lead_id',1),('created_at','2020-01-01')])
def test_backend_validates_fields_and_rejects_status_injection(ctx, field, value):
    assert submit(ctx, payload(ctx, **{field:value})).status_code == 422
    assert leads(ctx) == []


def test_honeypot_blocks_bots_without_lead(ctx):
    assert submit(ctx, payload(ctx, website='https://spam.example')).status_code == 400
    assert leads(ctx) == []


def test_server_checks_minimum_fill_time(ctx):
    proof = challenge(ctx, ready=False)
    body = payload(ctx, proof)
    assert submit(ctx, body).status_code == 400 and leads(ctx) == []
    advance(ctx, crud.MIN_FILL_SECONDS)
    assert submit(ctx, body).status_code == 201


def test_expired_unknown_and_cross_client_tokens_rejected(ctx):
    body = payload(ctx)
    other = ctx['new_client']()
    assert submit(ctx, body, other).status_code == 400
    assert submit(ctx, {**body,'challenge_token':'A'*43}).status_code == 400
    advance(ctx, crud.CHALLENGE_TTL)
    assert submit(ctx, body).status_code == 400
    assert leads(ctx) == []
    assert submit(ctx, payload(ctx)).status_code == 201


def test_incorrect_answer_has_attempt_limit_persisted_in_database(ctx):
    body = payload(ctx)
    wrong = {**body,'challenge_answer':'999'}
    for _ in range(crud.MAX_ANSWER_ATTEMPTS):
        assert submit(ctx, wrong).status_code == 400
    assert submit(ctx, body).status_code == 400
    assert leads(ctx) == []
    with SessionLocal() as db:
        stored = db.get(ConsultationChallenge, crud.token_hash(body['challenge_token']))
        assert stored.attempts == crud.MAX_ANSWER_ATTEMPTS


def test_replay_same_token_is_idempotent_and_cannot_change_phone(ctx):
    body = payload(ctx)
    first = submit(ctx, body)
    assert first.status_code == 201
    repeat = submit(ctx, body)
    assert repeat.status_code == 200 and repeat.json() == first.json()
    assert len(leads(ctx)) == 1
    assert submit(ctx, {**body,'phone':ctx['phone']()}).status_code == 409
    assert submit(ctx, {**body,'challenge_answer':'999'}).status_code == 400
    assert len(leads(ctx)) == 1


def test_duplicate_phone_normalized_and_blocked_across_clients(ctx):
    body = payload(ctx)
    assert submit(ctx, body).status_code == 201
    other = ctx['new_client']()
    proof = challenge(ctx, other)
    duplicate = payload(ctx, proof, phone='+84'+body['phone'][1:])
    assert submit(ctx, duplicate, other).status_code == 409
    assert len(leads(ctx)) == 1
    advance(ctx, crud.PHONE_WINDOW_SECONDS)
    duplicate = payload(ctx, challenge(ctx, other), phone=body['phone'])
    assert submit(ctx, duplicate, other).status_code == 201
    assert len(leads(ctx)) == 2


def test_submission_rate_survives_new_client_connection_and_ignores_spoofed_headers(ctx):
    body = payload(ctx, website='bot')
    for index in range(crud.SUBMIT_LIMIT):
        assert submit(ctx, body, headers={'X-Forwarded-For':f'198.51.100.{index+1}','X-Real-IP':str(index)}).status_code == 400
    # New connection/app client, same address: the database counter remains authoritative.
    with TestClient(app, client=(ctx['host'], 9999)) as connection:
        response = submit(ctx, body, connection)
    assert response.status_code == 429 and 0 < int(response.headers['retry-after']) <= crud.IP_WINDOW_SECONDS
    assert leads(ctx) == []
    advance(ctx, crud.IP_WINDOW_SECONDS)
    assert submit(ctx, payload(ctx)).status_code == 201


def test_rate_limit_successes_and_separate_client_limits(ctx):
    for _ in range(crud.SUBMIT_LIMIT):
        assert submit(ctx, payload(ctx)).status_code == 201
    assert submit(ctx, payload(ctx)).status_code == 429
    other = ctx['new_client']()
    assert submit(ctx, payload(ctx, challenge(ctx, other)), other).status_code == 201
    assert len(leads(ctx)) == crud.SUBMIT_LIMIT + 1


def test_challenge_generation_is_rate_limited_and_recovers(ctx):
    for _ in range(crud.CHALLENGE_LIMIT):
        challenge(ctx, ready=False)
    response = ctx['client'].get('/api/public/consultations/challenge')
    assert response.status_code == 429 and int(response.headers['retry-after']) == crud.IP_WINDOW_SECONDS
    advance(ctx, crud.IP_WINDOW_SECONDS)
    challenge(ctx)


def test_challenge_is_not_cacheable_or_stored_with_plain_answer_or_token(ctx):
    result = ctx['client'].get('/api/public/consultations/challenge')
    assert result.headers['cache-control'] == 'no-store'
    info = result.json()
    assert set(info) == {'challenge_token','question','expires_in','min_wait_seconds'}
    answer = str(sum(map(int,re.findall(r'\d+',info['question']))))
    with SessionLocal() as db:
        stored = db.get(ConsultationChallenge, crud.token_hash(info['challenge_token']))
        assert stored.token_hash != info['challenge_token'] and stored.answer_hash != answer
        assert stored.expires_at - stored.issued_at == timedelta(seconds=crud.CHALLENGE_TTL)


def test_database_failure_rolls_back_challenge_phone_and_lead(ctx):
    body = payload(ctx)

    def fail_insert(mapper, connection, target):
        raise RuntimeError('Simulated database failure')

    event.listen(ConsultationLead, 'before_insert', fail_insert)
    try:
        with pytest.raises(RuntimeError, match='Simulated database failure'):
            submit(ctx, body)
    finally:
        event.remove(ConsultationLead, 'before_insert', fail_insert)
    assert leads(ctx) == []
    with SessionLocal() as db:
        assert db.get(ConsultationChallenge, crud.token_hash(body['challenge_token'])).lead_id is None
        assert db.get(ConsultationRateBucket, crud.fingerprint('phone:'+body['phone'])).count == 0
    assert submit(ctx, body).status_code == 201


def test_public_api_never_lists_leads_or_exposes_pii(ctx):
    assert submit(ctx, payload(ctx)).status_code == 201
    assert ctx['client'].get('/api/public/consultations').status_code == 405
    assert ctx['client'].get('/api/public/consultations/1').status_code == 404
    assert ctx['client'].get('/api/consultation-leads').status_code == 404


def test_old_anti_spam_records_cleaned_without_deleting_leads(ctx):
    body = payload(ctx)
    assert submit(ctx, body).status_code == 201
    before = leads(ctx)
    advance(ctx, 3*86400)
    challenge(ctx)
    with SessionLocal() as db:
        assert db.get(ConsultationChallenge, crud.token_hash(body['challenge_token'])) is None
    assert leads(ctx) == before


def test_cors_exposes_rate_retry_to_public_frontend(ctx):
    response = ctx['client'].get('/api/public/consultations/challenge', headers={'Origin':'http://localhost:5173'})
    assert response.headers['access-control-allow-origin'] == 'http://localhost:5173'
    assert 'retry-after' in response.headers['access-control-expose-headers'].lower()


def test_mysql_keeps_microseconds_for_challenge_and_rate_timing():
    for model, names in [(ConsultationChallenge, ['issued_at','expires_at']), (ConsultationRateBucket,['window_start']),
                         (ConsultationLead,['created_at'])]:
        for name in names:
            assert model.__table__.c[name].type.compile(dialect=mysql.dialect()) == 'DATETIME(6)'
