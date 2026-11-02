import sys, json, copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from pipeline import prepare, normalize, date, BASE
from tagging import baseline, validate
from recommend import recommend
from datetime import datetime,timezone

@pytest.fixture
def event(): return prepare(BASE/'tests/fixtures/ninerengage.xml','ninerengage')[1][0][1]

def test_date_not_publication_and_id_stable():
    import xml.etree.ElementTree as ET
    item=ET.fromstring('<item><guid>1</guid><title>Study</title><link>https://example.org/event</link><pubDate>Mon, 01 Jun 2026 12:00:00 GMT</pubDate><start xmlns="events">2026-11-02T13:00:00-05:00</start><end xmlns="events">2026-11-02T14:00:00-05:00</end></item>')
    e=normalize(item,'ninerengage','2026-11-01T00:00:00+00:00')
    assert e['start_at']=='2026-11-02T18:00:00+00:00'
    item.find('pubDate').text='Tue, 02 Jun 2026 12:00:00 GMT'
    assert normalize(item,'ninerengage','2026-11-02T00:00:00+00:00')['content_hash']==e['content_hash']
    item.find('title').text='Changed'; changed=normalize(item,'ninerengage','2026-11-02T00:00:00+00:00')
    assert changed['id']==e['id'] and changed['content_hash']!=e['content_hash']

def test_dst_offsets():
    assert date('2026-11-01T01:30:00-04:00')!=date('2026-11-01T01:30:00-05:00')
    with pytest.raises(ValueError): date('2026-11-01T01:30:00')

def test_recurrences_distinct():
    _,rows=prepare(BASE/'tests/fixtures/campusevents.xml','campusevents')
    groups={}
    for _,e in rows: groups.setdefault(e['series_id'],[]).append(e)
    recurring=next(es for es in groups.values() if len(es)>2)
    assert len({e['id'] for e in recurring})==len(recurring)

def test_repeat_replay(event):
    a,rows=prepare(BASE/'tests/fixtures/ninerengage.xml','ninerengage'); b,again=prepare(BASE/'tests/fixtures/ninerengage.xml','ninerengage')
    assert [(r['id'],e['id'],e['content_hash']) for r,e in rows]==[(r['id'],e['id'],e['content_hash']) for r,e in again]

def test_food_claims(event):
    e={**event,'title':'Free event','description':'All are welcome.'}
    assert baseline(e)['free_food']=='unknown'
    with pytest.raises(ValueError): validate({'free_food':'yes','evidence':{'free_food':'Free event'}},'Free event')
    for text in ['No free food.','Free pizza is not provided.']:
        assert baseline({**e,'description':text})['free_food']!='yes'
    assert baseline({**e,'description':'Enjoy free pizza.'})['free_food']=='yes'

def test_evidence_required():
    with pytest.raises(ValueError):validate({'free_food':'yes','evidence':{'free_food':'free pizza'}},'Come to this free event')
    with pytest.raises(ValueError):validate({'topics':['unrecognized']},'event')

def test_recommend_eligibility_and_filters(event):
    e={**event,'start_at':'2030-01-01T12:00:00+00:00','status':'active','tags':{'topics':['technology'],'free_food':'unknown','audience_restricted':'yes','audience':['students']}}
    at=datetime(2026,1,1,tzinfo=timezone.utc)
    assert recommend([e],at=at)==[]
    assert recommend([e],at=at,audience=['students'],free_food=True)==[]
    assert len(recommend([e],at=at,audience=['students'],interests=['technology']))==1
    assert recommend([{**e,'status':'cancelled'}],at=at,audience=['students'])==[]

def test_split_disjoint():
    
    if not (BASE/'data/events.json').exists(): pytest.skip('Full snapshot needed for full grouping audit; run pipeline first')
    events=json.loads((BASE/'data/events.json').read_text()); split={r['event_id']:r['split'] for r in json.loads((BASE/'data/split_manifest.json').read_text())}
    for field in ['series_id','related_group','duplicate_key']:
        groups={}
        for e in events:
            if e[field]:groups.setdefault(e[field],set()).add(split[e['id']])
        assert all(len(v)==1 for v in groups.values())


def test_model_cannot_crop_negation():
    with pytest.raises(ValueError):
        validate({'free_food':'yes','evidence':{'free_food':'free pizza'}},'There is no free pizza.')
