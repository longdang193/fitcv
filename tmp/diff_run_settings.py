import json
from pathlib import Path
run='cb17dd77-5b3b-489a-aea1-edc66861701e'
settings_used=json.loads(Path(f'tmp/{run}-settings-used.json').read_text(encoding='utf-8'))
# active settings via API saved to temp from powershell now
import urllib.request
active=json.loads(urllib.request.urlopen('http://localhost:8000/settings').read().decode('utf-8'))

# flatten run settings-used if needed
if isinstance(settings_used, dict) and 'settings' in settings_used and isinstance(settings_used['settings'], dict):
    run_cfg=settings_used['settings']
else:
    run_cfg=settings_used if isinstance(settings_used, dict) else {}

# detect key->value drifts for keys present in both flat maps
common=sorted(set(run_cfg.keys()) & set(active.keys()))
drifts=[]
for k in common:
    if run_cfg[k] != active[k]:
        drifts.append((k, run_cfg[k], active[k]))

focus=[
 'synonym_management.apply_to_run_enabled',
 'synonym_management.promote_global_enabled',
 'synonym_management.triage_recommendation_reuse_enabled',
 'stage_runtime.enrich.concurrency',
 'enrichment_concurrency'
]
print('run_keys',len(run_cfg),'active_keys',len(active),'common',len(common),'drifts',len(drifts))
print('focus:')
for k in focus:
    print(k, 'run=', run_cfg.get(k,'<missing>'), 'active=', active.get(k,'<missing>'))
print('top_drifts:')
for k,a,b in drifts[:30]:
    print(k, 'run=',a,'active=',b)
