from unittest.mock import patch
from tests.test_pipeline import _minimal_job,_minimal_profile,_minimal_config,_agentic_analysis_ready,_agentic_generation_result
from fitcv.pipeline import run_pipeline
job=_minimal_job(); profile=_minimal_profile(); config=_minimal_config(); config.setdefault('cv',{})['agentic_late_stage']={'enabled':True}
structured_cv={
 'schema_version':'cv_doc_v1','sections':{'header':{'name':'Jane Doe','title':'Data Engineer','location':None,'contact':{'email':None,'phone':None,'linkedin':None}},'summary':{'text':'Grounded summary.'},'experience':[],'projects':[],'education':[],'skills':{'groups':[]},'certifications':[],'publications':[],'languages':[]}}
validation={'valid':False,'missing_sections':['experience'],'grounding_violations':[],'skill_violations':[],'warnings':[]}
with patch('fitcv.pipeline.load_config',return_value=config), \
 patch('fitcv.pipeline.parse_jobs_file',return_value=[job]), \
 patch('fitcv.pipeline.normalize_batch',return_value=[job]), \
 patch('fitcv.pipeline.normalize_batch_with_exclusions',return_value=([job],[])), \
 patch('fitcv.pipeline.load_to_bigquery'), \
 patch('fitcv.pipeline.enrich_batch',return_value=[job]), \
 patch('fitcv.pipeline.load_structured_jobs'), \
 patch('fitcv.pipeline.load_run_structured_jobs'), \
 patch('fitcv.pipeline.load_profile_yaml',return_value=profile), \
 patch('fitcv.pipeline.load_candidate_to_bigquery'), \
 patch('fitcv.pipeline.apply_rule_filters',return_value={'passed':[job['job_url']],'rejected':[]}), \
 patch('fitcv.pipeline.store_filter_results'), \
 patch('fitcv.pipeline.embed_and_store_jobs'), \
 patch('fitcv.pipeline.embed_and_store_candidate'), \
 patch('fitcv.pipeline.run_vector_search',return_value=[{'job_url':job['job_url'],'vector_similarity':0.9,'vector_rank':1}]), \
 patch('fitcv.pipeline.run_ai_scoring',return_value=[job]), \
 patch('fitcv.pipeline.build_ranking_features',return_value=[job]), \
 patch('fitcv.pipeline.rank_jobs',return_value=[job]), \
 patch('fitcv.pipeline.store_final_ranking'), \
 patch('fitcv.pipeline.retrieve_evidence',return_value=[]), \
 patch('fitcv.pipeline.compute_gap',return_value={'matched':['SQL'],'partial':[],'missing':[]}), \
 patch('fitcv.pipeline.classify_fit',return_value='strong'), \
 patch('fitcv.pipeline.generate_cv'), \
 patch('fitcv.pipeline.run_all_validations'), \
 patch('fitcv.pipeline.store_cv_version'), \
 patch('fitcv.pipeline.run_agentic_cv_analysis',return_value=_agentic_analysis_ready(job)), \
 patch('fitcv.pipeline.run_agentic_cv_generation',return_value=_agentic_generation_result(status='validation_failed',structured_cv=structured_cv,markdown='# Broken CV',validation_initial=validation,error={'stage':'validation','message':'Missing sections: experience'})), \
 patch('fitcv.pipeline._hitl_review_reason_for_agentic_case',return_value=None):
    result=run_pipeline('data/sample_jobs.json',config_path='config/env.yaml',run_id='debug-validation-manual')
print(result['cv_generation_debug_records'])
