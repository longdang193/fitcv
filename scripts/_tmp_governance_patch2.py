from pathlib import Path

for path, max_height in [
    ('src/fitcv_cp/templates/run_detail.html', '14rem'),
    ('src/fitcv_cp/templates/synonym_review.html', '18rem'),
]:
    p = Path(path)
    t = p.read_text(encoding='utf-8')
    start = t.index('{% if synonym_proposal_decision_ledger %}')
    else_idx = t.index('{% else %}', start)
    include = '{% if synonym_proposal_decision_ledger %}\n  {% include "_synonym_decision_ledger.html" %}\n  '
    t = t[:start] + include + t[else_idx:]
    if path.endswith('synonym_review.html'):
        t = t.replace('max-height:18rem', 'max-height:14rem')
    p.write_text(t, encoding='utf-8')
    print(f'patched {path}')

p = Path('src/fitcv_cp/templates/run_detail.html')
t = p.read_text(encoding='utf-8')
t = t.replace('<button class="tab-btn active" id="tab-btn-enriched"   onclick="showTab(\'enriched\')">📊 Enriched Jobs</button>', '<button class="tab-btn active" id="tab-btn-enriched" role="tab" aria-selected="true" aria-controls="pane-enriched" onclick="showTab(\'enriched\')">📊 Enriched Jobs</button>')
t = t.replace('<button class="tab-btn"        id="tab-btn-jobs-input" onclick="showTab(\'jobs-input\')">📄 Original Job Input</button>', '<button class="tab-btn"        id="tab-btn-jobs-input" role="tab" aria-selected="false" aria-controls="pane-jobs-input" onclick="showTab(\'jobs-input\')">📄 Original Job Input</button>')
t = t.replace('<button class="tab-btn"        id="tab-btn-profile"    onclick="showTab(\'profile\')">👤 Candidate Profile</button>', '<button class="tab-btn"        id="tab-btn-profile"    role="tab" aria-selected="false" aria-controls="pane-profile" onclick="showTab(\'profile\')">👤 Candidate Profile</button>')
t = t.replace('<div class="pane-container tab-pane active" id="pane-enriched" data-tab-id="enriched" data-tab-url="/admin/runs/{{ run.run_id }}/tabs/enriched">', '<div class="pane-container tab-pane active" id="pane-enriched" role="tabpanel" aria-labelledby="tab-btn-enriched" data-tab-id="enriched" data-tab-url="/admin/runs/{{ run.run_id }}/tabs/enriched">')
t = t.replace('<div class="pane-container tab-pane" id="pane-jobs-input" data-tab-id="jobs-input" data-tab-url="/admin/runs/{{ run.run_id }}/tabs/jobs-input">', '<div class="pane-container tab-pane" id="pane-jobs-input" role="tabpanel" aria-labelledby="tab-btn-jobs-input" data-tab-id="jobs-input" data-tab-url="/admin/runs/{{ run.run_id }}/tabs/jobs-input">')
t = t.replace('<div class="pane-container tab-pane" id="pane-profile" data-tab-id="profile" data-tab-url="/admin/runs/{{ run.run_id }}/tabs/profile">', '<div class="pane-container tab-pane" id="pane-profile" role="tabpanel" aria-labelledby="tab-btn-profile" data-tab-id="profile" data-tab-url="/admin/runs/{{ run.run_id }}/tabs/profile">')
t = t.replace("  document.querySelectorAll('.tab-pane').forEach(p => {\n    p.style.display = 'none';\n    p.classList.remove('active');\n  });\n  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));\n  const pane = document.getElementById('pane-' + id);\n  pane.style.display = 'block';\n  pane.classList.add('active');\n  document.getElementById('tab-btn-' + id).classList.add('active');", "  document.querySelectorAll('.tab-pane').forEach(p => {\n    p.style.display = 'none';\n    p.classList.remove('active');\n    p.hidden = true;\n  });\n  document.querySelectorAll('.tab-btn').forEach(b => {\n    b.classList.remove('active');\n    b.setAttribute('aria-selected', 'false');\n  });\n  const pane = document.getElementById('pane-' + id);\n  pane.style.display = 'block';\n  pane.classList.add('active');\n  pane.hidden = false;\n  const button = document.getElementById('tab-btn-' + id);\n  button.classList.add('active');\n  button.setAttribute('aria-selected', 'true');")
p.write_text(t, encoding='utf-8')
print('patched run_detail tabs')
