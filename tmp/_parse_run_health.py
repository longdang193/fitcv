import re, pathlib
ids=['4d83ef03-4acc-4acd-8ea6-240127a21098','5656eb4d-34ec-4445-938d-f49ebadb8e14','84c1c6a2-4b5f-49d6-991c-b3197e94f1bb']
labels=['Ranking Skip Rate','Ranking Strong Rate','Ranking Stretch Rate','Ranking AI-Score Reuse Rate','CV Analysis Skip Rate','CV Analysis Reranker Block Rate','CV Analysis Reuse Rate','CV Generation Reuse Rate','Enrich Reuse Rate']
for rid in ids:
    p=pathlib.Path(f'tmp/run_{rid}.html')
    t=p.read_text(encoding='utf-8',errors='ignore')
    print('\nRUN',rid)
    for label in labels:
        idx=t.find(f'<div class="run-health-label">{label}</div>')
        if idx<0:
            continue
        seg=t[idx:idx+900]
        m_rate=re.search(r'<div class="run-health-value">\s*([^<]+?)\s*</div>',seg,re.S)
        m_frac=re.search(r'<div class="run-health-support">\s*([^<]+?)\s*</div>',seg,re.S)
        rate=(m_rate.group(1).strip() if m_rate else 'NA')
        frac=(m_frac.group(1).strip() if m_frac else 'NA')
        print(f'  {label}: {rate} ({frac})')
    for pat in ['Ranking complete: ranked','CV analysis complete: ready','AI scored:']:
        mm=re.findall(re.escape(pat)+r'[^<]*',t)
        if mm:
            print(' ',mm[-1])
