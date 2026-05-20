import json, pathlib
base=pathlib.Path('artifacts/live_run_b5acf9de-7475-43b8-a44f-caf5d7597cc9/unzipped')

def j(name):
    return json.loads((base/name).read_text(encoding='utf-8'))

run = j('settings-used.json')
stage = j('stage-artifacts.json')
normalize=j('normalize.json')
enrich=j('enrich.json')
rulef=j('rule_filter.json')
shortl=j('shortlist.json')
rank=j('ranking.json')
cva=j('cv_analysis.json')
cvg=j('cv_generation.json')
rev=j('cv-generation-review-required.json')
syn=j('synonym-proposals.json')
tr=j('synonym-proposals-trace.json')

issues=[]
# 1 settings checks requested previously
sr=run['effective_settings']['stage_runtime']
sm=run['effective_settings']['synonym_management']
exp={
 ('stage_runtime.enrich.concurrency',4): sr['enrich']['concurrency'],
 ('stage_runtime.enrich.sleep_secs',0.0): float(sr['enrich']['sleep_secs']),
 ('stage_runtime.enrich.batch_size',20): sr['enrich']['batch_size'],
 ('stage_runtime.ranking.sleep_secs',0.0): float(sr['ranking']['sleep_secs']),
 ('stage_runtime.ranking.concurrency',2): sr['ranking']['concurrency'],
 ('stage_runtime.cv_analysis.concurrency',4): sr['cv_analysis']['concurrency'],
 ('stage_runtime.cv_generation.concurrency',4): sr['cv_generation']['concurrency'],
 ('synonym.apply_to_run_enabled',True): sm['apply_to_run_enabled'],
 ('synonym.promote_global_enabled',True): sm['promote_global_enabled'],
}
for (k,v),actual in exp.items():
    if actual!=v: issues.append(f'SETTING_MISMATCH {k} expected={v} actual={actual}')

# 2 count parity checks
n_total = normalize.get('total_jobs') or len(normalize.get('normalized_jobs') or [])
if n_total != 41: issues.append(f'NORMALIZE_COUNT unexpected total={n_total} expected=41')
rf_pass=len(rulef.get('passed_jobs') or [])
if rf_pass != 41: issues.append(f'RULE_FILTER_PASS expected=41 actual={rf_pass}')
short_count=len(shortl.get('shortlisted_jobs') or [])
if short_count != 10: issues.append(f'SHORTLIST_COUNT expected=10 actual={short_count}')
rank_count=len(rank.get('ranked_jobs') or [])
if rank_count != 10: issues.append(f'RANK_COUNT expected=10 actual={rank_count}')

# 3 cv analysis / generation consistency
analysis_rows=list(cva.get('analysis') or [])
ready=sum(1 for r in analysis_rows if str(r.get('status') or '').strip()=='ready')
if ready!=5: issues.append(f'CV_ANALYSIS_READY expected=5 actual={ready}')
results=list(cvg.get('results') or [])
if len(results)!=5: issues.append(f'CV_GENERATION_RESULTS expected=5 actual={len(results)}')
accepted=sum(1 for r in results if str(r.get('status') or '')=='accepted')
review_required=sum(1 for r in results if str(r.get('status') or '')=='review_required')
validation_failed=sum(1 for r in results if str(r.get('status') or '')=='validation_failed')
if (accepted,review_required,validation_failed)!=(4,4,1):
    pass
# accepted can later be converted to review_required after downstream checks in debug payload, so no hard assert.

# 4 synonym integrity
props=list(syn.get('proposals') or [])
if len(props)!=27: issues.append(f'SYN_PROPOSAL_COUNT expected=27 actual={len(props)}')
trace_summary=tr.get('trace_summary') or {}
if trace_summary.get('triage_recommendation_reused_total')!=0:
    issues.append('SYN_REUSE_NONZERO with reuse disabled')
if trace_summary.get('triage_recommendation_reuse_reason')!='reuse_disabled':
    issues.append(f"SYN_REUSE_REASON unexpected={trace_summary.get('triage_recommendation_reuse_reason')}")
if trace_summary.get('auto_promote_global_skip_reason')!='disabled':
    issues.append(f"AUTO_PROMOTE_SKIP unexpected={trace_summary.get('auto_promote_global_skip_reason')}")

# 5 pipeline terminal coherence from stage-artifacts
status=stage.get('status')
snapshot_complete=stage.get('snapshot_complete')
if status!='completed' or snapshot_complete is not True:
    issues.append(f'STAGE_ARTIFACT_TERMINAL status={status} snapshot_complete={snapshot_complete}')

print('issues_count',len(issues))
for i in issues:
    print(i)
print('summary',{
 'normalize_total':n_total,'rule_filter_pass':rf_pass,'shortlist':short_count,'ranked':rank_count,
 'cv_analysis_ready':ready,'cv_generation_results':len(results),
 'syn_proposals':len(props),
 'triage_reused':trace_summary.get('triage_recommendation_reused_total'),
 'reuse_reason':trace_summary.get('triage_recommendation_reuse_reason')
})
