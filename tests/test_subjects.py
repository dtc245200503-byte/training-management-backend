from datetime import datetime
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from app.core.security import create_access_token
from app.database import SessionLocal
from app.main import app
from app.models.subject import ClassSubject, Subject
from app.models.curriculum import CurriculumSubject
from app.models.training_program import TrainingClass, TrainingProgram
from app.models.user import User
from app.models.user_role import UserRole
from app.migrations import ensure_subject_columns


@pytest.fixture
def ctx():
    prefix = 'T33-' + uuid.uuid4().hex[:12].upper()
    users, programs, headers = [], [], {}
    with SessionLocal() as db:
        for role, role_id in [('manager', 5), ('admin', 1), ('student', 3), ('instructor', 2)]:
            user = User(username=prefix + role, email=prefix + role + '@example.com', full_name='Kiểm thử', password='unused', role_id=role_id)
            db.add(user); db.flush(); users.append(user.user_id)
            db.add(UserRole(user_id=user.user_id, role_id=role_id))
            headers[role] = {'Authorization': 'Bearer ' + create_access_token(user.user_id, 'ADMIN')}
        for suffix in ['A', 'B']:
            program = TrainingProgram(code=prefix + suffix, course_name='Chương trình kiểm thử', total_duration_hours=20, standard_tuition=0)
            db.add(program); db.flush(); programs.append(program.course_id)
        db.commit()
    with TestClient(app) as client:
        yield {'prefix': prefix, 'client': client, 'headers': headers, 'programs': programs}
    with SessionLocal() as db:
        ids = [item.id for item in db.query(Subject).filter(Subject.code.like(prefix + '%'))]
        db.query(ClassSubject).filter(ClassSubject.subject_id.in_(ids)).delete(synchronize_session=False)
        db.query(CurriculumSubject).filter(CurriculumSubject.subject_id.in_(ids)).delete(synchronize_session=False)
        db.query(Subject).filter(Subject.id.in_(ids)).delete(synchronize_session=False)
        db.query(TrainingClass).filter(TrainingClass.course_id.in_(programs)).delete(synchronize_session=False)
        db.query(TrainingProgram).filter(TrainingProgram.course_id.in_(programs)).delete(synchronize_session=False)
        db.query(UserRole).filter(UserRole.user_id.in_(users)).delete(synchronize_session=False)
        db.query(User).filter(User.user_id.in_(users)).delete(synchronize_session=False)
        db.commit()


def payload(ctx, suffix='A', **changes):
    return {'code': ctx['prefix'] + suffix, 'name': 'Lập trình Python', 'session_count': 12, 'weight': '1.25',
            'learning_outcomes': 'Viết được chương trình cơ bản', **changes}


def request(ctx, method, path='/api/subjects', role='manager', **kwargs):
    return ctx['client'].request(method, path, headers=ctx['headers'][role], **kwargs)


def create(ctx, suffix='A', **changes):
    result = request(ctx, 'POST', json=payload(ctx, suffix, **changes))
    assert result.status_code == 201, result.text
    return result.json()['subject_id']


def assign(ctx, subject_id, programs):
    return request(ctx, 'PUT', f'/api/subjects/{subject_id}/programs', json={'curriculum_ids': programs})


def add_class(ctx, status='in_progress', program_index=0):
    with SessionLocal() as db:
        item = TrainingClass(class_name='Lớp kiểm thử', course_id=ctx['programs'][program_index], status=status)
        db.add(item); db.commit(); db.refresh(item)
        return item.class_id


def test_create_read_update_and_unique_codes(ctx):
    first = create(ctx, code='  ' + ctx['prefix'].lower() + 'a  ', name='  Lập trình Python  ')
    item = request(ctx, 'GET', f'/api/subjects/{first}').json()
    assert item['code'] == ctx['prefix'] + 'A' and item['name'] == 'Lập trình Python'
    assert item['session_count'] == 12 and item['weight'] == '1.25' and item['class_count'] == 0
    assert request(ctx, 'POST', json=payload(ctx, code=item['code'].lower())).status_code == 409
    second = create(ctx, 'B')
    assert request(ctx, 'PUT', f'/api/subjects/{second}', json=payload(ctx, code=item['code'], name='Không được lưu')).status_code == 409
    assert request(ctx, 'GET', f'/api/subjects/{second}').json()['name'] == 'Lập trình Python'
    updated = request(ctx, 'PUT', f'/api/subjects/{first}', json=payload(ctx, session_count=20, weight='2', learning_outcomes=' '))
    assert updated.status_code == 200 and updated.json()['learning_outcomes'] is None
    assert updated.json()['session_count'] == 20 and updated.json()['weight'] == '2.00'
    with SessionLocal() as db:
        db.add(Subject(code=item['code'], subject_name='Trùng'))
        with pytest.raises(IntegrityError): db.commit()
        db.rollback()


@pytest.mark.parametrize('field,value', [('code', ''), ('code', 'Mã có dấu'), ('code', 'A' * 51), ('name', ' '), ('name', 'A' * 256),
    ('session_count', 0), ('session_count', -1), ('session_count', 1.5), ('session_count', True), ('session_count', 1001),
    ('weight', 0), ('weight', -1), ('weight', '1.234'), ('weight', '10000'), ('weight', 'NaN'),
    ('learning_outcomes', 'A' * 5001), ('unknown', 'not allowed')])
def test_invalid_data_is_rejected_by_backend(ctx, field, value):
    assert request(ctx, 'POST', json=payload(ctx, **{field: value})).status_code == 422
    assert request(ctx, 'GET', params={'search': ctx['prefix']}).json()['total'] == 0


def test_same_subject_reused_in_two_programs_without_duplicate_or_shared_rename(ctx):
    subject_id = create(ctx)
    response = assign(ctx, subject_id, ctx['programs'])
    assert response.status_code == 200 and len(response.json()['programs']) == 2
    assert assign(ctx, subject_id, ctx['programs']).status_code == 200
    for program_id in ctx['programs']:
        result = request(ctx, 'GET', f'/api/curriculums/{program_id}/subjects').json()
        assert len(result) == 1 and result[0]['subject_id'] == subject_id
    with SessionLocal() as db:
        assert db.query(Subject).filter(Subject.code.like(ctx['prefix'] + '%')).count() == 1
    assert assign(ctx, subject_id, [ctx['programs'][0], 999999]).status_code == 404
    assert len(request(ctx, 'GET', f'/api/subjects/{subject_id}').json()['programs']) == 2
    assert assign(ctx, subject_id, []).status_code == 200
    legacy = request(ctx, 'POST', f'/api/curriculums/{ctx["programs"][0]}/subjects', json={'subject_id': subject_id, 'subject_name': 'Không được đổi tên chung'})
    assert legacy.status_code == 201 and legacy.json()['subject_name'] == 'Lập trình Python'
    assert request(ctx, 'POST', f'/api/curriculums/{ctx["programs"][1]}/subjects', json={'subject_id': 999999, 'subject_name': 'Không tự tạo'}).status_code == 404


@pytest.mark.parametrize('status', ['in_progress', 'completed', 'cancelled'])
@pytest.mark.parametrize('remove_via', ['new', 'legacy'])
def test_any_class_blocks_delete_even_after_unlinking_from_program(ctx, status, remove_via):
    subject_id = create(ctx)
    assert assign(ctx, subject_id, [ctx['programs'][0]]).status_code == 200
    class_id = add_class(ctx, status)
    assert request(ctx, 'GET', f'/api/subjects/{subject_id}').json()['class_count'] == 1
    assert request(ctx, 'DELETE', f'/api/subjects/{subject_id}').status_code == 409
    if remove_via == 'new':
        assert assign(ctx, subject_id, []).status_code == 200
    else:
        assert request(ctx, 'DELETE', f'/api/curriculums/{ctx["programs"][0]}/subjects/{subject_id}').status_code == 200
    item = request(ctx, 'GET', f'/api/subjects/{subject_id}').json()
    assert item['programs'] == [] and item['class_count'] == 1 and not item['can_delete']
    assert request(ctx, 'DELETE', f'/api/subjects/{subject_id}').status_code == 409
    with SessionLocal() as db:
        assert db.get(TrainingClass, class_id).status == status
        assert db.query(ClassSubject).filter_by(class_id=class_id, subject_id=subject_id).count() == 1


def test_class_usage_is_deduplicated_and_existing_classes_captured_on_assignment(ctx):
    subject_id = create(ctx)
    add_class(ctx)
    assign(ctx, subject_id, [ctx['programs'][0]])
    assert request(ctx, 'GET', f'/api/subjects/{subject_id}').json()['class_count'] == 1
    assign(ctx, subject_id, ctx['programs'])
    add_class(ctx, 'completed', program_index=1)
    assert request(ctx, 'GET', f'/api/subjects/{subject_id}').json()['class_count'] == 2


def test_delete_without_class_removes_memberships_and_reserves_code(ctx):
    subject_id = create(ctx)
    assign(ctx, subject_id, ctx['programs'])
    assert request(ctx, 'DELETE', f'/api/subjects/{subject_id}').status_code == 200
    assert request(ctx, 'GET', f'/api/subjects/{subject_id}').status_code == 404
    assert request(ctx, 'GET', params={'search': ctx['prefix']}).json()['total'] == 0
    assert assign(ctx, subject_id, ctx['programs']).status_code == 404
    assert request(ctx, 'POST', json=payload(ctx)).status_code == 409
    with SessionLocal() as db:
        assert db.query(CurriculumSubject).filter_by(subject_id=subject_id).count() == 0
        assert db.get(Subject, subject_id).deleted_at is not None


def test_prerequisite_is_not_deleted_or_unlinked(ctx):
    first, second = create(ctx), create(ctx, 'B')
    assign(ctx, first, [ctx['programs'][0]])
    result = request(ctx, 'POST', f'/api/curriculums/{ctx["programs"][0]}/subjects', json={'subject_id': second, 'prerequisite_subject_id': first})
    assert result.status_code == 201
    assert request(ctx, 'DELETE', f'/api/subjects/{first}').status_code == 409
    assert assign(ctx, first, []).status_code == 409
    assert request(ctx, 'DELETE', f'/api/curriculums/{ctx["programs"][0]}/subjects/{first}').status_code == 409
    assert len(request(ctx, 'GET', f'/api/subjects/{first}').json()['programs']) == 1


@pytest.mark.parametrize('role', ['student', 'instructor'])
@pytest.mark.parametrize('method,path,data', [('GET','/api/subjects',None), ('POST','/api/subjects',{}),
    ('GET','/api/subjects/1',None), ('PUT','/api/subjects/1',{}), ('DELETE','/api/subjects/1',None),
    ('PUT','/api/subjects/1/programs',{}), ('GET','/api/subjects/program-options',None)])
def test_unauthorized_roles_denied_despite_admin_claim_in_jwt(ctx, role, method, path, data):
    assert request(ctx, method, path, role=role, json=data).status_code == 403


def test_admin_and_search_pagination(ctx):
    for suffix in ['A', 'B', 'C']: create(ctx, suffix, name='Môn học % ' + suffix)
    result = request(ctx, 'GET', role='admin', params={'search': ctx['prefix'].lower(), 'page_size': 2, 'page': 2}).json()
    assert result['total'] == 3 and len(result['items']) == 1
    assert request(ctx, 'GET', params={'search': 'Môn học %'}).json()['total'] == 3
    assert request(ctx, 'GET', params={'page': 0}).status_code == 422
    assert request(ctx, 'GET', '/api/subjects/999999').status_code == 404
    assert request(ctx, 'GET', '/api/subjects/program-options').status_code == 200


def test_assignment_requires_program_permission(ctx):
    from app.models.role_permission import RolePermission
    with SessionLocal() as db:
        db.query(RolePermission).filter_by(role_id=5, permission_id=3).delete(); db.commit()
    try:
        subject_id = create(ctx)
        assert assign(ctx, subject_id, ctx['programs']).status_code == 403
        assert request(ctx, 'GET', '/api/subjects/program-options').status_code == 403
    finally:
        with SessionLocal() as db:
            db.add(RolePermission(role_id=5, permission_id=3)); db.commit()


def test_migration_preserves_legacy_data_and_class_links():
    engine = create_engine('sqlite://')
    with engine.begin() as db:
        db.execute(text('CREATE TABLE subjects (id INTEGER PRIMARY KEY, subject_name TEXT, description TEXT)'))
        db.execute(text("INSERT INTO subjects VALUES (7, 'Môn cũ', 'Chuẩn đầu ra cũ')"))
        db.execute(text('CREATE TABLE classes (class_id INTEGER PRIMARY KEY, course_id INTEGER)'))
        db.execute(text('INSERT INTO classes VALUES (3, 9)'))
        db.execute(text('CREATE TABLE curriculum_subjects (curriculum_id INTEGER, subject_id INTEGER)'))
        db.execute(text('INSERT INTO curriculum_subjects VALUES (9, 7)'))
    ClassSubject.__table__.create(engine)
    ensure_subject_columns(engine); ensure_subject_columns(engine)
    with engine.connect() as db:
        assert db.execute(text('SELECT subject_name,description,code,session_count,weight FROM subjects')).one() == ('Môn cũ','Chuẩn đầu ra cũ','MH-7',1,1)
        assert db.execute(text('SELECT class_id,subject_id FROM class_subjects')).all() == [(3,7)]
    assert any(item.get('unique') and item['column_names'] == ['code'] for item in inspect(engine).get_indexes('subjects'))
    engine.dispose()
