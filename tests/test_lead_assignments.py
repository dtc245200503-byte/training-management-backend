import pytest
from sqlalchemy import create_engine, inspect, text
from test_leads import ctx, payload, req, create
from app.database import SessionLocal
from app.models.user import User
from app.models.user_role import UserRole
from app.models.role_permission import RolePermission
from app.models.lead_assignment import LeadAssignmentHistory
from app.models.consultation import ConsultationLead
from app.core.security import create_access_token
from app.migrations import ensure_lead_assignment_columns


@pytest.fixture
def assigned(ctx):
    with SessionLocal() as db:
        second = User(username=ctx['prefix']+'second', full_name=ctx['prefix']+' Tư vấn B',
                      email=ctx['prefix']+'second@example.com', password='unused', role_id=5)
        db.add(second); db.flush()
        db.add(UserRole(user_id=second.user_id, role_id=6)); db.commit()
        ctx['users'].append(second.user_id)
        ctx['headers']['second'] = {'Authorization': 'Bearer '+create_access_token(second.user_id, 'ADMIN')}
    return ctx


def manager_lead(ctx, **changes):
    result = req(ctx, 'POST', role='manager', json=payload(ctx, **changes))
    assert result.status_code == 201, result.text
    return result.json()


def assign(ctx, ids, target=None, role='manager', **changes):
    return req(ctx, 'POST', '/api/leads/assign', role=role, json={
        'lead_ids': ids, 'assignee_id': target or ctx['users'][0], 'note': 'Gọi sau 17 giờ', **changes})


def history(ctx, lead, role='manager', **params):
    return req(ctx, 'GET', f"/api/leads/{lead['lead_id']}/assignment-history", role=role, params=params)


def test_single_bulk_transfer_visibility_and_immutable_history(assigned):
    c = assigned
    leads = [manager_lead(c) for _ in range(3)]
    assert req(c, 'GET', params={'search': c['prefix']}).json()['total'] == 0
    result = assign(c, [l['lead_id'] for l in leads])
    assert result.status_code == 200 and result.json()['changed'] == 3
    assert req(c, 'GET', params={'search': c['prefix']}).json()['total'] == 3
    assert req(c, 'GET', role='second', params={'search': c['prefix']}).json()['total'] == 0
    lead = leads[0]
    first = history(c, lead).json()['items'][0]
    assert first['from_assignee_id'] is None and first['to_assignee_id'] == c['users'][0]
    assert first['actor_id'] == c['users'][1] and first['note'] == 'Gọi sau 17 giờ'
    assert assign(c, [lead['lead_id']], c['users'][-1]).json()['changed'] == 1
    assert req(c, 'GET', f"/api/leads/{lead['lead_id']}").status_code == 404
    assert history(c, lead, role='admissions').status_code == 404
    assert history(c, lead, role='second').json()['total'] == 2
    assert req(c, 'GET', role='second', params={'search': c['prefix']}).json()['total'] == 1
    with SessionLocal() as db:
        db.get(User, c['users'][0]).full_name = c['prefix']+' Đã đổi tên'; db.commit()
    latest = history(c, lead).json()['items'][0]
    assert latest['from_assignee_name'] == first['to_assignee_name']
    assert latest['from_assignee_id'] == c['users'][0] and latest['to_assignee_id'] == c['users'][-1]
    assert req(c, 'GET', role='admin', params={'search': c['prefix']}).json()['total'] == 3


def test_scoping_all_read_edit_duplicate_paths_and_forged_filters(assigned):
    c = assigned
    hidden = manager_lead(c)
    own = create(c, phone=hidden['phone'], confirm_duplicate=True)
    assert own['assignee_id'] == c['users'][0] and own['duplicate_count'] == 0
    for role in ['admissions', 'second']:
        url = f"/api/leads/{hidden['lead_id']}"
        assert req(c, 'GET', url, role=role).status_code == 404
        assert req(c, 'PUT', url, role=role, json=payload(c)).status_code == 404
        assert history(c, hidden, role=role).status_code == 404
        assert req(c, 'GET', '/api/leads/check-phone', role=role, params={
            'phone': hidden['phone'], 'exclude_lead_id': hidden['lead_id']}).status_code == 404
        result = req(c, 'GET', '/api/leads/check-phone', role=role, params={'phone': hidden['phone']}).json()
        assert result['hidden_match'] is True
        assert hidden['lead_id'] not in [x['lead_id'] for x in result['duplicates']]
        assert result['total'] == (1 if role == 'admissions' else 0)
    for params in [{'assignee_id': 0}, {'assignee_id': c['users'][-1]}, {'search': hidden['email']}, {'search': hidden['full_name'], 'page_size': 100}]:
        result = req(c, 'GET', params=params).json()
        assert hidden['lead_id'] not in [x['lead_id'] for x in result['items']]
    warning = req(c, 'POST', role='second', json=payload(c, phone=hidden['phone']))
    assert warning.status_code == 409
    assert warning.json()['detail']['duplicates'] == [] and warning.json()['detail']['total'] == 0
    assert hidden['full_name'] not in warning.text


@pytest.mark.parametrize('role', ['admissions', 'second', 'admin', 'student', 'instructor'])
def test_assignment_requires_actual_training_manager_role(assigned, role):
    c = assigned; lead = manager_lead(c)
    assert assign(c, [lead['lead_id']], role=role).status_code == 403
    assert req(c, 'GET', '/api/leads/advisors', role=role).status_code == 403
    assert history(c, lead).json()['total'] == 0


def test_manager_multirole_and_revocation_take_effect_immediately(assigned):
    c = assigned; lead = manager_lead(c)
    with SessionLocal() as db:
        db.add(UserRole(user_id=c['users'][2], role_id=5)); db.commit()
    assert assign(c, [lead['lead_id']], role='admin').status_code == 200
    with SessionLocal() as db:
        db.add(UserRole(user_id=c['users'][1], role_id=6))
        db.query(UserRole).filter_by(user_id=c['users'][1], role_id=5).delete(); db.commit()
    assert assign(c, [lead['lead_id']], c['users'][-1]).status_code == 403
    assert req(c, 'GET', role='manager', params={'search': c['prefix']}).json()['total'] == 0


@pytest.mark.parametrize('index', [1, 2, 3, 4])
def test_recipient_must_be_an_advisor_not_primary_role_or_claim(assigned, index):
    c = assigned; lead = manager_lead(c)
    assert assign(c, [lead['lead_id']], c['users'][index]).status_code == 400
    assert history(c, lead).json()['total'] == 0


@pytest.mark.parametrize('state', ['locked', 'temporary_lock', 'role_removed', 'permission_removed', 'nonexistent'])
def test_inactive_or_revoked_advisor_is_rejected_and_hidden(assigned, state):
    from datetime import datetime, timedelta, UTC
    c = assigned; lead = manager_lead(c); target = c['users'][-1]
    with SessionLocal() as db:
        if state == 'locked': db.get(User, target).is_locked = True
        if state == 'temporary_lock': db.get(User, target).locked_until = datetime.now(UTC).replace(tzinfo=None)+timedelta(hours=1)
        if state == 'role_removed': db.query(UserRole).filter_by(user_id=target, role_id=6).delete()
        if state == 'permission_removed': db.query(RolePermission).filter_by(role_id=6, permission_id=5).delete()
        if state == 'nonexistent': target = 999999
        db.commit()
    try:
        assert assign(c, [lead['lead_id']], target).status_code == 400
        assert target not in [u['user_id'] for u in req(c, 'GET', '/api/leads/advisors', role='manager').json()]
        assert history(c, lead).json()['total'] == 0
    finally:
        if state == 'permission_removed':
            with SessionLocal() as db:
                db.add(RolePermission(role_id=6, permission_id=5)); db.commit()


@pytest.mark.parametrize('changes', [
    {'lead_ids': []}, {'lead_ids': [1, 1]}, {'lead_ids': [0]}, {'lead_ids': [-1]},
    {'lead_ids': [True]}, {'lead_ids': ['1']}, {'lead_ids': [1.0]}, {'lead_ids': list(range(1, 102))},
    {'assignee_id': 0}, {'assignee_id': None}, {'assignee_id': True}, {'assignee_id': '1'},
    {'note': 'A'*1001}, {'actor_id': 1}, {'created_at': '2026-01-01'}])
def test_invalid_batch_and_history_injection_are_rejected(assigned, changes):
    c = assigned; lead = manager_lead(c)
    assert assign(c, [lead['lead_id']], **changes).status_code == 422
    assert history(c, lead).json()['total'] == 0


@pytest.mark.parametrize('missing', ['absent', 'deleted'])
def test_batch_is_atomic_for_a_missing_or_deleted_lead(assigned, missing):
    c = assigned; one, two = manager_lead(c), manager_lead(c)
    invalid = 999999
    if missing == 'deleted':
        invalid = two['lead_id']; req(c, 'DELETE', f'/api/leads/{invalid}', role='manager')
    response = assign(c, [one['lead_id'], invalid])
    assert response.status_code == 404
    assert req(c, 'GET', f"/api/leads/{one['lead_id']}", role='manager').json()['assignee_id'] is None
    assert history(c, one).json()['total'] == 0


def test_noop_assignment_creates_no_fake_history_and_mixed_batch_counts(assigned):
    c = assigned; first, second = manager_lead(c), manager_lead(c)
    assert assign(c, [first['lead_id']]).json()['changed'] == 1
    result = assign(c, [first['lead_id'], second['lead_id']]).json()
    assert result['changed'] == 1 and result['unchanged'] == 1
    assert assign(c, [first['lead_id'], second['lead_id']]).json()['changed'] == 0
    assert history(c, first).json()['total'] == history(c, second).json()['total'] == 1


def test_history_pagination_filters_and_contact_edit_preserve_owner(assigned):
    c = assigned; lead = manager_lead(c)
    assert req(c, 'GET', role='manager', params={'search': c['prefix'], 'assignee_id': 0}).json()['total'] == 1
    for i in range(23):
        assert assign(c, [lead['lead_id']], c['users'][0] if i % 2 == 0 else c['users'][-1]).status_code == 200
    first = history(c, lead, page_size=20).json(); second = history(c, lead, page=2, page_size=20).json()
    assert first['total'] == 23 and len(first['items']) == 20 and len(second['items']) == 3
    assert not {i['history_id'] for i in first['items']} & {i['history_id'] for i in second['items']}
    updated = req(c, 'PUT', f"/api/leads/{lead['lead_id']}", json=payload(c)).json()
    assert updated['assignee_id'] == c['users'][0] and history(c, lead).json()['total'] == 23
    assert req(c, 'GET', role='manager', params={'search': c['prefix'], 'assignee_id': 0}).json()['total'] == 0
    assert req(c, 'GET', role='manager', params={'search': c['prefix'], 'assignee_id': c['users'][0]}).json()['total'] == 1


def test_advisor_creation_is_automatically_assigned_and_cannot_forge_owner(assigned):
    c = assigned; lead = create(c)
    assert lead['assignee_id'] == c['users'][0]
    assert history(c, lead, role='admissions').json()['items'][0]['actor_id'] == c['users'][0]
    assert req(c, 'POST', json=payload(c, assignee_id=c['users'][-1])).status_code == 422
    assert req(c, 'PUT', f"/api/leads/{lead['lead_id']}", json=payload(c, assignee_id=c['users'][-1])).status_code == 422


def test_assignment_migration_preserves_existing_unassigned_leads_idempotently():
    engine = create_engine('sqlite://')
    with engine.begin() as conn:
        conn.execute(text('CREATE TABLE users (user_id INTEGER PRIMARY KEY)'))
        conn.execute(text('CREATE TABLE consultation_leads (lead_id INTEGER PRIMARY KEY, full_name VARCHAR(100))'))
        conn.execute(text("INSERT INTO consultation_leads VALUES (1, 'Khách cũ')"))
    ensure_lead_assignment_columns(engine); ensure_lead_assignment_columns(engine)
    with engine.connect() as conn:
        row = conn.execute(text('SELECT * FROM consultation_leads')).mappings().one()
        assert row['full_name'] == 'Khách cũ' and row['assignee_id'] is None
    assert 'ix_consultation_leads_assignee_id' in {i['name'] for i in inspect(engine).get_indexes('consultation_leads')}
    engine.dispose()
