import json
import re
import time


# ADD EXCLUSION COLUMNS
#  chosen based on stdev from mean, and tweaked based on performance and final quality

# when similarity < 0.85 (median)
outlier_criteria_s1 = {
    "len_ratio": (0.75, 1.92),  # override with 2 stdev len ratios
    "verb_ratio": (0.75, 1.50),
    "noun_ratio": (1.00, 1.75),
    "entity_ratio": (0.33, 1.00),
    "clause_ratio": (1.00, 1.50),
    "one_char_words_fr": (0.0, 1.0),
    "one_char_words_en": (0.0, 1.0),
    "potential_fr_accent_issues": (0.0, 0.1),  # exclude anything above 0
}

# when similarity < 0.92 (1 stdev above median)
outlier_criteria_s2 = {
    "len_ratio": (0.75, 1.92),
    "verb_ratio": (0.50, 3.00),
    "noun_ratio": (0.67, 4.00),
    "entity_ratio": (0.17, 2.00),
    "clause_ratio": (0.50, 3.00),
    "one_char_words_fr": (0.0, 3.0),
    "one_char_words_en": (0.0, 3.0),
    "potential_fr_accent_issues": (0.0, 0.1),  # exclude anything above 0
}

# all higher similarities
outlier_criteria_s3 = {
    "len_ratio": (0.34, 3.93),
    "verb_ratio": (0.25, 5.00),
    "noun_ratio": (0.38, 12.00),
    "entity_ratio": (0.10, 4.00),
    "clause_ratio": (0.20, 6.00),
    "one_char_words_fr": (0.0, 11.0),
    "one_char_words_en": (0.0, 11.0),
    "potential_fr_accent_issues": (0.0, 0.1),  # exclude anything above 0
}


def add_exclusion_columns(dataframe):
    print("adding exclusion columns based on similarity scores...")
    t0 = time.perf_counter()
    
    dataframe["exclude_low_similarity"] = dataframe["similarity"] < 0.757
    
    s1_mask = dataframe["similarity"] < 0.85
    s2_mask = (dataframe["similarity"] >= 0.85) & (dataframe["similarity"] < 0.92)
    s3_mask = dataframe["similarity"] >= 0.92
    
    for feature in outlier_criteria_s1:
        col_name = f"exclude_{feature}"
        dataframe[col_name] = False
        
        low1, high1 = outlier_criteria_s1[feature]
        low2, high2 = outlier_criteria_s2[feature]
        low3, high3 = outlier_criteria_s3[feature]
        
        dataframe.loc[s1_mask, col_name] = ~dataframe.loc[s1_mask, feature].between(low1, high1)
        dataframe.loc[s2_mask, col_name] = ~dataframe.loc[s2_mask, feature].between(low2, high2)
        dataframe.loc[s3_mask, col_name] = ~dataframe.loc[s3_mask, feature].between(low3, high3)
    
    print(f"→ done in {(time.perf_counter() - t0) / 60:.2f} min")
    return dataframe


def analyze_text_for_figrefs(text, language='en'):
    result = {
        'has_trailing_numbers': False,
        'has_parenthetical_numbers': False,
        'has_figure_references': False,
        'has_repeated_punctuation': False,
        'exclude_figtext': False
    }
    
    # Check for trailing numbers
    if re.search(r'\s+\d+\s*$', text):
        result['has_trailing_numbers'] = True
    
    # Check for parenthetical numbers
    if re.search(r'\s+\(\d+\)\s*$', text):
        result['has_parenthetical_numbers'] = True
    
    # Check for figure/table references (with French support)
    if language == 'fr':
        # French patterns: Figure, Tableau, Fig., Tab.
        pattern = r'\s*(?:Figure|Tableau|Fig\.?|Tab\.?)\s+\d+.*$'
    else:
        # English patterns: Figure, Table, Fig., Tab.
        pattern = r'\s*(?:Figure|Table|Fig\.?|Tab\.?)\s+\d+.*$'
    
    if re.search(pattern, text, flags=re.IGNORECASE):
        result['has_figure_references'] = True
    
    # Check for repeated punctuation
    if re.search(r'[.!?]{2,}$', text):
        result['has_repeated_punctuation'] = True
    
    # Set exclude flag if any issue found
    result['exclude_figtext'] = any([
        result['has_figure_references'],
        result['has_trailing_numbers'],
        result['has_parenthetical_numbers'],
        result['has_repeated_punctuation']
    ])
    
    return result


def add_figref_column(dataframe, text_en_column='en', text_fr_column='fr'):
    print("adding exclusion column for detected figure and table text...")
    t0 = time.perf_counter()
    
    en_results = dataframe[text_en_column].apply(lambda x: analyze_text_for_figrefs(x, language='en'))
    fr_results = dataframe[text_fr_column].apply(lambda x: analyze_text_for_figrefs(x, language='fr'))
    
    dataframe['exclude_figtext'] = (
            en_results.apply(lambda x: x['exclude_figtext']) |
            fr_results.apply(lambda x: x['exclude_figtext'])
    )
    
    print(f"→ done in {(time.perf_counter() - t0) / 60:.2f} min")
    return dataframe


def add_dates_column(dataframe):
    print("adding exclusion column for dates...")
    t0 = time.perf_counter()
    
    dataframe['has_date_refs'] = dataframe[['en', 'fr']].apply(lambda x: x.astype(str).str.contains(
        r'\b(?:19|20)\d{2}\b|(?:January|February|March|April|May|June|July|August|September|October'
        r'|November|December|janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre'
        r'|décembre|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b',
        case=False, regex=True).any(), axis=1)
    
    print(f"→ done in {(time.perf_counter() - t0) / 60:.2f} min")
    return dataframe


def exclude_for_training_data(dataframe):
    print("excluding columns to create training data...")
    t0 = time.perf_counter()
    
    exclusion_columns = [
        'exclude_low_similarity',
        'exclude_len_ratio',
        'exclude_verb_ratio',
        'exclude_noun_ratio',
        'exclude_entity_ratio',
        'exclude_clause_ratio',
        'exclude_one_char_words_fr',
        'exclude_one_char_words_en',
        'exclude_figtext',
        'has_date_refs',
        'potential_fr_accent_issues',
    ]
    dataframe["exclude"] = dataframe[exclusion_columns].any(axis=1)
    dataframe = dataframe[~dataframe.exclude].copy()
    
    print(f"→ done in {(time.perf_counter() - t0) / 60:.2f} min")
    return dataframe


def add_periods_to_all_sentences(dataframe):
    print("adding periods to all sentences...")
    t0 = time.perf_counter()
    
    dataframe['fr'] = dataframe['fr'] + "."
    dataframe['en'] = dataframe['en'] + "."
    
    print(f"→ done in {(time.perf_counter() - t0) / 60:.2f} min")
    return dataframe


def exclude_for_testing_data(dataframe):
    print("excluding columns to create testing data...")
    t0 = time.perf_counter()
    
    for feature, (low, high) in outlier_criteria_s3.items():
        col_name = f"exclude_relaxed_{feature}"
        dataframe[col_name] = False
        dataframe[col_name] = ~dataframe[feature].between(low, high)
    
    exclusion_relaxed_columns = [
        'exclude_relaxed_len_ratio',
        'exclude_relaxed_verb_ratio',
        'exclude_relaxed_noun_ratio',
        'exclude_relaxed_entity_ratio',
        'exclude_relaxed_clause_ratio',
        'exclude_relaxed_one_char_words_fr',
        'exclude_relaxed_one_char_words_en',
    ]
    
    dataframe["exclude_relaxed"] = dataframe[exclusion_relaxed_columns].any(axis=1)
    dataframe = dataframe[~dataframe["exclude_relaxed"] & dataframe["exclude"]]
    
    print(f"→ done in {(time.perf_counter() - t0) / 60:.2f} min")
    return dataframe


# CREATE TRAINING DATA

def create_dataset(dataframe, exclusion_func):
    dataframe = add_exclusion_columns(dataframe)
    dataframe = add_figref_column(dataframe)
    dataframe = add_dates_column(dataframe)
    dataframe = exclusion_func(dataframe)
    dataframe = add_periods_to_all_sentences(dataframe)
    
    return dataframe


def create_training_data(dataframe):
    dataframe = create_dataset(dataframe, exclude_for_training_data)
    return dataframe


def create_testing_data(dataframe):
    dataframe = create_dataset(dataframe, exclude_for_testing_data)
    return dataframe


def save_jsonl(dataframe, filename):
    with open(filename, "w", encoding="utf-8") as f:
        for i, row in enumerate(dataframe.itertuples(index=False)):
            f.write(json.dumps({
                "source": f"{row.en}",
                "target": f"{row.fr}",
                "source_lang": "en",
            }, ensure_ascii=False) + "\n")
            f.write(json.dumps({
                "source": f"{row.fr}",
                "target": f"{row.en}",
                "source_lang": "fr",
            }, ensure_ascii=False) + "\n")
