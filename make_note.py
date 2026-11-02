"""Build the three-page D2 submission note from measured snapshot statistics."""
from pathlib import Path
import json
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
P=Path(__file__).parent; S=json.loads((P/'reports/statistics.json').read_text())
out=P/'reports/D2-data-note.pdf'; c=canvas.Canvas(str(out),pagesize=(612,792)); c.setTitle('UNC Charlotte Events - D2 Data Note')
style=ParagraphStyle('body',fontName='Helvetica',fontSize=10.4,leading=14,textColor=HexColor('#24342e'))
def base(page,title):
 c.setFillColor(HexColor('#00703c'));c.rect(0,756,612,36,fill=1,stroke=0); c.setFillColor(HexColor('#ffffff'));c.setFont('Helvetica-Bold',10);c.drawString(42,769,'CHARLOTTE EVENT OBSERVATORY  /  D2')
 c.setFillColor(HexColor('#163b2b'));c.setFont('Helvetica-Bold',21);c.drawString(42,720,title)
 c.setFont('Helvetica',9);c.setFillColor(HexColor('#65736a'));c.drawString(42,32,'Snapshot collected November 2, 2026 | Campus timezone: America/New_York');c.drawRightString(570,32,str(page))
def para(text,y):
 p=Paragraph(text,style);w,h=p.wrap(528,700);p.drawOn(c,42,y-h);return y-h-13
def heading(text,y):
 c.setFillColor(HexColor('#00703c'));c.setFont('Helvetica-Bold',12);c.drawString(42,y,text);return y-12
def fig(name,y,h):
 img=ImageReader(str(P/'reports'/name));w0,h0=img.getSize();w=min(528,h*w0/h0);c.drawImage(img,42+(528-w)/2,y-h,width=w,height=h,preserveAspectRatio=True);return y-h-12
base(1,'Niner Engage: scope and provenance')
y=690
y=para('<b>Current scope.</b> This revision uses only the official UNC Charlotte Niner Engage RSS feed. Campus-calendar collection is disabled. Its historical records remain preserved in Supabase but are excluded from the dashboard, API, review queue and current D2 analysis. No new collection is claimed by this scope change.',y)
y=heading('Measured snapshot',y)
y=para(f"The November 2, 2026 snapshot contains <b>{S['records']} Niner Engage occurrences</b>, with 622 source-listed active records and 16 explicit cancellations. All passed required identifier/title/start-date validation. Starts range from December 18, 2024 to December 2, 2026. Older ongoing listings can appear in the feed; upcoming recommendations use an explicit start-time filter.",y)
y=heading('Collection, updates and source lineage',y)
y=para('The source is https://ninerengage.charlotte.edu/events.rss. Original feed bytes and collection timestamps were archived before transformation. Raw item XML, source GUIDs, collection timestamps and content hashes are stored privately in Supabase. Stable source-plus-GUID IDs update an existing occurrence when its content changes. Substantive hashes exclude volatile publication timestamps. Repeated imports preserve first-seen time and unchanged reviewed labels.',y)
y=para('Collection uses timeouts, retry/backoff and durable error reporting. A failed publication does not claim a successful source refresh. The dashboard reads Supabase directly using a publishable key; there is no fixture fallback. Daily refresh remains off at the user request, with a separate deployment ready for later server-secret configuration.',y)
y=heading('Dates, recurrence and cleaning decisions',y)
y=para('Event starts and ends come from explicit events:start and events:end fields, never RSS pubDate. Dates are timezone-aware, stored as UTC and displayed in America/New_York. Cancellation comes from the explicit source status. Disappearance from a rolling feed does not imply cancellation. Every current record has a description, structured start/end, venue and category; 12 records lack an organizer.',y)
y=para('The feed does not expose a trustworthy shared recurrence-series ID. All 638 series_id values therefore remain NULL. Each source GUID remains a separate occurrence; normalized-title related groups help protect evaluation partitions without asserting factual recurrence. There are zero duplicate-key excess records within this active snapshot. Source pages remain authoritative for changing details.',y)
c.showPage()
base(2,'Five views of Niner Engage')
y=690
y=para('<b>1. Categories.</b> ThoughtfulLearning appears on 420 records, Social on 136, and Workshop on 53. Categories are multi-label. Academic support programming dominates this observed feed; category frequencies are not a measure of student demand.',y)
y=fig('figure-1.png',y,155)
y=para('<b>2. Weekday/time.</b> Tuesday has 174 records and Monday 155, compared with 11 on Sunday. This pattern is consistent with weekday academic programming, but recurring sessions increase counts. Midnight timestamps are not automatically interpreted as all-day events.',y)
y=para('<b>3. Missing fields.</b> No descriptions, end times, locations or categories are missing in this snapshot. Twelve records lack an organizer, and all 638 lack an explicit shared series identifier. The latter is a source limitation, not a parser failure.',y)
y=fig('figure-3.png',y,150)
y=para('<b>4. Free food/admission.</b> Conservative keyword rules identify 8 explicit free-food positives, 1 free-admission positive and 7 registration requirements. All other values are unknown, not negative. These are unreviewed extraction counts, not accuracy estimates.',y)
y=para('<b>5. Organizer coverage.</b> Niner Engage is now the only active source. The University Center for Academic Excellence is listed on 344 records, followed by Dimensions of Wellness on 32 and Counseling and Psychological Services on 20. Multiple hosts can overlap. All five full-size plots accompany this note.',y)
c.showPage()
base(3,'Evaluation and operational limits')
y=690
y=heading('Frozen assignments preserved',y)
y=para('Before model tuning, the original two-source split grouped related titles, series URLs and exact duplicate keys, then ordered groups by earliest start. This scope revision selects Niner Engage records without changing any assignment: <b>558 train, 72 validation and 8 test</b>. The original immutable manifest remains available; active_split_manifest.json records the selected subset.',y)
y=para('The resulting test subset is too small and unreviewed to support credible per-tag quality claims. Group chronology is approximate because recurring groups can span later groups. Obtain more independent human-reviewed groups and pre-register any future split revision before tuning. Do not reshuffle based on observed outcomes. Audit near-duplicates before training.',y)
y=heading('Tagging and recommendations',y)
y=para('Topic, format, admission, food, registration and audience are separate fields. Factual attributes use yes/no/unknown and require exact supporting source quotes. Missing evidence stays unknown; free admission never implies free food. Validation rejects cropped negation. Current labels are keyword candidates pending human review. A configurable model adapter exists, but no external model inference or measured accuracy is claimed.',y)
y=para('Recommendations rank upcoming active events using explicit interest matches and saved-event topic similarity, with provisional diversity penalties across organizers and topics. Known eligibility restrictions and explicit factual filters are respected. Explanations expose interest matches. Existing browser-local preferences remain untouched. There is no mandatory account or persistent interaction tracking.',y)
y=heading('Later evaluation and privacy',y)
y=para('Human reviewers should annotate independently of predictions and adjudicate disagreements. Fit TF-IDF plus one logistic-regression classifier per topic on reviewed training data only, tune on validation, and report per-tag precision/recall/F1 only when test support is adequate. Compare recommendation relevance against an upcoming-events baseline with genuine feedback. No measured evaluation findings exist yet.',y)
y=para('RLS restricts raw records, ingestion runs, reviews and split assignments. The public app uses read-only access and filters to Niner Engage; historical campus-calendar rows remain in Supabase for provenance. Source windows, recurring academic sessions, stale listings and unobserved private events limit representativeness. See DATA_DICTIONARY.md, EVALUATION.md, README.md and reports/live-verification.json for field definitions, run instructions and actual checks.',y)
c.save();print(out)
