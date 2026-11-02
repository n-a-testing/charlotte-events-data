"""D2 figures and frozen, group-disjoint holdout from observed records."""
import json
from collections import Counter
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pipeline import BASE, now
from tagging import baseline

def frame(events):
    rows=[]
    for e in events:
        t=e.get('tags') or baseline(e)
        rows.append({**e,**{k:t[k] for k in ['topics','free_food','free_admission','registration_required']}})
    df=pd.DataFrame(rows)
    df['campus_start']=pd.to_datetime(df.start_at,utc=True).dt.tz_convert('America/New_York')
    return df

def plots(df):
    figures=[]
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    def bar(series,title,xlabel):
        fig,ax=plt.subplots(figsize=(9,4.2)); series.sort_values().plot.barh(ax=ax,color='#00703c'); ax.set(title=title,xlabel=xlabel); fig.tight_layout(); figures.append(fig)
    cats=df.explode('source_categories').source_categories.fillna('Uncategorized').value_counts().head(12)
    bar(cats,'Source categories — top 12 (multi-label)','Source occurrence records')
    heat=pd.crosstab(df.campus_start.dt.dayofweek,df.campus_start.dt.hour).reindex(index=range(7),columns=range(24),fill_value=0)
    fig,ax=plt.subplots(figsize=(10,4.2)); im=ax.imshow(heat,aspect='auto',cmap='Greens'); ax.set(yticks=range(7),yticklabels=['Mon','Tue','Wed','Thu','Fri','Sat','Sun'],xticks=range(0,24,2),xlabel='Campus start hour (America/New_York)',title='Weekday and start time — source occurrence records'); fig.colorbar(im,ax=ax,label='Records'); fig.tight_layout(); figures.append(fig)
    missing=pd.Series({k:int(df[k].apply(lambda v: v is None or v=='' or v==[]).sum()) for k in ['description','end_at','location','organizers','source_categories','series_id']})
    bar(missing,'Missing structured fields','Records with missing values')
    facts=pd.DataFrame({k:df[k].value_counts().reindex(['yes','no','unknown'],fill_value=0) for k in ['free_admission','free_food','registration_required']}).T
    fig,ax=plt.subplots(figsize=(9,4.2)); facts.plot.barh(stacked=True,ax=ax,color=['#00703c','#b33b3b','#b8b8b8']); ax.set(title='Explicit factual evidence — conservative keyword baseline',xlabel='Records'); ax.legend(loc='lower right'); fig.tight_layout(); figures.append(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4.2)); df.source_id.value_counts().plot.barh(ax=axes[0],color='#00703c'); org=df.explode('organizers').organizers.fillna('Unknown').value_counts().head(8); org.sort_values().plot.barh(ax=axes[1],color='#a49665'); axes[0].set_title('Source coverage'); axes[1].set_title('Top organizers (multi-organizer)'); fig.tight_layout(); figures.append(fig)
    return figures

def freeze(events):
    target=BASE/'data/split_manifest.json'
    if target.exists(): return json.loads(target.read_text())
    parent={e['id']:e['id'] for e in events}
    def root(x):
        while parent[x]!=x: parent[x]=parent[parent[x]]; x=parent[x]
        return x
    seen={}
    for e in events:
        for field in ['related_group','series_id','duplicate_key']:
            if not e[field]: continue
            key=(field,e[field])
            if key in seen: parent[root(e['id'])]=root(seen[key])
            else: seen[key]=e['id']
    groups={}
    for e in events: groups.setdefault(root(e['id']),[]).append(e)
    ordered=sorted(groups.items(),key=lambda kv:min(e['start_at'] for e in kv[1]))
    rows=[]; n=len(ordered)
    for i,(group,items) in enumerate(ordered):
        split='train' if i<int(n*.6) else 'validation' if i<int(n*.8) else 'test'
        rows.extend({'event_id':e['id'],'group_id':group,'split':split,'frozen_at':now()} for e in items)
    target.write_text(json.dumps(rows,indent=2)); return rows

def main():
    events=json.loads((BASE/'data/events.json').read_text()); df=frame(events); freeze(events)
    (BASE/'reports').mkdir(exist_ok=True)
    for i,fig in enumerate(plots(df),1): fig.savefig(BASE/f'reports/figure-{i}.png',dpi=160); plt.close(fig)
    stats={'records':len(df),'sources':df.source_id.value_counts().to_dict(),'status':df.status.value_counts().to_dict(), 'start_min':str(df.campus_start.min()),'start_max':str(df.campus_start.max()),'missing':{k:int(df[k].apply(lambda v:v is None or v=='' or v==[]).sum()) for k in ['description','end_at','location','organizers','source_categories','series_id']},'facts':{k:df[k].value_counts().to_dict() for k in ['free_food','free_admission','registration_required']},'top_categories':df.explode('source_categories').source_categories.value_counts().head(5).to_dict(),'top_organizers':df.explode('organizers').organizers.value_counts().head(5).to_dict(),'duplicate_key_excess':int(df.duplicate_key.duplicated().sum()),'weekday':df.campus_start.dt.day_name().value_counts().to_dict(),'splits':dict(Counter(r['split'] for r in freeze(events)))}
    (BASE/'reports/statistics.json').write_text(json.dumps(stats,indent=2)); print(json.dumps(stats,indent=2))
if __name__=='__main__':main()
