import uuid
import pytest
from fastapi.testclient import TestClient
from app.core.security import create_access_token
from app.database import SessionLocal
from app.main import app
from app.models.user import User
from app.models.user_role import UserRole
from app.models.role_permission import RolePermission


@pytest.fixture
def context():
    ids, tokens = {}, {}
    prefix = 'selfrole_' + uuid.uuid4().hex[:12]
    with SessionLocal() as db:
        # Instructor has ROLE_MANAGE for these tests but remains a non-admin.
        db.add(RolePermission(role_id=2, permission_id=2))
        for name, primary_role, roles, jwt_role in [('admin',3,[1,3],'STUDENT'), ('manager',2,[2],'ADMIN'), ('student',3,[3],'ADMIN')]:
            user = User(username=prefix + name, email=prefix + name + '@example.com', full_name='Kiểm thử', password='unused', role_id=primary_role)
            db.add(user); db.flush(); ids[name] = user.user_id
            for role_id in roles: db.add(UserRole(user_id=user.user_id, role_id=role_id))
            tokens[name] = {'Authorization': 'Bearer ' + create_access_token(user.user_id, jwt_role)}
        db.commit()
    with TestClient(app) as client:
        yield client, ids, tokens
    with SessionLocal() as db:
        db.query(UserRole).filter(UserRole.user_id.in_(ids.values())).delete(synchronize_session=False)
        db.query(User).filter(User.user_id.in_(ids.values())).delete(synchronize_session=False)
        db.query(RolePermission).filter_by(role_id=2, permission_id=2).delete()
        db.commit()


def test_actual_admin_can_add_remove_other_own_roles_and_keeps_admin(context):
    client, ids, tokens = context
    url = f'/api/users/{ids["admin"]}/roles'
    assert client.post(url, headers=tokens['admin'], json={'role_id':5}).status_code == 200
    assert client.request('DELETE',url,headers=tokens['admin'],json={'role_id':3}).status_code == 200
    assert client.request('DELETE',url,headers=tokens['admin'],json={'role_id':5}).status_code == 200
    response = client.request('DELETE',url,headers=tokens['admin'],json={'role_id':1})
    assert response.status_code == 403 and 'chính mình' in response.json()['detail']
    assert [role['role_name'] for role in client.get(url,headers=tokens['admin']).json()['roles']] == ['ADMIN']


@pytest.mark.parametrize('method,role_id',[('POST',5),('POST',1),('DELETE',2)])
def test_non_admin_with_role_permission_cannot_edit_own_roles_or_escalate(context,method,role_id):
    client, ids, tokens = context
    url = f'/api/users/{ids["manager"]}/roles'
    assert client.request(method,url,headers=tokens['manager'],json={'role_id':role_id}).status_code == 403
    assert [role['role_name'] for role in client.get(url,headers=tokens['manager']).json()['roles']] == ['INSTRUCTOR']


def test_admin_can_still_edit_other_accounts(context):
    client, ids, tokens = context
    url = f'/api/users/{ids["student"]}/roles'
    assert client.post(url,headers=tokens['admin'],json={'role_id':5}).status_code == 200
    assert client.request('DELETE',url,headers=tokens['admin'],json={'role_id':5}).status_code == 200


def test_student_admin_claim_does_not_grant_role_permission(context):
    client, ids, tokens = context
    url = f'/api/users/{ids["student"]}/roles'
    assert client.post(url,headers=tokens['student'],json={'role_id':1}).status_code == 403
