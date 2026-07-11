import json, pathlib
ids=['4d83ef03-4acc-4acd-8ea6-240127a21098','5656eb4d-34ec-4445-938d-f49ebadb8e14','84c1c6a2-4b5f-49d6-991c-b3197e94f1bb']
for rid in ids:
    d=json.loads(pathlib.Path(f'tmp/{rid}.stage-artifacts.json').read_text(encoding='utf-8'))
    ranking=((d.get('artifacts') or {}).get('stages') or {}).get('ranking') or {}
    dec=(((ranking.get('stage_result') or {}).get('evidence') or {}).get('decision_summary') or {})
    qm=dec.get('quality_metrics') or {}
    print('\nRUN',rid)
    print(' ranking_fit_label_counts=',dec.get('ranking_fit_label_counts'))
    print(' ranking.quality_metrics=',qm)
