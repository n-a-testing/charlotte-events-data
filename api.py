from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from storage import load_catalog
from recommend import recommend
from datetime import datetime, timezone
from functools import lru_cache
import time
app=FastAPI(title='Charlotte Events Data API',version='1.0.0',description='Public university feed data. Campus timezone: America/New_York. Tags are provisional unless reviewed. No personal data is persisted.')
@lru_cache(maxsize=2)
def cached(bucket): return load_catalog()
def catalog():
    try: return cached(int(time.time()//120))
    except Exception: raise HTTPException(503,'Event database unavailable')
@app.get('/health')
def health():
    events,sources=catalog(); return {'status':'ok','event_count':len(events),'sources':sources}
@app.get('/events')
def events(source:str|None=None,q:str='',upcoming:bool=True,offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=200)):
    records,_=catalog(); now=datetime.now(timezone.utc)
    records=[e for e in records if (not source or e['source_id']==source) and q.lower() in (e['title']+' '+e['description']).lower() and (not upcoming or (e['status']=='active' and datetime.fromisoformat(e['start_at'])>=now))]
    records.sort(key=lambda e:(e['start_at'],e['id']))
    return {'total':len(records),'offset':offset,'events':records[offset:offset+limit]}
class Preferences(BaseModel):
    interests:list[str]=Field(default_factory=list,max_length=20)
    saved_ids:list[str]=Field(default_factory=list,max_length=200)
    audience:list[str]=Field(default_factory=list,max_length=10)
    free_food:bool=False
    free_admission:bool=False
    limit:int=Field(20,ge=1,le=100)
@app.post('/recommendations')
def recommendations(preferences:Preferences): return recommend(catalog()[0],**preferences.model_dump())
