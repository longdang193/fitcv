import json, pathlib
ids=['4d83ef03-4acc-4acd-8ea6-240127a21098','5656eb4d-34ec-4445-938d-f49ebadb8e14','84c1c6a2-4b5f-49d6-991c-b3197e94f1bb']

print('=== SETTINGS DRIFT CHECK ===')
keys=[
 'ai_score_top_n','final_top_n','fit_label_thresholds',
 'reuse.ranking.enabled','reuse.enrich.enabled','reuse.cv_analysis.enabled','reuse.cv_generation.enabled',
 'ranking_concurrency','cv_analysis_concurrency','cv_generation_concurrency'
]
vals={}
for rid in ids:
    p=pathlib.Path(f'tmp/{rid}.settings-used.json')
    d=json.loads(p.read_text(encoding='utf-8'))
    v={k:d.get(k) for k in keys}
    vals[rid]=v
    print('\nRUN',rid)
    for k in keys:
        print(' ',k,'=',v[k])

print('\n=== STAGE ARTIFACTS CHECK ===')
for rid in ids:
    p=pathlib.Path(f'tmp/{rid}.stage-artifacts.json')
    d=json.loads(p.read_text(encoding='utf-8'))
    # artifacts might be list or dict keyed by stage
    stage_map={}
    if isinstance(d,list):
        for item in d:
            sid=item.get('stage_id') or item.get('stage')
            if sid: stage_map[sid]=item
    elif isinstance(d,dict):
        if 'artifacts' in d and isinstance(d['artifacts'],list):
            for item in d['artifacts']:
                sid=item.get('stage_id') or item.get('stage')
                if sid: stage_map[sid]=item
        else:
            stage_map=d
    print('\nRUN',rid)
    rank=stage_map.get('ranking') or {}
    decision=rank.get('decision_summary') or {}
    ld=decision.get('label_distribution') or {}
    rm=decision.get('reuse_metrics') or {}
    print(' ranking.label_distribution=',ld)
    print(' ranking.reuse_metrics=',rm)
    shortlist=stage_map.get('shortlist') or {}
    s_out=shortlist.get('output_snapshot') or {}
    print(' shortlist.output_snapshot=',{k:s_out.get(k) for k in ['shortlisted_jobs','scoring_shortlist_jobs','backfilled_jobs']})
    cva=stage_map.get('cv_analysis') or {}
    cvd=cva.get('decision_summary') or {}
    print(' cv_analysis.quality_metrics=',cvd.get('quality_metrics'))
