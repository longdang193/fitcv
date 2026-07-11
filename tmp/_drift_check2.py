import json, pathlib
ids=['4d83ef03-4acc-4acd-8ea6-240127a21098','5656eb4d-34ec-4445-938d-f49ebadb8e14','84c1c6a2-4b5f-49d6-991c-b3197e94f1bb']

print('=== SETTINGS (effective_settings) ===')
keys=['ai_score_top_n','final_top_n','fit_label_thresholds','ranking_concurrency','cv_analysis_concurrency','cv_generation_concurrency']
reuse_keys=['enrich','ranking','cv_analysis','cv_generation']
for rid in ids:
    d=json.loads(pathlib.Path(f'tmp/{rid}.settings-used.json').read_text(encoding='utf-8'))
    eff=d.get('effective_settings') or {}
    print('\nRUN',rid)
    for k in keys:
        print(' ',k,'=',eff.get(k))
    reuse=eff.get('reuse') or {}
    for rk in reuse_keys:
        rv=(reuse.get(rk) or {}).get('enabled') if isinstance(reuse.get(rk),dict) else None
        print(f' reuse.{rk}.enabled =',rv)

print('\n=== STAGE ARTIFACTS (ranking/cv_analysis) ===')
for rid in ids:
    d=json.loads(pathlib.Path(f'tmp/{rid}.stage-artifacts.json').read_text(encoding='utf-8'))
    stages=((d.get('artifacts') or {}).get('stages') or {})
    ranking=stages.get('ranking') or {}
    cva=stages.get('cv_analysis') or {}
    rs=(ranking.get('stage_result') or {})
    cs=(cva.get('stage_result') or {})
    r_dec=((rs.get('evidence') or {}).get('decision_summary') or {})
    c_dec=((cs.get('evidence') or {}).get('decision_summary') or {})
    print('\nRUN',rid)
    print(' ranking.label_distribution =', r_dec.get('label_distribution'))
    print(' ranking.reuse_metrics =', r_dec.get('reuse_metrics'))
    print(' ranking.output_counts =', ranking.get('output_counts'))
    print(' cv_analysis.quality_metrics =', c_dec.get('quality_metrics'))
    print(' cv_analysis.reuse_metrics =', c_dec.get('reuse_metrics'))
