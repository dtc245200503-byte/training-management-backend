import pytest
from test_subjects import ctx, create, request, assign, add_class
from app.database import SessionLocal
from app.models.subject import Subject
from app.models.curriculum import CurriculumSubject
from app.models.role_permission import RolePermission
from app.models.training_program import TrainingProgram


def base(ctx, index=0):
    return f'/api/curriculums/{ctx["programs"][index]}'


def attach(ctx, subject_id, index=0, **fields):
    return request(ctx, 'POST', base(ctx,index) + '/subjects', json={'subject_id':subject_id, **fields})


def path(ctx, index=0):
    response = request(ctx,'GET',base(ctx,index) + '/subjects')
    assert response.status_code == 200, response.text
    return response.json()


def reorder(ctx, ids, index=0):
    return request(ctx,'PUT',base(ctx,index) + '/subjects/reorder',json={'items':[
        {'subject_id':subject_id,'sequence_order':position} for position,subject_id in enumerate(ids,1)]})


def prerequisite(ctx, subject_id, prerequisite_id, index=0):
    return request(ctx,'PATCH',base(ctx,index) + f'/subjects/{subject_id}/prerequisite',json={'prerequisite_subject_id':prerequisite_id})


def setup_path(ctx, n=3):
    ids = [create(ctx,str(index)) for index in range(n)]
    for subject_id in ids: assert attach(ctx,subject_id).status_code == 201
    return ids


def test_add_append_insert_and_remove_persist_contiguous_order(ctx):
    first,second,third = [create(ctx,suffix) for suffix in ['A','B','C']]
    result = attach(ctx,first,subject_name='Không đổi tên dùng chung')
    assert result.status_code == 201 and result.json()['subject_name'] == 'Lập trình Python'
    assert result.json()['subject_code'] == ctx['prefix'] + 'A' and result.json()['session_count'] == 12
    assert attach(ctx,second,prerequisite_subject_id=first).status_code == 201
    assert attach(ctx,third,sequence_order=2).status_code == 201
    assert [item['subject_id'] for item in path(ctx)] == [first,third,second]
    assert [item['sequence_order'] for item in path(ctx)] == [1,2,3]
    assert attach(ctx,first).status_code == 400
    assert request(ctx,'DELETE',base(ctx) + f'/subjects/{third}').status_code == 200
    assert [item['sequence_order'] for item in path(ctx)] == [1,2]
    assert request(ctx,'DELETE',base(ctx) + f'/subjects/{first}').status_code == 409
    assert prerequisite(ctx,second,None).status_code == 200
    assert request(ctx,'DELETE',base(ctx) + f'/subjects/{first}').status_code == 200
    assert path(ctx)[0]['subject_id'] == second and path(ctx)[0]['sequence_order'] == 1


def test_reorder_is_saved_with_metadata_and_prerequisites_before_dependents(ctx):
    first,second,third = setup_path(ctx)
    assert prerequisite(ctx,second,first).status_code == 200
    response = reorder(ctx,[third,first,second])
    assert response.status_code == 200
    assert response.json()['items'] == path(ctx)
    assert response.json()['items'][2]['prerequisite_subject_name'] == 'Lập trình Python'
    before = path(ctx)
    assert reorder(ctx,[second,third,first]).status_code == 400
    assert path(ctx) == before


def test_prerequisite_is_per_program_can_clear_and_cannot_cycle(ctx):
    first,second,third = setup_path(ctx)
    for subject_id in [first,second,third]: assert attach(ctx,subject_id,index=1).status_code == 201
    assert prerequisite(ctx,second,first).status_code == 200
    assert prerequisite(ctx,third,second).status_code == 200
    before = path(ctx)
    assert prerequisite(ctx,first,third).status_code == 400
    assert path(ctx) == before
    assert all(item['prerequisite_subject_id'] is None for item in path(ctx,1))
    assert reorder(ctx,[third,second,first],index=1).status_code == 200
    assert prerequisite(ctx,third,None).status_code == 200
    assert reorder(ctx,[third,first,second]).status_code == 200


@pytest.mark.parametrize('kind',['self','later','outside','missing'])
def test_invalid_prerequisites_are_atomic(ctx,kind):
    first,second,third = setup_path(ctx)
    outside = create(ctx,'OUT')
    values = {'self':second,'later':third,'outside':outside,'missing':999999}
    before = path(ctx)
    result = prerequisite(ctx,second,values[kind])
    assert result.status_code == (404 if kind == 'missing' else 400)
    assert path(ctx) == before


@pytest.mark.parametrize('kind',['partial','duplicate_subject','duplicate_position','gap','foreign','empty'])
def test_bad_reorder_cannot_partially_change_path(ctx,kind):
    ids = setup_path(ctx)
    outside = create(ctx,'OUT'); attach(ctx,outside,index=1)
    rows = [{'subject_id':subject_id,'sequence_order':position} for position,subject_id in enumerate(ids,1)]
    if kind == 'partial': rows.pop()
    if kind == 'duplicate_subject': rows[1]['subject_id'] = ids[0]
    if kind == 'duplicate_position': rows[1]['sequence_order'] = 1
    if kind == 'gap': rows[-1]['sequence_order'] = 4
    if kind == 'foreign': rows[-1]['subject_id'] = outside
    if kind == 'empty': rows = []
    before,other = path(ctx),path(ctx,1)
    result = request(ctx,'PUT',base(ctx) + '/subjects/reorder',json={'items':rows})
    assert result.status_code in [400,409]
    assert path(ctx) == before and path(ctx,1) == other


@pytest.mark.parametrize('field,value',[('subject_id',0),('subject_id',True),('sequence_order',0),
    ('sequence_order',1.5),('sequence_order',True),('prerequisite_subject_id',-1),('unknown','x')])
def test_add_input_validation(ctx,field,value):
    subject_id = create(ctx)
    assert request(ctx,'POST',base(ctx) + '/subjects',json={'subject_id':subject_id,field:value}).status_code == 422
    assert path(ctx) == []


def test_insert_cannot_place_advanced_before_foundation_or_leave_gap(ctx):
    first,second = setup_path(ctx,2)
    third = create(ctx,'NEW')
    before = path(ctx)
    assert attach(ctx,third,sequence_order=1,prerequisite_subject_id=first).status_code == 400
    assert attach(ctx,third,sequence_order=4).status_code == 400
    assert path(ctx) == before


def test_removal_preserves_catalogue_and_class_history(ctx):
    first,second = setup_path(ctx,2)
    add_class(ctx,'completed')
    assert request(ctx,'DELETE',base(ctx) + f'/subjects/{first}').status_code == 200
    assert path(ctx)[0]['subject_id'] == second and path(ctx)[0]['sequence_order'] == 1
    assert request(ctx,'GET',f'/api/subjects/{first}').status_code == 200
    assert request(ctx,'DELETE',f'/api/subjects/{first}').status_code == 409


def test_subject_side_membership_and_delete_keep_route_order(ctx):
    first,second,third = setup_path(ctx)
    assert assign(ctx,second,[]).status_code == 200
    assert [item['sequence_order'] for item in path(ctx)] == [1,2]
    assert assign(ctx,second,[ctx['programs'][0]]).status_code == 200
    assert [item['subject_id'] for item in path(ctx)] == [first,third,second]
    assert prerequisite(ctx,second,first).status_code == 200
    assert assign(ctx,first,[]).status_code == 409
    assert request(ctx,'DELETE',f'/api/subjects/{third}').status_code == 200
    assert [item['sequence_order'] for item in path(ctx)] == [1,2]
    assert path(ctx)[1]['prerequisite_subject_id'] == first


def test_available_subjects_exclude_linked_deleted_and_support_search_pagination(ctx):
    first,second,third = [create(ctx,suffix,name='Môn % ' + suffix) for suffix in ['A','B','C']]
    attach(ctx,first); request(ctx,'DELETE',f'/api/subjects/{third}')
    response = request(ctx,'GET',base(ctx) + '/available-subjects',params={'search':'Môn %','page_size':1})
    assert response.status_code == 200
    assert response.json()['total'] == 1 and response.json()['items'][0]['subject_id'] == second
    with SessionLocal() as db:
        db.query(RolePermission).filter_by(role_id=5,permission_id=4).delete(); db.commit()
    try:
        assert request(ctx,'GET',base(ctx) + '/available-subjects').status_code == 200
        assert attach(ctx,second).status_code == 201
    finally:
        with SessionLocal() as db:
            db.add(RolePermission(role_id=5,permission_id=4)); db.commit()


@pytest.mark.parametrize('role',['student','instructor'])
@pytest.mark.parametrize('method,suffix,data',[('GET','/subjects',None),('GET','/available-subjects',None),
    ('POST','/subjects',{'subject_id':1}),('DELETE','/subjects/1',None),
    ('PUT','/subjects/reorder',{'items':[]}),('PATCH','/subjects/1/prerequisite',{'prerequisite_subject_id':None})])
def test_curriculum_permission_required_at_backend(ctx,role,method,suffix,data):
    assert request(ctx,method,base(ctx)+suffix,role=role,json=data).status_code == 403


def test_missing_deleted_program_and_empty_path(ctx):
    assert path(ctx) == [] and reorder(ctx,[]).status_code == 200
    assert request(ctx,'GET','/api/curriculums/999999/subjects').status_code == 404
    assert request(ctx,'PATCH',base(ctx) + '/subjects/999999/prerequisite',json={'prerequisite_subject_id':None}).status_code == 404
    assert request(ctx,'PATCH',base(ctx) + '/subjects/1/prerequisite',json={}).status_code == 422
    assert request(ctx,'DELETE',base(ctx)).status_code == 200
    assert request(ctx,'GET',base(ctx) + '/subjects').status_code == 404
