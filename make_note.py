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
base(1,'Sources, provenance and cleaning')
y=690
y=para('<b>Scope.</b> This foundation ingests two official university feeds into Supabase and supplies a read-only Streamlit dashboard and JSON API. The dataset is a collection of source-listed occurrences, not a census of campus activity or a measure of attendance.',y)
y=heading('Measured snapshot',y)
y=para(f"The snapshot contains <b>{S['records']:,} records</b>: 638 from Niner Engage and 849 from the campus calendar (Localist). All passed required identifier/title/start-date checks. There are <b>17 explicit cancellations</b>. Starts range from December 18, 2024 to May 13, 2027. The historical tail demonstrates why source-listed active status alone is insufficient for recommendations.",y)
y=heading('Collection and reproducibility',y)
y=para('Original feed bytes and collection metadata were saved before transformation. Raw item XML, source GUIDs, collection timestamps and raw hashes are stored privately in Supabase. Stable source-plus-GUID event IDs prevent repeated ingestion from adding occurrences. Normalized content hashes exclude volatile publication clocks; changes update existing IDs. Timeouts and retry/backoff handle transient failures. Failed collection or publication is recorded without claiming a successful refresh.',y)
y=heading('Dates, recurrence and duplicate handling',y)
y=para('Engage exposes explicit start/end instants, status, venue and hosts. Localist exposes dc:date and an occurrence GUID, while a shared event URL links its recurring series. RSS publication dates are never substituted for starts. All instants are timezone-aware, stored as UTC and displayed in America/New_York. Engage lacks explicit series IDs; title-based related groups are only a conservative split safeguard.',y)
y=para('Three excess records share exact cross-source URL/start keys; these remain traceable in storage and are collapsed for recommendations. No fuzzy deduplication is asserted. Disappearance from a rolling feed never marks cancellation. Unknown end times and structured venues stay NULL; midnight does not automatically mean all-day. Some listings describe registration periods rather than the later activity, so source detail pages remain authoritative.',y)
y=heading('Sources and companion artifacts',y)
y=para('Official feeds: ninerengage.charlotte.edu/events.rss and campusevents.charlotte.edu/calendar.xml. Companion files: DATA_DICTIONARY.md (every database field), statistics.json (measured counts), figure-1.png through figure-5.png, and the frozen split manifest. The dashboard reads Supabase directly; no fixture fallback is used.',y)
c.showPage()
base(2,'Five views of the observed data')
y=690
y=para('<b>1. Categories.</b> ThoughtfulLearning occurs on 420 records, followed by Social (165) and Academic Calendar (142). Categories are multi-label and source-defined: these counts reflect how feeds classify listings, not independent student preferences.',y)
y=fig('figure-1.png',y,155)
y=para('<b>2. Weekday/time.</b> Tuesday has 363 records and Monday 339, versus 33 on Sunday. Weekday-heavy academic programming and recurring listings likely drive this pattern. Midnight bins include records with uncertain time specificity, so they are not evidence of overnight attendance.',y)
y=para('<b>3. Missing fields.</b> 849 records lack structured end time and venue; 850 lack organizers, 463 lack categories and 159 lack usable descriptions. These are largely source-coverage limitations. A title venue suffix is not silently treated as a verified structured venue.',y)
y=fig('figure-3.png',y,150)
y=para('<b>4. Free food/admission.</b> Conservative rules find 15 explicit free-food positives, 5 free-admission positives and 32 registration requirements. All remaining values are unknown, not negative. These counts are unreviewed extraction results, not measured classifier accuracy.',y)
y=para('<b>5. Coverage.</b> Localist supplies 57.1% of records. The University Center for Academic Excellence appears as organizer on 344 records, making repeated academic support sessions prominent. Organizer totals can overlap when multiple hosts are listed. All five full-size plots are included separately.',y)
c.showPage()
base(3,'Evaluation, limitations and readiness')
y=690
y=heading('Holdout reserved before model tuning',y)
y=para('A frozen manifest groups shared series URLs, normalized related titles and exact duplicate keys before assignment. Groups are ordered by earliest start and allocated 60/20/20 to train/validation/test, yielding 1,102/206/179 records. Large recurring groups skew record proportions. This is approximate chronological separation: a long series may span later groups. Near-duplicate audit remains necessary before training.',y)
y=heading('Controlled labels and recommendation foundation',y)
y=para('Topics, format, food, admission, registration and audience restrictions are separate fields. Facts require exact supporting source quotes and yes/no/unknown values. The keyword baseline is pending review. A configurable model adapter accepts only schema-valid evidence-backed candidates; unavailable or failed model access leaves ingestion functional. No external model inference or human-label accuracy result is claimed.',y)
y=para('Recommendations use explicit interests and saved-event topic similarity, filter upcoming active records and known eligibility restrictions, and penalize repeated organizers/topics for variety. Explanations expose matches. Score weights are provisional, not validated. Existing app local preferences are untouched; no mandatory account or persistent interaction collection was added.',y)
y=heading('What can be evaluated later',y)
y=para('Human reviewers should label a stratified sample independently of model predictions and adjudicate disagreements. Fit TF-IDF and one logistic-regression classifier per tag on reviewed training data only; choose thresholds on validation and report per-tag precision, recall and F1 on the locked test set when support permits. Compare recommendations with an upcoming-events baseline using genuine relevance feedback and nDCG@10/recall@10. No such measured results exist yet.',y)
y=heading('Limitations and operational handoff',y)
y=para('Rolling feed windows, missing fields, syndicated events, recurring programs and stale historical listings limit representativeness. Public listings can omit student-only activities and details available after sign-in. Keyword positives may still need human correction, and restriction extraction is intentionally conservative. Descriptions are untrusted data, never instructions.',y)
y=para('Supabase RLS protects raw records, ingestion runs, reviews and split assignments; public catalog tables are read-only. The dashboard uses a publishable key. Privileged refresh and review require a server-only credential. Deployment URLs and the current refresh status are recorded in README.md; verification results are in reports/live-verification.json. Automated refresh is not asserted unless its server secret is configured and a run succeeds.',y)
c.save();print(out)
