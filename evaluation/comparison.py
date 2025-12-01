import json
import csv
import random
import os
from datetime import datetime
from datasets import load_dataset
from .metrics import is_valid_translation, calculate_similarity_scores

LANGUAGE_CODES = {
    "en": "English",
    "fr": "French",
}


def sample_evaluation_data(file_path, num_samples=10, source_language=None, use_eval_split=False, validation_ratio=0.05, split_seed=42):
    if use_eval_split:
        dataset = load_dataset("json", data_files=file_path, split="train")
        if source_language:
            dataset = dataset.filter(lambda x: x.get("source_lang") == source_language, load_from_cache_file=False)
        eval_dataset = dataset.train_test_split(test_size=validation_ratio, seed=split_seed)["test"]
        k = len(eval_dataset) if num_samples is None else min(num_samples, len(eval_dataset))
        if k < len(eval_dataset):
            indices = random.sample(range(len(eval_dataset)), k)
            return [eval_dataset[i] for i in indices]
        return [eval_dataset[i] for i in range(len(eval_dataset))]
    else:
        with open(file_path, "r", encoding="utf-8") as f:
            data = [json.loads(line) for line in f
                    if not source_language or json.loads(line).get("source_lang") == source_language]
        k = len(data) if num_samples is None else min(num_samples, len(data))
        return random.sample(data, k) if k < len(data) else data


def test_translations_with_models(translation_manager, dataset, output_directory, test_name_suffix=None, use_find_replace=True):
    num_samples = len(dataset)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    indent_width = 70
    
    os.makedirs(output_directory, exist_ok=True)
    
    if test_name_suffix:
        csv_path = os.path.join(output_directory, f"{timestamp}_translation_comparison_{test_name_suffix}.csv")
        errors_path = os.path.join(output_directory, f"{timestamp}_translation_errors_{test_name_suffix}.json")
    else:
        csv_path = os.path.join(output_directory, f"{timestamp}_translation_comparison.csv")
        errors_path = os.path.join(output_directory, f"{timestamp}_translation_errors.json")
    
    csv_data = []
    
    print(f"\nRunning evaluation: {test_name_suffix if test_name_suffix else 'default'}")
    print(f"Total samples: {num_samples}")
    print("-" * 80)
    
    for i, data_item in enumerate(dataset, start=1):
        source_text = data_item.get("source")
        target_text = data_item.get("target")
        source_language = data_item.get("source_lang")
        target_language = "en" if source_language == "fr" else "fr"
        
        print(
            f"\n[sample {i}/{num_samples}] {LANGUAGE_CODES[source_language]}"
            f"\n{f'source ({LANGUAGE_CODES[source_language]}):':<{indent_width}}{source_text}"
            f"\n{f'expected ({LANGUAGE_CODES[target_language]}):':<{indent_width}}{target_text}"
        )
        
        translation_results = translation_manager.translate_with_all_models(
            text=source_text,
            source_lang=source_language,
            target_lang=target_language,
            use_find_replace=use_find_replace,
            idx=i,
            target_text=target_text,
        )
        
        for model_name, result in translation_results.items():
            csv_entry = {
                'source': source_text,
                'target': target_text,
                'source_lang': source_language,
                'target_lang': target_language,
                'model_name': model_name,
                'translated_text': result.get("translated_text", "[TRANSLATION FAILED]"),
                'similarity_of_original': result.get("similarity_of_original_translation"),
                'similarity_vs_source': result.get("similarity_vs_source"),
                'similarity_vs_target': result.get("similarity_vs_target"),
            }
            csv_data.append(csv_entry)
            
            print(f"{f'predicted ({LANGUAGE_CODES[target_language]}) via {model_name}:':<{indent_width}}"
                  f"{result.get('translated_text', '[FAILED]')}")
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'source', 'target', 'source_lang', 'target_lang', 'model_name', 'translated_text',
            'similarity_of_original', 'similarity_vs_source', 'similarity_vs_target'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_data)
    
    error_summary = translation_manager.get_error_summary()
    if error_summary["extra_token_errors"] > 0 or error_summary["find_replace_errors"] > 0:
        with open(errors_path, "w", encoding="utf-8") as f:
            json.dump(error_summary, f, ensure_ascii=False, indent=2)
    
    print(f"\nCompleted evaluation: {test_name_suffix if test_name_suffix else 'default'}")
    print(f"Results saved to: {csv_path}")
    print(f"Total samples processed: {num_samples}")
    print(f"Total CSV entries: {len(csv_data)}")
    
    if error_summary["extra_token_errors"] > 0:
        print(f"Extra token errors: {error_summary['extra_token_errors']}")
    if error_summary["find_replace_errors"] > 0:
        print(f"Find-replace errors: {error_summary['find_replace_errors']}")
    if error_summary["extra_token_errors"] > 0 or error_summary["find_replace_errors"] > 0:
        print(f"Error details saved to: {errors_path}")
    else:
        print("No errors detected. Error log not created.")
    
    return csv_path, errors_path


def get_error_summary(translation_manager):
    return translation_manager.get_error_summary()
