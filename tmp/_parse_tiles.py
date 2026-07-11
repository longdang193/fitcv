import re, pathlib
ids=['4d83ef03-4acc-4acd-8ea6-240127a21098','5656eb4d-34ec-4445-938d-f49ebadb8e14','84c1c6a2-4b5f-49d6-991c-b3197e94f1bb']
for rid in ids:
    t=pathlib.Path(f'tmp/run_{rid}.html').read_text(encoding='utf-8',errors='ignore')
    print('\nRUN',rid)
    tiles=list(re.finditer(r'<div class="run-health-label">(?P<label>[^<]+)</div>(?P<body>.*?)</div>\s*</div>\s*<div style="display:flex;align-items:center;gap:0\.6rem;flex-wrap:wrap;margin-top:0\.55rem">\s*<code>(?P<fraction>[^<]+)</code>',t,re.S))
    keep={'Ranking Strong Rate','Ranking Stretch Rate','Ranking Skip Rate','Ranking AI-Score Reuse Rate','CV Analysis Reranker Block Rate','CV Analysis Skip Rate','CV Analysis Reuse Rate','CV Generation Reuse Rate','Enrich Reuse Rate'}
    for m in tiles:
        label=m.group('label').strip()
        if label not in keep:
            continue
        body=m.group('body')
        pctm=re.search(r'<span class="badge [^"]+">\s*([0-9]+%)\s*</span>',body,re.S)
        pct=pctm.group(1) if pctm else 'NA'
        print(f'  {label}: {pct} ({m.group("fraction").strip()})')
    # timeline summary lines
    for pat in ['Ranking complete: ranked','CV analysis complete: ready','AI scored:']:
        mm=re.findall(re.escape(pat)+r'[^<]*',t)
        if mm:
            print(' ',mm[-1])
