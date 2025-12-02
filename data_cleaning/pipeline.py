import config
import os
import time
import torch
import multiprocessing as mp
import pandas as pd
import json

from sentence_transformers import SentenceTransformer

from .text_processing import (
    extract_both_languages_from_two_files,
    extract_both_languages_from_single_file,
)
from .correlation import correlate_and_clean_text
from .feature_engineering import add_features

try:
    from ..language_classifier import LanguageClassifier
except ImportError:
    from language_classifier.language_classifier import LanguageClassifier


def _get_json_file_link(parsed_docs_folder, pdf_filename):
    if pdf_filename.endswith(".pdf"):
        json_filename = pdf_filename + ".json"
        for root, _, files in os.walk(parsed_docs_folder):
            if json_filename in files:
                return os.path.join(root, json_filename)
    return None


def _process_row(row_tuple, device, language_classifier, sentence_encoder, skip_abstracts=False, linebreaks=True, parsed_docs_folder="../ParsedPublications"):
    index, row = row_tuple
    pub_number = row['pub_number']
    filename_fr, filename_en = row['filename_fr'], row['filename_en']
    
    if filename_fr == "WITHDRAWN" and filename_en == "WITHDRAWN":
        return None
    
    fr_link = _get_json_file_link(parsed_docs_folder, filename_fr)
    if fr_link is None:
        return None
    
    if filename_fr == filename_en:
        text_fr, text_en = extract_both_languages_from_single_file(fr_link, language_classifier, linebreaks)
    else:
        en_link = _get_json_file_link(parsed_docs_folder, filename_en)
        if en_link is None:
            return None
        text_fr, text_en = extract_both_languages_from_two_files(fr_link, en_link, language_classifier, linebreaks)
    
    max_ratio = 2
    min_char = 1000
    len_fr, len_en = len(text_fr), len(text_en)
    
    if len_fr == 0 or len_en == 0:
        return None
    elif skip_abstracts:
        if len(text_fr) / len(text_en) > max_ratio or len(text_en) / len(text_fr) > max_ratio:
            return None
    elif len(text_fr) < min_char or len(text_en) < min_char:
        return None
    
    return correlate_and_clean_text(text_fr, text_en, pub_number, sentence_encoder, device, linebreaks)


def _process_row_wrapper(args):
    row, device, language_classifier, sentence_encoder, skip_abstracts, linebreaks, parsed_docs_folder = args
    return _process_row(row, device, language_classifier, sentence_encoder, skip_abstracts, linebreaks, parsed_docs_folder)


def _print_time_estimate(start_time, processed_count, total_count):
    if processed_count == 0:
        print(f"\n{processed_count}/{total_count} complete.", end="... ")
        return
    
    time_elapsed = int(time.time() - start_time)
    time_remaining = int((time_elapsed / processed_count) * (total_count - processed_count))
    
    time_elapsed_text = f"{time_elapsed // 3600}h:{(time_elapsed % 3600) // 60:02d}m"
    time_remaining_text = f"{time_remaining // 3600}h:{(time_remaining % 3600) // 60:02d}m"
    
    print(f"\n{processed_count}/{total_count} complete at {time_elapsed_text}. Estimated {time_remaining_text} remaining.", end="... ")


def _print_status(start_time, processed_count, total_count):
    small_update = 50
    large_update = 500
    
    if processed_count % small_update == 0:
        if processed_count % large_update == 0:
            _print_time_estimate(start_time, processed_count, total_count)
        else:
            print(f"{processed_count}", end="... ")


def _create_dataframe(num_workers, total_rows, rows, device, language_classifier, sentence_encoder, skip_abstracts, linebreaks, parsed_docs_folder, output_filename):
    start_time = time.time()
    
    args_list = [(row, device, language_classifier, sentence_encoder, skip_abstracts, linebreaks, parsed_docs_folder) for row in rows]
    
    print(f"\n=========== PROCESSING {output_filename} ===========")
    
    with mp.Pool(num_workers) as pool:
        results = []
        for i, result in enumerate(pool.imap_unordered(_process_row_wrapper, args_list)):
            if result:
                results.extend(result)
            
            _print_status(start_time, i, len(rows))
    
    dataframe = pd.DataFrame(results, columns=['pub_number', 'fr', 'en', 'similarity'])
    dataframe.to_pickle(output_filename)
    print(f"\nProcessing {output_filename} complete!\n")
    
    return dataframe


def _prepare_training_data(correlation_csv_path, parsed_docs_folder, linebreaks=True, add_features_flag=True):
    correlation_dataframe = pd.read_csv(correlation_csv_path)
    correlation_dataframe = correlation_dataframe[['pub_number', 'filename_fr', 'filename_en']]
    rows = list(correlation_dataframe.iterrows())
    total_rows = len(rows)
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    num_workers = max(1, os.cpu_count() // 2)
    
    language_classifier = LanguageClassifier()
    sentence_encoder = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2').to(device)
    
    print(f'\nUsing device: {device}')
    print(f"Using {num_workers} CPU cores.\n")
    
    matched_data = _create_dataframe(
        num_workers, total_rows, rows, device, language_classifier, sentence_encoder,
        False, linebreaks, parsed_docs_folder,
        os.path.join(config.DATA_DIR, "pipeline_matched_data.pickle")
    )
    
    if add_features_flag:
        print("Adding linguistic features...")
        featured_data = add_features(matched_data)
        featured_data.to_pickle(os.path.join(config.DATA_DIR, "pipeline_df_with_features.pickle"))
        print("Features added and saved.\n")
        return featured_data
    else:
        return matched_data


def data_cleaning_pipeline(correlation_csv_path=None, parsed_docs_folder=None, linebreaks=True, add_features=True):
    if correlation_csv_path is None:
        # Note: this csv was created with BS4 webcrawling
        correlation_csv_path = config.CORRELATION_CSV_PATH
    if parsed_docs_folder is None:
        # Note: this data was provided by CDOS (used for ISAS)
        parsed_docs_folder = config.PARSED_DOCS_DIR
    
    print("Starting data cleaning pipeline...")
    print(f"Using correlation CSV: {correlation_csv_path}")
    print(f"Using parsed docs folder: {parsed_docs_folder}\n")
    
    if not os.path.exists(correlation_csv_path):
        print(f"ERROR: Correlation CSV not found at {correlation_csv_path}")
        return None
    
    if not os.path.exists(parsed_docs_folder):
        print(f"ERROR: Parsed docs folder not found at {parsed_docs_folder}")
        return None
    
    training_data = _prepare_training_data(
        correlation_csv_path,
        parsed_docs_folder,
        linebreaks=linebreaks,
        add_features_flag=add_features
    )
    
    if training_data is not None:
        training_data_output = os.path.join(config.DATA_DIR, "pipeline_training_data.jsonl")
        print(f"Converting to JSONL format and saving to {training_data_output}...")
        
        with open(training_data_output, 'w', encoding='utf-8') as f:
            for _, row in training_data.iterrows():
                entry = {
                    'pub_number': row['pub_number'],
                    'source': row['en'],
                    'target': row['fr'],
                    'source_lang': 'en',
                    'similarity': float(row['similarity'])
                }
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        
        print(f"Data cleaning pipeline complete! Saved {len(training_data)} examples.\n")
        return training_data
    else:
        print("Data cleaning pipeline failed!")
        return None
