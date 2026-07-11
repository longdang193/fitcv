import json, pathlib

rids=['4d83ef03-4acc-4acd-8ea6-240127a21098','5656eb4d-34ec-4445-938d-f49ebadb8e14','84c1c6a2-4b5f-49d6-991c-b3197e94f1bb']


def load_stage(rid):
    d=json.loads(pathlib.Path(f'tmp/{rid}.stage-artifacts.json').read_text(encoding='utf-8'))
    return ((d.get('artifacts') or {}).get('stages') or {})


def ranking_inputs_map(stages):
    ranking=stages.get('ranking') or {}
    # try full rows from outputs_sample / output_records
    candidates=[]
    for key in ['outputs_sample','output_records','records_sample','output_rows_sample','sample_rows']:
        v=ranking.get(key)
        if isinstance(v,list) and v:
            candidates=v; break
    # fall back to stage_result.output if present
    if not candidates:
        out=((ranking.get('stage_result') or {}).get('output') or {})
        for key in ['ranked_jobs_sample','ranking_inputs_sample','rows_sample']:
            v=out.get(key) if isinstance(out,dict) else None
            if isinstance(v,list) and v:
                candidates=v; break
    m={}
    for row in candidates:
        if not isinstance(row,dict):
            continue
        u=str(row.get('job_url') or row.get('url') or '').strip()
        if not u: 
            continue
        fit=str(row.get('fit_label') or row.get('ranking_fit_label') or '').strip().lower()
        reuse=str(row.get('ai_score_reuse_status') or '').strip().lower()
        m[u]={'fit':fit,'reuse':reuse}
    return m, len(candidates)


def enriched_urls(stages):
    s=stages.get('enrich') or {}
    rows=[]
    for key in ['outputs_sample','output_records','records_sample']:
        v=s.get(key)
        if isinstance(v,list) and v:
            rows=v; break
    out=((s.get('stage_result') or {}).get('output') or {})
    if not rows and isinstance(out,dict):
        for key in ['enriched_rows_sample','rows_sample']:
            v=out.get(key)
            if isinstance(v,list) and v:
                rows=v; break
    urls=set()
    for r in rows:
        if isinstance(r,dict):
            u=str(r.get('job_url') or '').strip()
            if u: urls.add(u)
    return urls,len(rows)

st=[load_stage(r) for r in rids]

# headline from quality metrics
print('=== HEADLINE METRICS ===')
for rid,stages in zip(rids,st):
    q=((stages.get('ranking') or {}).get('stage_result') or {}).get('evidence',{}).get('decision_summary',{}).get('quality_metrics',{})
    ld=q.get('label_distribution') or {}
    rm=((stages.get('ranking') or {}).get('stage_result') or {}).get('evidence',{}).get('decision_summary',{}).get('reuse_metrics',{})
    print(rid, 'skip',ld.get('skip_count'),'/',ld.get('total_scored'),'stretch',ld.get('stretch_count'),'reuse',rm.get('reused_ai_scores'),'fresh',rm.get('fresh_ai_scores'))

# sample-level overlap if rows available
maps=[]
for rid,stages in zip(rids,st):
    m,n=ranking_inputs_map(stages)
    maps.append(m)
    print(f'RUN {rid} ranking sample rows captured={n}, mapped_urls={len(m)}')

if all(len(m)>0 for m in maps):
    r1,r2,r3=maps
    s1,s2,s3=set(r1),set(r2),set(r3)
    print('=== RANKING SAMPLE OVERLAP ===')
    print('r1∩r2',len(s1&s2),'r2-only',len(s2-s1),'r3∩r2',len(s3&s2),'r3-only-vs-r2',len(s3-s2))
    def stats(base,new):
        inter=set(base)&set(new)
        only=set(new)-set(base)
        def pct_skip(d,keys):
            if not keys: return (0,0,0)
            skip=sum(1 for k in keys if d[k]['fit']=='skip')
            return skip,len(keys),round(skip/len(keys),3)
        return pct_skip(new,inter), pct_skip(new,only)
    inter2,only2=stats(r1,r2)
    inter3,only3=stats(r2,r3)
    print('run2 overlap_with_run1 skip',inter2,'run2 new_vs_run1 skip',only2)
    print('run3 overlap_with_run2 skip',inter3,'run3 new_vs_run2 skip',only3)
else:
    print('No full ranking row samples in stage artifacts; cannot do per-url fit transition from artifacts alone.')
