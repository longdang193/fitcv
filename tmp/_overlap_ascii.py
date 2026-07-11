import json, pathlib
rids=['4d83ef03-4acc-4acd-8ea6-240127a21098','5656eb4d-34ec-4445-938d-f49ebadb8e14','84c1c6a2-4b5f-49d6-991c-b3197e94f1bb']

def load_stage(rid):
    d=json.loads(pathlib.Path(f'tmp/{rid}.stage-artifacts.json').read_text(encoding='utf-8'))
    return ((d.get('artifacts') or {}).get('stages') or {})

def ranking_map(stages):
    ranking=stages.get('ranking') or {}
    rows=ranking.get('outputs_sample') or []
    m={}
    for row in rows:
        if not isinstance(row,dict):
            continue
        u=str(row.get('job_url') or '').strip()
        if not u:
            continue
        m[u]={
            'fit': str(row.get('fit_label') or row.get('ranking_fit_label') or '').strip().lower(),
            'reuse': str(row.get('ai_score_reuse_status') or '').strip().lower(),
        }
    return m

st=[load_stage(r) for r in rids]
maps=[ranking_map(s) for s in st]
r1,r2,r3=maps
s1,s2,s3=set(r1),set(r2),set(r3)
print('overlap_r1_r2',len(s1 & s2),'r2_only',len(s2 - s1))
print('overlap_r2_r3',len(s2 & s3),'r3_only',len(s3 - s2))

def skip_stats(target,keys):
    if not keys:
        return (0,0,0.0)
    skip=sum(1 for k in keys if target[k]['fit']=='skip')
    return (skip,len(keys),round(skip/len(keys),3))

inter2=s1 & s2
only2=s2 - s1
inter3=s2 & s3
only3=s3 - s2
print('run2_skip_on_overlap_with_run1',skip_stats(r2,inter2))
print('run2_skip_on_new_vs_run1',skip_stats(r2,only2))
print('run3_skip_on_overlap_with_run2',skip_stats(r3,inter3))
print('run3_skip_on_new_vs_run2',skip_stats(r3,only3))

for name,data in [('run1',r1),('run2',r2),('run3',r3)]:
    vals=list(data.values())
    reused=sum(1 for v in vals if v['reuse']=='reused_exact_match')
    fresh=sum(1 for v in vals if v['reuse']=='fresh_compute')
    skip=sum(1 for v in vals if v['fit']=='skip')
    print(name,'sample_rows',len(vals),'reused',reused,'fresh',fresh,'skip',skip)
