"""Supabase REST adapter plus SQL batches for connector-authorized bootstrap."""
import json, os
from pathlib import Path
from pipeline import SOURCES, BASE, session, now
from tagging import baseline, model_candidate

class Supabase:
    def __init__(self, write=False):
        self.url=os.environ['SUPABASE_URL'].rstrip('/')+'/rest/v1/'
        key=os.environ['SUPABASE_SERVICE_ROLE_KEY' if write else 'SUPABASE_PUBLISHABLE_KEY']
        self.http=session(); self.http.headers.update({'apikey':key})
        if key.startswith('eyJ'): self.http.headers['Authorization']='Bearer '+key
    def rows(self, table, **filters):
        result=[]; offset=0
        while True:
            r=self.http.get(self.url+table,params={'select':'*','order':'id' if table in ('events','event_sources') else 'event_id','limit':500,'offset':offset,**filters},timeout=(10,45))
            r.raise_for_status(); page=r.json(); result.extend(page)
            if len(page)<500: return result
            offset+=len(page)
    def upsert(self,table,rows,key='id',ignore=False):
        if not rows: return
        r=self.http.post(self.url+table,params={'on_conflict':key},json=rows,headers={'Prefer':'resolution='+('ignore' if ignore else 'merge')+'-duplicates,return=minimal'},timeout=(10,60))
        r.raise_for_status()
    def patch(self,table,filters,values):
        r=self.http.patch(self.url+table,params=filters,json=values,timeout=(10,45)); r.raise_for_status()

def publish(source,run,rows):
    db=Supabase(write=True)
    db.upsert('event_sources',[dict(id=source,url=SOURCES[source],name=source)])
    db.upsert('ingestion_runs',[{**run,'status':'running','finished_at':None}])
    try:
        for raw,event in rows:
            db.upsert('raw_records',[raw],ignore=True)
            if not event: continue
            old=db.rows('events',id='eq.'+event['id'])
            if old:
                event['first_seen_at']=old[0]['first_seen_at']
                if old[0]['content_hash']==event['content_hash']:
                    db.patch('events',{'id':'eq.'+event['id']},{'last_seen_at':event['last_seen_at']}); continue
            # Clear prior claims before publishing changed content. Readers also hash-check joins.
            tag=baseline(event)
            try: tag=model_candidate(event) or tag
            except Exception: pass  # baseline remains pending; never fabricate model success
            db.upsert('event_tags',[tag],key='event_id') if old else None
            db.upsert('events',[event])
            db.upsert('event_tags',[tag],key='event_id')
        db.upsert('ingestion_runs',[run])
        db.patch('event_sources',{'id':'eq.'+source},{'last_success_at':run['finished_at']})
    except Exception as exc:
        db.patch('ingestion_runs',{'id':'eq.'+run['id']},{'status':'failed','finished_at':now(),'error':type(exc).__name__})
        raise

def literal(value):
    if value is None: return 'null'
    if isinstance(value,(dict,list)): return "'"+json.dumps(value).replace("'","''")+"'"
    if isinstance(value,int): return str(value)
    return "'"+str(value).replace("'","''")+"'"

ARRAYS={'organizers','source_categories','quality_flags','topics','audience'}
def insert(table,row, conflict='id',keep=(),ignore=False):
    vals=[]
    for key,value in row.items():
        vals.append('array['+','.join(literal(x) for x in value)+']::text[]' if key in ARRAYS else literal(value))
    action='nothing' if ignore else 'update set '+','.join(f'{k}=excluded.{k}' for k in row if k!=conflict and k not in keep)
    if table=='event_tags': action += ' where event_tags.content_hash <> excluded.content_hash'
    if table=='events':
        action=action.replace('updated_at=excluded.updated_at','updated_at=case when events.content_hash <> excluded.content_hash then excluded.updated_at else events.updated_at end')
    return f"insert into public.{table} ({','.join(row)}) values ({','.join(vals)}) on conflict ({conflict}) do {action};\n"

def export_sql(source,run,rows):
    folder=BASE/'data/sql'; folder.mkdir(exist_ok=True)
    header=insert('event_sources',dict(id=source,url=SOURCES[source],name=source))
    header+=insert('ingestion_runs',{**run,'status':'running','finished_at':None})
    (folder/f'{source}-000.sql').write_text('begin;\n'+header+'commit;')
    for i in range(0,len(rows),20):
        sql='begin;\n'
        for raw,event in rows[i:i+20]:
            sql+=insert('raw_records',raw,ignore=True)
            if event:
                sql+=insert('events',event,keep=('first_seen_at',))
                sql+=insert('event_tags',baseline(event),conflict='event_id')
        (folder/f'{source}-{1+i//20:03d}.sql').write_text(sql+'commit;')
    tail=insert('ingestion_runs',run)+f"update public.event_sources set last_success_at={literal(run['finished_at'])} where id={literal(source)};"
    (folder/f'{source}-999.sql').write_text('begin;\n'+tail+'commit;')

def load_catalog():
    db=Supabase(); active='in.('+','.join(SOURCES)+')'; events=db.rows('events',source_id=active); tags={t['event_id']:t for t in db.rows('event_tags')}
    for e in events:
        t=tags.get(e['id']); e['tags']=t if t and t['content_hash']==e['content_hash'] else None
    return events,db.rows('event_sources',id=active)
