from quality_evaluation.evaluate import run_quality_evaluation

if __name__ == '__main__':
    jsonl_path = "../Data/pipeline_testing_data.jsonl"
    results_output_file = "quality_evaluation/tests/quality_test_results_with_gender_fix.pickle"
    seed = 42
    n_samples = 100
    models_to_use = [
        'opus_mt_base', 'opus_mt_finetuned',
        'm2m100_418m_base', 'm2m100_418m_finetuned',
        'mbart50_mmt_base', 'mbart50_mmt_finetuned',
    ]
    
    run_quality_evaluation(
        models_to_use=models_to_use,
        jsonl_path=jsonl_path,
        n_samples=n_samples,
        seed=seed,
        use_find_replace=True,
        compare_find_replace=True,
        output_pickle=results_output_file
    )
