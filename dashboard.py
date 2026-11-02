import streamlit as st
import pandas as pd
from storage import load_catalog
from analysis import frame, plots
from recommend import recommend
from tagging import TOPICS
st.set_page_config(page_title='Charlotte Event Observatory',page_icon='🟢',layout='wide')
st.title('Charlotte Event Observatory')
st.caption('UNC Charlotte Niner Engage public events · D2 data foundation · Campus times: America/New_York')
@st.cache_data(ttl=120)
def fetch(): return load_catalog()
if st.button('Refresh from Supabase'): fetch.clear()
try: events,sources=fetch()
except Exception:
    st.error('Supabase could not be read. Check server configuration and database availability.'); st.stop()
if not events: st.info('No ingested records yet.'); st.stop()
st.caption('Last successful collection: '+' · '.join(s['name']+': '+(pd.Timestamp(s['last_success_at']).tz_convert('America/New_York').strftime('%b %d, %Y %I:%M %p %Z') if s.get('last_success_at') else 'Not yet') for s in sources))
df=frame(events)
a,b,c=st.columns(3); a.metric('Source occurrence records',len(df)); b.metric('Cancelled',int((df.status=='cancelled').sum())); c.metric('Records with quality flags',int(df.quality_flags.map(bool).sum()))
st.info('Counts describe a rolling feed snapshot, not all campus activities. Tags are provisional keyword evidence unless human-approved. Missing information means unknown. Recurring listings remain separate occurrences; the campus-calendar feed is excluded.')
with st.sidebar:
    st.header('Browse filters')
    chosen=st.multiselect('Sources',sorted(df.source_id.unique()),default=sorted(df.source_id.unique()))
    status=st.multiselect('Status',sorted(df.status.unique()),default=['active'])
    dates=st.date_input('Campus date range',value=(df.campus_start.min().date(),df.campus_start.max().date()))
    query=st.text_input('Search title and description')
    food=st.checkbox('Explicit free-food evidence only')
    admission=st.checkbox('Explicit free-admission evidence only')
    interests=st.multiselect('Your interests (session only)',list(TOPICS))
    audience=st.multiselect('Eligibility you choose to disclose (session only)',['students','faculty','staff','graduate','undergraduate','members'])
filtered=df[df.source_id.isin(chosen)&df.status.isin(status)].sort_values('campus_start')
if len(dates)==2: filtered=filtered[(filtered.campus_start.dt.date>=dates[0])&(filtered.campus_start.dt.date<=dates[1])]
if query: filtered=filtered[(filtered.title+' '+filtered.description).str.contains(query,case=False,regex=False)]
if food: filtered=filtered[filtered.free_food=='yes']
if admission: filtered=filtered[filtered.free_admission=='yes']
tab1,tab2,tab3=st.tabs(['Browse events','Data quality & plots','Recommendations'])
with tab1:
    st.write(f'{len(filtered)} matching records')
    st.dataframe(filtered[['title','campus_start','location','source_id','status','free_food','free_admission','url']],hide_index=True,column_config={'url':st.column_config.LinkColumn('Source')})
    st.download_button('Download filtered CSV',filtered[['id','title','start_at','end_at','location','source_id','url']].to_csv(index=False),'charlotte-events.csv','text/csv')
with tab2:
    st.caption('Plots reflect the current filters. Category totals are multi-label; midnight records may represent all-day or unspecified-time listings.')
    if not filtered.empty:
        for fig in plots(filtered): st.pyplot(fig)
    st.dataframe(filtered[['title','quality_flags']],hide_index=True)
with tab3:
    allowed=set(filtered.id)
    recs=recommend([e for e in events if e['id'] in allowed],interests=interests,audience=audience,free_food=food,free_admission=admission)
    st.caption('Provisional rule-based ranking; no measured relevance result. Preferences are not saved to the database.')
    for event in recs:
        st.subheader(event['title']); st.write(event['explanation']); st.write(pd.Timestamp(event['start_at']).tz_convert('America/New_York').strftime('%a %b %d, %I:%M %p %Z')); st.link_button('Official event details',event['url'])
