from datetime import datetime, timedelta
import pytest
from test_lead_assignments import assigned, manager_lead, assign
from test_leads import ctx, req, create
from app.database import SessionLocal
from app.models.consultation import ConsultationLead
from app.models.user import User


def stamp(item, *, status='new', created_at=None):
    with SessionLocal() as db:
        lead = db.get(ConsultationLead, item['lead_id'])
        lead.status = status
        if created_at is not None: lead.created_at = created_at
        db.commit()
    return item


def listing(c, role='manager', **filters):
    result = req(c, 'GET', role=role, params={'search': c['prefix'], **filters})
    assert result.status_code == 200, result.text
    return result.json()


@pytest.mark.parametrize('status', ['new', 'contacted', 'qualified', 'converted', 'closed'])
def test_filter_each_status_without_changing_status(assigned, status):
    c = assigned
    target = stamp(manager_lead(c), status=status)
    stamp(manager_lead(c), status='closed' if status != 'closed' else 'new')
    result = listing(c, status=status)
    assert result['total'] == 1 and result['items'][0]['lead_id'] == target['lead_id']
    assert listing(c)['total'] == 2


def test_all_filters_are_intersected_and_phone_search_is_quick(assigned):
    c = assigned
    desired = stamp(manager_lead(c, full_name=c['prefix']+' Nguyễn Minh An', source='Facebook'),
                    status='contacted', created_at=datetime(2026, 9, 15, 2, 0))
    excluded = [stamp(manager_lead(c, source='Facebook'), status='new', created_at=datetime(2026, 9, 15)),
                stamp(manager_lead(c, source='Giới thiệu'), status='contacted', created_at=datetime(2026, 9, 15)),
                stamp(manager_lead(c, source='Facebook'), status='contacted', created_at=datetime(2026, 8, 15)),
                stamp(manager_lead(c, source='Facebook'), status='contacted', created_at=datetime(2026, 9, 15))]
    assert assign(c, [desired['lead_id']]+[l['lead_id'] for l in excluded[:3]]).status_code == 200
    assert assign(c, [excluded[-1]['lead_id']], c['users'][-1]).status_code == 200
    filters = {'source':'Facebook', 'status':'contacted', 'assignee_id':c['users'][0], 'date_from':'2026-09-01', 'date_to':'2026-09-30'}
    for role in ['manager', 'admin', 'admissions']:
        result = listing(c, role, **filters)
        assert result['total'] == 1 and result['items'][0]['lead_id'] == desired['lead_id']
    for term in ['minh an', desired['phone'][1:7], '+84'+desired['phone'][1:6],
                 desired['phone'][:4]+' '+desired['phone'][4:7]+' '+desired['phone'][7:]]:
        result = listing(c, 'admissions', search=term, **filters)
        assert result['total'] == 1 and result['items'][0]['lead_id'] == desired['lead_id']


@pytest.mark.parametrize('from_date,to_date,expected', [
    ('2026-09-01','2026-09-30',[1,2,3]), ('2026-09-01',None,[1,2,3,4]),
    (None,'2026-09-30',[0,1,2,3]), ('2026-09-01','2026-09-01',[1]),
    ('2026-09-30','2026-09-30',[3]), ('2026-10-01','2026-10-01',[4])])
def test_inclusive_calendar_date_boundaries_in_vietnam_time(assigned, from_date, to_date, expected):
    c = assigned
    dates = [datetime(2026,8,31,16,59,59,999999), datetime(2026,8,31,17), datetime(2026,9,15,12),
             datetime(2026,9,30,16,59,59,999999), datetime(2026,9,30,17)]
    items = [stamp(manager_lead(c), created_at=value) for value in dates]
    params = {k:v for k,v in [('date_from',from_date),('date_to',to_date)] if v is not None}
    result = listing(c, **params)
    assert {l['lead_id'] for l in result['items']} == {items[i]['lead_id'] for i in expected}


@pytest.mark.parametrize('params', [{'status':'invalid'}, {'status':'Mới'}, {'status':''}, {'date_from':'2026-02-30'},
    {'date_to':'2026-13-01'}, {'date_from':'07/10/2026'}, {'date_to':'2026-09-30T23:59:59Z'},
    {'assignee_id':-1}, {'assignee_id':'other'}, {'source':'A'*101}])
def test_invalid_filter_values_return_validation_errors(assigned, params):
    assert req(assigned, 'GET', role='manager', params=params).status_code == 422


def test_reversed_range_rejected_no_mutation_and_valid_leap_day(assigned):
    c = assigned; lead = stamp(manager_lead(c), created_at=datetime(2024,2,29,5))
    response = req(c, 'GET', role='manager', params={'date_from':'2026-10-10','date_to':'2026-10-01'})
    assert response.status_code == 400 and 'Ngày bắt đầu' in response.json()['detail']
    assert listing(c, date_from='2024-02-29', date_to='2024-02-29')['total'] == 1
    assert listing(c)['items'][0]['created_at'] == '2024-02-29T05:00:00'


def test_filters_and_options_never_expose_other_advisors_or_deleted_leads(assigned):
    c = assigned
    own = create(c, source=c['prefix']+' Nguồn A')
    hidden = manager_lead(c, source=c['prefix']+' Nguồn B')
    assert assign(c, [hidden['lead_id']], c['users'][-1]).status_code == 200
    deleted = create(c, source=c['prefix']+' Đã xóa')
    assert req(c, 'DELETE', f"/api/leads/{deleted['lead_id']}", role='manager').status_code == 200
    for filters in [{'assignee_id':c['users'][-1]}, {'assignee_id':0}, {'source':hidden['source']},
                    {'search':hidden['phone']}, {'date_from':'2020-01-01','date_to':'2030-12-31'}]:
        result = listing(c, 'admissions', **filters)
        assert all(l['lead_id'] == own['lead_id'] for l in result['items'])
    options = req(c, 'GET', '/api/leads/filter-options').json()
    assert options == {'sources':[own['source']], 'assignees':[{'user_id':c['users'][0], 'full_name':c['prefix']+'admissions'}], 'can_view_all':False}
    assert hidden['source'] not in str(options) and str(c['users'][-1]) not in str([u['user_id'] for u in options['assignees']])
    for role in ['manager','admin']:
        options = req(c,'GET','/api/leads/filter-options',role=role).json()
        assert options['can_view_all'] is True and hidden['source'] in options['sources'] and deleted['source'] not in options['sources']
    with SessionLocal() as db:
        db.get(User,c['users'][-1]).is_locked = True; db.commit()
    # Existing leads remain filterable by a former/inactive owner.
    options = req(c,'GET','/api/leads/filter-options',role='manager').json()
    assert c['users'][-1] in [u['user_id'] for u in options['assignees']]


def test_unassigned_source_exact_match_and_literal_search(assigned):
    c = assigned
    lead = manager_lead(c, source=c['prefix']+' Facebook % _')
    manager_lead(c, source=c['prefix']+' Facebook')
    create(c, source=lead['source'])
    assert listing(c, source=lead['source'], assignee_id=0)['total'] == 1
    assert listing(c, search='%')['total'] == 2
    assert listing(c, search="' OR 1=1 --")['total'] == 0


def test_filtered_total_and_pagination_stable_with_matching_creation_times(assigned):
    c = assigned
    items = [stamp(manager_lead(c, source=c['prefix']+' Trang'), status='contacted', created_at=datetime(2026,9,1,12)) for _ in range(22)]
    stamp(manager_lead(c, source=c['prefix']+' Trang'), status='closed', created_at=datetime(2026,9,1,12))
    assert assign(c,[i['lead_id'] for i in items]).status_code == 200
    filters = {'status':'contacted','source':c['prefix']+' Trang','assignee_id':c['users'][0],'date_from':'2026-09-01','date_to':'2026-09-30'}
    first = listing(c, 'admissions', **filters); second = listing(c,'admissions',page=2,**filters)
    assert first['total'] == second['total'] == 22 and len(first['items']) == 20 and len(second['items']) == 2
    assert [i['lead_id'] for i in first['items']+second['items']] == sorted([i['lead_id'] for i in items], reverse=True)


@pytest.mark.parametrize('role', ['student','instructor'])
def test_filter_options_and_filtered_listing_require_permission(assigned, role):
    c = assigned
    assert req(c,'GET','/api/leads/filter-options',role=role).status_code == 403
    assert req(c,'GET',role=role,params={'status':'new','date_from':'2026-09-01'}).status_code == 403
    assert c['client'].get('/api/leads/filter-options').status_code == 401
