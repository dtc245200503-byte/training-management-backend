import pytest
from sqlalchemy.exc import IntegrityError
from app.database import SessionLocal
from app.models.subject import Subject
from app.models.subject_lesson import SubjectLesson
from test_subjects import ctx, create, payload, request


@pytest.fixture
def lessons_ctx(ctx):
    yield ctx
    with SessionLocal() as db:
        ids = [row.id for row in db.query(Subject).filter(Subject.code.like(ctx['prefix'] + '%'))]
        db.query(SubjectLesson).filter(SubjectLesson.subject_id.in_(ids)).delete(synchronize_session=False)
        db.commit()


def url(subject_id, lesson_id=None):
    return f'/api/subjects/{subject_id}/lessons' + (f'/{lesson_id}' if lesson_id is not None else '')


def lesson(sequence=1, **changes):
    return {'sequence_order': sequence, 'topic': '  Chủ đề cơ bản  ', 'objectives': '  Hiểu kiến thức\nThực hành bài tập  ', **changes}


def add(ctx, sid, sequence=1, **changes):
    result = request(ctx, 'POST', url(sid), json=lesson(sequence, **changes))
    assert result.status_code == 201, result.text
    return result.json()


def get(ctx, sid):
    response = request(ctx, 'GET', url(sid))
    assert response.status_code == 200, response.text
    return response.json()


def clone(ctx, sid, source, mode='append'):
    return request(ctx, 'POST', url(sid) + '/clone', json={'source_subject_id': source, 'mode': mode})


def test_crud_ordered_trimmed_and_stored(lessons_ctx):
    ctx = lessons_ctx
    sid = create(ctx, session_count=3)
    assert get(ctx, sid)['items'] == []
    later = add(ctx, sid, 3)
    earlier = add(ctx, sid, 1, topic='Nền tảng')
    info = get(ctx, sid)
    assert info['session_count'] == 3 and info['code'] == ctx['prefix'] + 'A'
    assert [row['sequence_order'] for row in info['items']] == [1, 3]
    assert later['topic'] == 'Chủ đề cơ bản' and later['objectives'] == 'Hiểu kiến thức\nThực hành bài tập'
    result = request(ctx, 'PUT', url(sid, later['lesson_id']), json=lesson(2, topic='Chủ đề mới', objectives='Mục tiêu mới'))
    assert result.status_code == 200 and result.json()['topic'] == 'Chủ đề mới'
    assert [row['sequence_order'] for row in get(ctx, sid)['items']] == [1, 2]
    assert request(ctx, 'DELETE', url(sid, earlier['lesson_id'])).status_code == 200
    assert get(ctx, sid)['items'][0]['sequence_order'] == 2


@pytest.mark.parametrize('field,value', [('sequence_order', 0), ('sequence_order', -1), ('sequence_order', 1001),
    ('sequence_order', True), ('sequence_order', 1.5), ('sequence_order', '1'), ('sequence_order', None),
    ('topic', ''), ('topic', ' '), ('topic', 'A' * 256), ('topic', None),
    ('objectives', ''), ('objectives', ' '), ('objectives', 'A' * 5001), ('objectives', None),
    ('subject_id', 123), ('lesson_id', 123)])
def test_backend_validates_all_fields_without_writing(lessons_ctx, field, value):
    ctx = lessons_ctx
    sid = create(ctx)
    assert request(ctx, 'POST', url(sid), json=lesson(**{field: value})).status_code == 422
    assert get(ctx, sid)['items'] == []


def test_unique_positions_and_capacity_on_create_and_update(lessons_ctx):
    ctx = lessons_ctx
    sid = create(ctx, session_count=2)
    first = add(ctx, sid)
    assert request(ctx, 'POST', url(sid), json=lesson()).status_code == 409
    assert request(ctx, 'POST', url(sid), json=lesson(3)).status_code == 400
    second = add(ctx, sid, 2)
    before = get(ctx, sid)
    assert request(ctx, 'PUT', url(sid, second['lesson_id']), json=lesson(1, topic='Không được lưu')).status_code == 409
    assert request(ctx, 'PUT', url(sid, first['lesson_id']), json=lesson(3)).status_code == 400
    assert get(ctx, sid) == before
    with SessionLocal() as db:
        db.add(SubjectLesson(subject_id=sid, sequence_order=1, topic='Trùng', objectives='Mục tiêu'))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_position_is_scoped_to_subject_and_foreign_lesson_cannot_be_changed(lessons_ctx):
    ctx = lessons_ctx
    first, second = create(ctx), create(ctx, 'B')
    item = add(ctx, first)
    add(ctx, second)
    before = get(ctx, first)
    assert request(ctx, 'PUT', url(second, item['lesson_id']), json=lesson()).status_code == 404
    assert request(ctx, 'DELETE', url(second, item['lesson_id'])).status_code == 404
    assert get(ctx, first) == before


def test_reducing_subject_sessions_cannot_leave_invalid_lessons(lessons_ctx):
    ctx = lessons_ctx
    sid = create(ctx, session_count=5)
    item = add(ctx, sid, 5)
    update = request(ctx, 'PUT', f'/api/subjects/{sid}', json=payload(ctx, name='Không được lưu', session_count=4))
    assert update.status_code == 409
    subject = request(ctx, 'GET', f'/api/subjects/{sid}').json()
    assert subject['session_count'] == 5 and subject['name'] == 'Lập trình Python'
    assert request(ctx, 'PUT', url(sid, item['lesson_id']), json=lesson(2)).status_code == 200
    assert request(ctx, 'PUT', f'/api/subjects/{sid}', json=payload(ctx, session_count=2)).status_code == 200
    assert request(ctx, 'POST', url(sid), json=lesson(3)).status_code == 400


def test_clone_append_and_replace_produce_independent_copies(lessons_ctx):
    ctx = lessons_ctx
    source, target = create(ctx, session_count=5), create(ctx, 'B', session_count=5)
    source_later = add(ctx, source, 5, topic='Nâng cao')
    add(ctx, source, 2, topic='Nền tảng')
    original = add(ctx, target, 2, topic='Buổi đích')
    source_before = get(ctx, source)
    result = clone(ctx, target, source)
    assert result.status_code == 200
    copied = result.json()['items']
    assert [row['sequence_order'] for row in copied] == [2, 3, 4]
    assert [row['topic'] for row in copied] == ['Buổi đích', 'Nền tảng', 'Nâng cao']
    assert copied[0]['lesson_id'] == original['lesson_id']
    assert not {row['lesson_id'] for row in copied} & {row['lesson_id'] for row in source_before['items']}
    assert request(ctx, 'PUT', url(target, copied[-1]['lesson_id']), json=lesson(4, topic='Sửa bản sao')).status_code == 200
    assert get(ctx, source) == source_before
    assert request(ctx, 'PUT', url(source, source_later['lesson_id']), json=lesson(5, topic='Nguồn thay đổi')).status_code == 200
    assert get(ctx, target)['items'][-1]['topic'] == 'Sửa bản sao'
    replaced = clone(ctx, target, source, 'replace')
    assert replaced.status_code == 200
    assert [row['sequence_order'] for row in replaced.json()['items']] == [1, 2]
    assert [row['topic'] for row in replaced.json()['items']] == ['Nền tảng', 'Nguồn thay đổi']
    assert get(ctx, source)['items'][-1]['sequence_order'] == 5


@pytest.mark.parametrize('mode', ['append', 'replace'])
def test_failed_clone_never_removes_or_changes_target(lessons_ctx, mode):
    ctx = lessons_ctx
    source, target = create(ctx), create(ctx, 'B', session_count=1)
    add(ctx, source, 1); add(ctx, source, 2)
    add(ctx, target)
    before = get(ctx, target)
    assert clone(ctx, target, source, mode).status_code == 400
    assert get(ctx, target) == before


def test_append_capacity_checks_last_position_not_just_count(lessons_ctx):
    ctx = lessons_ctx
    source, target = create(ctx), create(ctx, 'B', session_count=3)
    add(ctx, source); add(ctx, target, 3)
    before = get(ctx, target)
    assert clone(ctx, target, source).status_code == 400
    assert get(ctx, target) == before
    assert clone(ctx, target, source, 'replace').status_code == 200


def test_clone_same_empty_missing_or_deleted_source_is_rejected(lessons_ctx):
    ctx = lessons_ctx
    source, target = create(ctx), create(ctx, 'B')
    before = get(ctx, target)
    assert clone(ctx, target, target).status_code == 400
    assert clone(ctx, target, source).status_code == 400
    assert clone(ctx, target, 99999999).status_code == 404
    add(ctx, source)
    assert request(ctx, 'DELETE', f'/api/subjects/{source}').status_code == 200
    assert clone(ctx, target, source).status_code == 404
    assert get(ctx, target) == before


@pytest.mark.parametrize('changes', [{'source_subject_id': True}, {'source_subject_id': '1'}, {'source_subject_id': 0},
    {'source_subject_id': -1}, {'mode': 'invalid'}, {'extra': 'forbidden'}])
def test_clone_schema_is_strict(lessons_ctx, changes):
    ctx = lessons_ctx
    sid = create(ctx)
    result = request(ctx, 'POST', url(sid) + '/clone', json={'source_subject_id': sid + 1, 'mode': 'append', **changes})
    assert result.status_code == 422
    assert get(ctx, sid)['items'] == []


@pytest.mark.parametrize('role', ['student', 'instructor'])
def test_unauthorized_role_cannot_access_any_lessons_api(lessons_ctx, role):
    ctx = lessons_ctx
    sid = create(ctx)
    item = add(ctx, sid)
    for method, path, body in [('GET', url(sid), None), ('POST', url(sid), lesson(2)),
        ('PUT', url(sid, item['lesson_id']), lesson()), ('DELETE', url(sid, item['lesson_id']), None),
        ('POST', url(sid) + '/clone', {'source_subject_id': sid + 1})]:
        assert request(ctx, method, path, role=role, **({'json': body} if body else {})).status_code == 403
    assert len(get(ctx, sid)['items']) == 1


def test_admin_and_unauthenticated_requests(lessons_ctx):
    ctx = lessons_ctx
    sid = create(ctx)
    assert request(ctx, 'POST', url(sid), role='admin', json=lesson()).status_code == 201
    assert request(ctx, 'GET', url(sid), role='admin').status_code == 200
    assert ctx['client'].get(url(sid)).status_code == 401


def test_missing_deleted_subject_and_missing_lesson(lessons_ctx):
    ctx = lessons_ctx
    sid = create(ctx)
    assert request(ctx, 'PUT', url(sid, 999999), json=lesson()).status_code == 404
    assert request(ctx, 'DELETE', url(sid, 999999)).status_code == 404
    assert request(ctx, 'DELETE', f'/api/subjects/{sid}').status_code == 200
    for method, body in [('GET', None), ('POST', lesson())]:
        assert request(ctx, method, url(sid), **({'json': body} if body else {})).status_code == 404
        assert request(ctx, method, url(999999), **({'json': body} if body else {})).status_code == 404


def test_live_capacity_change_is_enforced_on_clone_and_create(lessons_ctx):
    ctx = lessons_ctx
    source, target = create(ctx), create(ctx, 'B', session_count=4)
    add(ctx, source); add(ctx, source, 2)
    get(ctx, target)  # Represents an already open page with the previous limit.
    assert request(ctx, 'PUT', f'/api/subjects/{target}', json=payload(ctx, 'B', session_count=1)).status_code == 200
    assert clone(ctx, target, source).status_code == 400
    assert request(ctx, 'POST', url(target), json=lesson(2)).status_code == 400
    assert get(ctx, target)['items'] == []
