import datetime
import json
from fitcv_cp.models import PipelineRun, RunStatus
from fitcv_cp.bq_store import insert_run

run_id='11111111-2222-4333-8444-555555555555'
run=PipelineRun(
    run_id=run_id,
    status=RunStatus.SUCCEEDED,
    triggered_by='manual-ui-check',
    trigger_source='web',
    jobs_path='data/sample_jobs.json',
    config_path='.env.yaml',
    created_at=datetime.datetime.now(datetime.timezone.utc),
    run_mode='run_all',
    effective_settings_json=json.dumps({'synonym_management':{'apply_to_run_enabled':True,'promote_global_enabled':True}}),
    synonym_proposals_json=json.dumps({
        'run_id': run_id,
        'proposals': [
            {'proposal_id':'proposal-new','proposal_status':'approved_for_run_overlay','alias':'sql','canonical':'structured query language','confidence':0.9},
            {'proposal_id':'proposal-existing','proposal_status':'approved_for_run_overlay','alias':'gcp','canonical':'google cloud','confidence':0.9},
            {'proposal_id':'proposal-deferred','proposal_status':'deferred','alias':'it services and it consulting','canonical':'artificial intelligence','confidence':0.9},
            {'proposal_id':'proposal-conflict-a','proposal_status':'approved_for_run_overlay','alias':'ai','canonical':'artificial intelligence','confidence':0.9},
            {'proposal_id':'proposal-conflict-b','proposal_status':'approved_for_run_overlay','alias':'ai','canonical':'applied informatics','confidence':0.9}
        ]
    })
)
insert_run(run, None, project='', dataset='fitcv')
print(run_id)
