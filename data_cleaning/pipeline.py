import config
import os
import re
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

_GLOBAL_SENTENCE_ENCODER = None
_GLOBAL_LANGUAGE_CLASSIFIER = None


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


def _worker_init(device):
    global _GLOBAL_SENTENCE_ENCODER, _GLOBAL_LANGUAGE_CLASSIFIER
    _GLOBAL_LANGUAGE_CLASSIFIER = LanguageClassifier()
    _GLOBAL_SENTENCE_ENCODER = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2').to(device)


def _process_row_wrapper(args):
    row, device, skip_abstracts, linebreaks, parsed_docs_folder = args
    return _process_row(row, device, _GLOBAL_LANGUAGE_CLASSIFIER, _GLOBAL_SENTENCE_ENCODER, skip_abstracts, linebreaks, parsed_docs_folder)


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


def _create_dataframe(num_workers, rows, device, skip_abstracts, linebreaks, parsed_docs_folder, output_filename):
    start_time = time.time()
    
    args_list = [(row, device, skip_abstracts, linebreaks, parsed_docs_folder) for row in rows]
    
    print(f"\n=========== PROCESSING {output_filename} ===========")
    
    with mp.Pool(num_workers, initializer=_worker_init, initargs=(device,)) as pool:
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
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    num_workers = max(1, min(4, os.cpu_count() // 4))
    
    print(f'\nUsing device: {device}')
    print(f"Using {num_workers} worker processes.\n")
    
    matched_data = _create_dataframe(
        num_workers, rows, device,
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


def _apply_quality_filters(dataframe, quality_level='strict'):
    if quality_level == 'strict':
        outlier_criteria = {
            "len_ratio": (0.75, 1.92),
            "verb_ratio": (0.75, 1.50),
            "noun_ratio": (1.00, 1.75),
            "entity_ratio": (0.33, 1.00),
            "clause_ratio": (1.00, 1.50),
            "one_char_words_fr": (0.0, 1.0),
            "one_char_words_en": (0.0, 1.0),
        }
        dataframe["exclude_quality"] = dataframe["similarity"] < 0.757
        
        for feature, (low, high) in outlier_criteria.items():
            dataframe["exclude_quality"] |= ~dataframe[feature].between(low, high)
        
        return dataframe[~dataframe["exclude_quality"]].copy()
    
    elif quality_level == 'relaxed':
        outlier_criteria = {
            "len_ratio": (0.34, 3.93),
            "verb_ratio": (0.25, 5.00),
            "noun_ratio": (0.38, 12.00),
            "entity_ratio": (0.10, 4.00),
            "clause_ratio": (0.20, 6.00),
            "one_char_words_fr": (0.0, 11.0),
            "one_char_words_en": (0.0, 11.0),
        }
        dataframe["exclude_quality"] = False
        
        for feature, (low, high) in outlier_criteria.items():
            dataframe["exclude_quality"] |= ~dataframe[feature].between(low, high)
        
        return dataframe[~dataframe["exclude_quality"]].copy()


def _analyze_text_for_figrefs(text, language='en'):
    if language == 'fr':
        pattern = r'\s*(?:Figure|Tableau|Fig\.?|Tab\.?)\s+\d+.*$'
    else:
        pattern = r'\s*(?:Figure|Table|Fig\.?|Tab\.?)\s+\d+.*$'
    
    has_figure_refs = bool(re.search(pattern, text, flags=re.IGNORECASE))
    has_trailing_nums = bool(re.search(r'\s+\d+\s*$', text))
    has_paren_nums = bool(re.search(r'\s+\(\d+\)\s*$', text))
    has_repeated_punct = bool(re.search(r'[.!?]{2,}$', text))
    
    return any([has_figure_refs, has_trailing_nums, has_paren_nums, has_repeated_punct])


def _exclude_figure_text(dataframe):
    dataframe["exclude_figtext"] = dataframe.apply(
        lambda row: _analyze_text_for_figrefs(row['en'], 'en') or
                    _analyze_text_for_figrefs(row['fr'], 'fr'),
        axis=1
    )
    return dataframe


def _exclude_date_references(dataframe):
    date_pattern = (r'\b(?:19|20)\d{2}\b|(?:January|February|March|April|May|June|July|August|September|October|November|December|janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre'
                    r'|novembre|décembre|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b')
    dataframe["has_date_refs"] = dataframe[['en', 'fr']].apply(
        lambda x: x.astype(str).str.contains(date_pattern, case=False, regex=True).any(),
        axis=1
    )
    return dataframe


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
        return
    
    if not os.path.exists(parsed_docs_folder):
        print(f"ERROR: Parsed docs folder not found at {parsed_docs_folder}")
        return
    
    dataframe = _prepare_training_data(
        correlation_csv_path,
        parsed_docs_folder,
        linebreaks=linebreaks,
        add_features_flag=add_features
    )
    
    if dataframe is not None:
        dataframe = _exclude_figure_text(dataframe)
        dataframe = _exclude_date_references(dataframe)
        
        print("Applying quality filters...")
        training_data = _apply_quality_filters(dataframe, quality_level='strict')
        
        testing_candidates = dataframe[~dataframe.index.isin(training_data.index)]
        testing_data = _apply_quality_filters(testing_candidates, quality_level='relaxed')
        
        for df_set in [training_data, testing_data]:
            df_set['fr'] = df_set['fr'] + "."
            df_set['en'] = df_set['en'] + "."
        
        training_data_output = os.path.join(config.DATA_DIR, "pipeline_training_data.jsonl")
        testing_data_output = os.path.join(config.DATA_DIR, "pipeline_eval_data.jsonl")
        
        print(f"Saving {len(training_data)} training examples...")
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
        
        print(f"Saving {len(testing_data)} testing examples...")
        with open(testing_data_output, 'w', encoding='utf-8') as f:
            for _, row in testing_data.iterrows():
                entry = {
                    'pub_number': row['pub_number'],
                    'source': row['en'],
                    'target': row['fr'],
                    'source_lang': 'en',
                    'similarity': float(row['similarity'])
                }
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        
        print(f"Data cleaning pipeline complete!")
        print(f"  - {training_data_output} ({len(training_data)} examples)")
        print(f"  - {testing_data_output} ({len(testing_data)} examples)\n")
    else:
        print("Data cleaning pipeline failed!")
