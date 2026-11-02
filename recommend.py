from datetime import datetime, timezone

def recommend(events, interests=(), saved_ids=(), audience=(), free_food=False, free_admission=False, limit=20, at=None):
    at=at or datetime.now(timezone.utc)
    tags=lambda e:set((e.get('tags') or {}).get('topics',[]))
    saved=set().union(*(tags(e) for e in events if e['id'] in saved_ids)) if saved_ids else set()
    candidates=[]; seen=set()
    for e in events:
        t=e.get('tags') or {}
        if e['status']!='active' or datetime.fromisoformat(e['start_at'])<at: continue
        if free_food and t.get('free_food')!='yes': continue
        if free_admission and t.get('free_admission')!='yes': continue
        if t.get('audience_restricted')=='yes' and (not t.get('audience') or not set(t['audience']).issubset(set(audience))): continue
        if e['duplicate_key'] in seen: continue
        seen.add(e['duplicate_key'])
        matches=tags(e)&set(interests); similarity=len(tags(e)&saved)/max(1,len(tags(e)|saved))
        score=2*len(matches)+similarity
        reason='Matches your '+', '.join(sorted(matches))+' interests.' if matches else ('Similar to saved event topics.' if similarity else 'Upcoming campus event.')
        candidates.append((score,e,reason))
    selected=[]; organizers={}; topics={}
    while candidates and len(selected)<limit:
        def rank(c):
            score,e,_=c; org='|'.join(e['organizers']) or e['source_id']
            penalty=.4*organizers.get(org,0)+.15*sum(topics.get(t,0) for t in tags(e))
            return (-score+penalty,e['start_at'],e['id'])
        best=min(candidates,key=rank); candidates.remove(best); score,e,reason=best
        org='|'.join(e['organizers']) or e['source_id']; organizers[org]=organizers.get(org,0)+1
        for t in tags(e): topics[t]=topics.get(t,0)+1
        selected.append({**e,'recommendation_score':score,'explanation':reason})
    return selected
