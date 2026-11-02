"""Replayable ingestion: archive first, normalize second, publish last."""
from __future__ import annotations
import argparse, hashlib, json, re, uuid
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

SOURCES = {'ninerengage': 'https://ninerengage.charlotte.edu/events.rss',
           'campusevents': 'https://campusevents.charlotte.edu/calendar.xml'}
BASE = Path(__file__).parent

def now(): return datetime.now(timezone.utc).isoformat()
def digest(value): return hashlib.sha256(value.encode()).hexdigest()
def session():
    s = requests.Session()
    s.headers['User-Agent'] = 'CharlotteEventsResearch/1.0 (public event data ingestion)'
    s.mount('https://', HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1, status_forcelist=[429,500,502,503,504], allowed_methods=['GET','POST'])))
    return s

def clean(value):
    soup = BeautifulSoup(value or '', 'html.parser')
    for tag in soup(['script','style']): tag.decompose()
    return ' '.join(soup.get_text(' ', strip=True).split())

def url(value):
    p = urlsplit(value or '')
    if p.scheme not in ('https','http') or not p.netloc: raise ValueError('Missing/unsafe event URL')
    return urlunsplit((p.scheme,p.netloc.lower(),p.path.rstrip('/'),p.query,''))

def date(value):
    if not value: return None
    try: dt = datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError: dt = parsedate_to_datetime(value)
    if dt.tzinfo is None: raise ValueError('Timezone missing; no guessing DST')
    return dt.astimezone(timezone.utc).isoformat()

def normalize(item, source, collected_at):
    get = lambda key: item.findtext(key) or ''
    identifier = get('guid')
    if not identifier: raise ValueError('Missing stable source GUID')
    title, link = clean(get('title')), url(get('link'))
    soup = BeautifulSoup(get('description'), 'html.parser')
    if source == 'ninerengage':
        desc = soup.select_one('.p-description')
        description = clean(str(desc)) if desc else clean(get('description'))
        start, end = date(get('{events}start')), date(get('{events}end'))
        location = clean(get('{events}location')) or None
        organizers = sorted(set(clean(n.text) for n in item.findall('{events}host') if n.text))
        status = {'confirmed':'active','cancelled':'cancelled','canceled':'cancelled'}.get(get('{events}status').lower(),'unknown')
        series = None  # feed does not expose a trustworthy recurrence-series ID
        provenance = 'events:start'
    else:
        for a in soup.select('a[href^="mailto:"]'):
            if a.parent: a.parent.decompose()
        description = clean(str(soup))
        start, end = date(get('{http://purl.org/dc/elements/1.1/}date')), None
        title = re.sub(r'^\w{3} \d{1,2}, \d{4}:\s*', '', title)
        # Preserve title venue suffix: not a structured location field.
        location = None
        host = re.search(r'Hosted by:\s*(.*?)(?:Additional Information|$)',description)
        organizers = [host.group(1).strip()] if host else []
        status = 'cancelled' if re.search(r'\b(cancelled|canceled)\b',title,re.I) else 'active'
        series, provenance = link, 'dc:date'
    if not title or not start: raise ValueError('Missing title or explicit event start')
    if end and end < start: raise ValueError('End before start')
    categories = sorted(set(clean(n.text) for n in item.findall('category') if n.text))
    group_title = re.sub(r'\s*\(cancelled\)\s*','',title,flags=re.I).lower()
    group_title = re.sub(r'\s+at\s+.*$','',group_title)
    group = digest(group_title)  # conservative related-title grouping, not asserted series
    cross = re.search(r'https://ninerengage\.charlotte\.edu/event/\d+', get('description'))
    canonical = cross.group(0) if cross else link
    event = dict(id=digest(source+':'+identifier), source_id=source, source_identifier=identifier,
        title=title, description=description, url=link, start_at=start, end_at=end,
        date_provenance=provenance, location=location, organizers=organizers, source_categories=categories,
        status=status, series_id=series, related_group=group,
        duplicate_key=digest(canonical+'|'+start),
        quality_flags=([f'missing_{k}' for k,v in [('end',end),('location',location),('organizer',organizers),('description',description)] if not v]
          + (['midnight_time_unconfirmed'] if datetime.fromisoformat(start).astimezone(__import__('zoneinfo').ZoneInfo('America/New_York')).hour == 0 else [])
          + (['no_explicit_series_id'] if series is None else [])),
        first_seen_at=collected_at,last_seen_at=collected_at,updated_at=collected_at)
    significant = {k:v for k,v in event.items() if k not in ('first_seen_at','last_seen_at','updated_at')}
    event['content_hash'] = digest(json.dumps(significant,sort_keys=True))
    return event

def collect(source):
    response = session().get(SOURCES[source], timeout=(10,60)); response.raise_for_status()
    stamp = now(); folder=BASE/'data/raw'/stamp.replace(':','-'); folder.mkdir(parents=True,exist_ok=True)
    path=folder/(source+'.xml'); path.write_bytes(response.content)
    path.with_suffix('.json').write_text(json.dumps({'source_url':SOURCES[source],'collected_at':stamp,'http_status':response.status_code},indent=2))
    return path

def prepare(path, source):
    stamp = json.loads(path.with_suffix('.json').read_text())['collected_at']
    run = dict(id=str(uuid.uuid4()),source_id=source,started_at=stamp,finished_at=None,status='running',received=0,accepted=0,rejected=0,error=None)
    rows=[]
    for item in ET.fromstring(path.read_bytes()).findall('./channel/item'):
        original=ET.tostring(item,encoding='unicode'); rawhash=digest(original)
        raw=dict(id=digest(source+rawhash),source_id=source,source_identifier=item.findtext('guid'),content_hash=rawhash,collected_at=stamp,run_id=run['id'],original_xml=original,error=None)
        event=None
        try:
            event=normalize(item,source,stamp); event['raw_record_id']=raw['id']
        except (ValueError,TypeError,OverflowError) as exc: raw['error']=str(exc)
        rows.append((raw,event))
    run.update(received=len(rows),accepted=sum(e is not None for _,e in rows),rejected=sum(e is None for _,e in rows),finished_at=now(),status='success')
    return run,rows

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--replay',type=Path); parser.add_argument('--export',action='store_true'); args=parser.parse_args()
    from storage import publish, export_sql
    all_events=[]
    for source in SOURCES:
        try:
            path=args.replay/(source+'.xml') if args.replay else collect(source)
            run,rows=prepare(path,source)
            (export_sql if args.export else publish)(source,run,rows)
            all_events.extend(e for _,e in rows if e)
            print(json.dumps({k:v for k,v in run.items() if k!='id'}))
        except Exception as exc:
            # Always durable local failure report; do not imply successful refresh.
            failure={'source':source,'failed_at':now(),'error':type(exc).__name__+': '+str(exc)}
            with (BASE/'data/failures.jsonl').open('a') as f: f.write(json.dumps(failure)+'\n')
            raise
    (BASE/'data/events.json').write_text(json.dumps(all_events,indent=2))
if __name__=='__main__': main()
