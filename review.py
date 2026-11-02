"""Operator-only review commands; never expose the service credential to the dashboard."""
import argparse,json,uuid
from storage import Supabase
from tagging import validate,baseline,model_candidate
from pipeline import now, SOURCES

def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='cmd',required=True)
    q=sub.add_parser('queue'); q.add_argument('--output',default='data/review-queue.json')
    a=sub.add_parser('approve'); a.add_argument('event_id'); a.add_argument('labels_file'); a.add_argument('--reviewer',required=True)
    sub.add_parser('tag-pending')
    args=p.parse_args(); db=Supabase(write=True)
    events={e['id']:e for e in db.rows('events',source_id='in.('+','.join(SOURCES)+')')}; tags=[t for t in db.rows('event_tags') if t['event_id'] in events]
    if args.cmd=='queue':
        # Gold review deliberately hides model/keyword predictions to reduce anchoring.
        pending=[{'event_id':t['event_id'],'content_hash':events[t['event_id']]['content_hash'],'title':events[t['event_id']]['title'],'description':events[t['event_id']]['description'],'url':events[t['event_id']]['url']} for t in tags if t['review_status']=='pending']
        open(args.output,'w').write(json.dumps(pending,indent=2)); print(f'Exported {len(pending)} review items')
    elif args.cmd=='approve':
        event=events[args.event_id]; incoming=json.load(open(args.labels_file))
        if incoming.pop('content_hash')!=event['content_hash']: raise ValueError('Event changed since review; review again')
        labels=validate(incoming,event['title']+'\n'+event['description'])
        db.upsert('tag_reviews',[{'id':str(uuid.uuid4()),'event_id':event['id'],'content_hash':event['content_hash'],'reviewer':args.reviewer,'labels':labels,'created_at':now()}])
        tag={**baseline(event),**labels,'method':'human','model_version':None,'review_status':'approved'}
        db.upsert('event_tags',[tag],key='event_id')
    else:
        processed=0
        for t in tags:
            if t['review_status']!='pending' or t['method']=='model': continue
            try: candidate=model_candidate(events[t['event_id']])
            except Exception: continue
            if candidate: db.upsert('event_tags',[candidate],key='event_id'); processed+=1
        print(f'Model candidates stored: {processed}; all require human review')
if __name__=='__main__':main()
