import re, pathlib
ids=['4d83ef03-4acc-4acd-8ea6-240127a21098','5656eb4d-34ec-4445-938d-f49ebadb8e14','84c1c6a2-4b5f-49d6-991c-b3197e94f1bb']
keys=['fit_label_thresholds','ai_score_top_n','final_top_n','reuse.ranking.enabled','reuse\\": {','ranking_concurrency_effective','configured_fit_label_thresholds','ranking_fit_label_counts']
for rid in ids:
    t=pathlib.Path(f'tmp/run_{rid}.html').read_text(encoding='utf-8',errors='ignore')
    print('\nRUN',rid)
    for k in keys:
        if k in t:
            print('  has',k)
    # print nearby snippets for crucial keys
    for k in ['fit_label_thresholds','ai_score_top_n','final_top_n','reuse.ranking.enabled']:
        idx=t.find(k)
        if idx!=-1:
            s=t[max(0,idx-120):idx+220]
            print('---',k,'snippet---')
            print(re.sub(r'\s+',' ',s))
