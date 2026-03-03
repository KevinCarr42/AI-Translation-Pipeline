import json
import re

from helpers.helpers import print_timing

outlier_criteria_s1 = {
    "len_ratio": (0.75, 1.92),  # override with 2 stdev len ratios
    "verb_ratio": (0.75, 1.50),
    "noun_ratio": (1.00, 1.75),
    "entity_ratio": (0.33, 1.00),
    "clause_ratio": (1.00, 1.50),
}

outlier_criteria_s2 = {
    "len_ratio": (0.75, 1.92),
    "verb_ratio": (0.50, 3.00),
    "noun_ratio": (0.67, 4.00),
    "entity_ratio": (0.17, 2.00),
    "clause_ratio": (0.50, 3.00),
}

outlier_criteria_s3 = {
    "len_ratio": (0.34, 3.93),
    "verb_ratio": (0.25, 5.00),
    "noun_ratio": (0.38, 12.00),
    "entity_ratio": (0.10, 4.00),
    "clause_ratio": (0.20, 6.00),
}


@print_timing("adding exclusion columns based on similarity scores...")
def add_exclusion_columns(dataframe):
    # Note:
    #  thresholds increased 1 stdev from original POC to improve training data quality
    #  median, +1 stdev, +2 stdev
    low_p, med_p, high_p = 0.85, 0.92, 0.99
    
    dataframe["exclude_low_similarity"] = dataframe["similarity"] < low_p
    
    s1_mask = dataframe["similarity"] < med_p
    s2_mask = (dataframe["similarity"] >= med_p) & (dataframe["similarity"] < high_p)
    s3_mask = dataframe["similarity"] >= high_p
    
    for feature in outlier_criteria_s1:
        col_name = f"exclude_{feature}"
        dataframe[col_name] = False
        
        low1, high1 = outlier_criteria_s1[feature]
        low2, high2 = outlier_criteria_s2[feature]
        low3, high3 = outlier_criteria_s3[feature]
        
        dataframe.loc[s1_mask, col_name] = ~dataframe.loc[s1_mask, feature].between(low1, high1)
        dataframe.loc[s2_mask, col_name] = ~dataframe.loc[s2_mask, feature].between(low2, high2)
        dataframe.loc[s3_mask, col_name] = ~dataframe.loc[s3_mask, feature].between(low3, high3)
    
    return dataframe


def analyze_text_for_figrefs(text, language='en'):
    result = {
        'has_leading_numbers': False,
        'has_trailing_numbers': False,
        'has_parenthetical_numbers': False,
        'has_figure_references': False,
        'has_repeated_punctuation': False,
        'exclude_figtext': False
    }
    
    if re.search(r'^\s*\d+\s+', text):
        result['has_leading_numbers'] = True
    
    if re.search(r'\s+\d+\s*$', text):
        result['has_trailing_numbers'] = True
    
    if re.search(r'\s+\(\d+\)\s*$', text):
        result['has_parenthetical_numbers'] = True
    
    if language == 'fr':
        pattern = r'\s*(?:Figure|Tableau|Fig\.?|Tab\.?)\s+\d+.*$'
    else:
        pattern = r'\s*(?:Figure|Table|Fig\.?|Tab\.?)\s+\d+.*$'
    if re.search(pattern, text, flags=re.IGNORECASE):
        result['has_figure_references'] = True
    
    if re.search(r'[.!?]{2,}$', text):
        result['has_repeated_punctuation'] = True
    
    result['exclude_figtext'] = any([
        result['has_figure_references'],
        result['has_leading_numbers'],
        result['has_trailing_numbers'],
        result['has_parenthetical_numbers'],
        result['has_repeated_punctuation']
    ])
    
    return result


@print_timing("adding exclusion column for detected figure and table text...")
def add_figref_column(dataframe, text_en_column='en', text_fr_column='fr'):
    en_results = dataframe[text_en_column].apply(lambda x: analyze_text_for_figrefs(x, language='en'))
    fr_results = dataframe[text_fr_column].apply(lambda x: analyze_text_for_figrefs(x, language='fr'))
    
    dataframe['exclude_figtext'] = (
            en_results.apply(lambda x: x['exclude_figtext']) |
            fr_results.apply(lambda x: x['exclude_figtext'])
    )
    
    return dataframe


@print_timing("adding exclusion column for short text...")
def add_too_short_column(dataframe, min_length=20):
    dataframe['exclude_too_short'] = (
            (dataframe['en'].str.len() < min_length) |
            (dataframe['fr'].str.len() < min_length)
    )
    return dataframe


@print_timing("adding exclusion column for dates...")
def add_dates_column(dataframe):
    dataframe['has_date_refs'] = dataframe[['en', 'fr']].apply(lambda x: x.astype(str).str.contains(
        r'\b(?:19|20)\d{2}\b|(?:January|February|March|April|May|June|July|August|September|October'
        r'|November|December|janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre'
        r'|décembre|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b',
        case=False, regex=True).any(), axis=1)
    
    return dataframe


@print_timing("excluding columns to create training data...")
def exclude_for_training_data(dataframe):
    exclusion_columns = [
        'exclude_low_similarity',
        'exclude_len_ratio',
        'exclude_verb_ratio',
        'exclude_noun_ratio',
        'exclude_entity_ratio',
        'exclude_clause_ratio',
        'exclude_figtext',
        'exclude_too_short',
        'has_date_refs',
        'OCR_issue',
    ]
    dataframe["exclude"] = dataframe[exclusion_columns].any(axis=1)
    dataframe = dataframe[~dataframe.exclude].copy()
    
    return dataframe


@print_timing("adding periods to all sentences...")
def add_periods_to_all_sentences(dataframe):
    dataframe.loc[:, 'fr'] = dataframe['fr'].apply(
        lambda x: x if x.endswith(('.', '!', '?')) else x + "."
    )
    dataframe.loc[:, 'en'] = dataframe['en'].apply(
        lambda x: x if x.endswith(('.', '!', '?')) else x + "."
    )
    
    return dataframe


@print_timing("excluding columns to create testing data...")
def exclude_for_testing_data(dataframe):
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
        'exclude_too_short',
        'OCR_issue',
    ]
    
    dataframe["exclude_relaxed"] = dataframe[exclusion_relaxed_columns].any(axis=1)
    dataframe = dataframe[~dataframe["exclude_relaxed"] & dataframe["exclude"]]
    
    return dataframe


def create_dataset(dataframe, exclusion_func):
    dataframe = add_exclusion_columns(dataframe)
    dataframe = add_figref_column(dataframe)
    dataframe = add_too_short_column(dataframe)
    dataframe = add_dates_column(dataframe)
    dataframe = exclusion_func(dataframe)
    dataframe = add_periods_to_all_sentences(dataframe)
    
    return dataframe


def create_training_data(dataframe):
    dataframe = create_dataset(dataframe, exclude_for_training_data)
    print("Training dataset created.")
    return dataframe


def create_testing_data(dataframe):
    dataframe = create_dataset(dataframe, exclude_for_testing_data)
    print("Testing dataset created.")
    return dataframe


def save_jsonl(dataframe, filename):
    print("Saving file...")
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
    print("Save complete!\n")
