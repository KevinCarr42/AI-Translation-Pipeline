from quality_evaluation.evaluate import run_quality_evaluation

if __name__ == '__main__':
    jsonl_path = "../Data/pipeline_testing_data.jsonl"
    results_output_file = "quality_evaluation/tests/quality_test_results.pickle"
    n_samples = 10
    
    run_quality_evaluation(
        jsonl_path=jsonl_path,
        n_samples=n_samples,
        use_find_replace=True,
        use_finetuned=None,
        output_pickle=results_output_file
    )
