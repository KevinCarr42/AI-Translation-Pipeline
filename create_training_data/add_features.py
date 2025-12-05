import os
import unicodedata
import re
import spacy
import time

import pandas as pd
import numpy as np

from collections import Counter
from spellchecker import SpellChecker

import config


# ADD FEATURES

def add_some_features(dataframe):
    t_total = time.perf_counter()
    
    print("loading nlp language models")
    t0 = time.perf_counter()
    nlp_fr = spacy.load("fr_core_news_lg")
    nlp_en = spacy.load("en_core_web_lg")
    nlp_en.disable_pipes("parser")
    nlp_fr.disable_pipes("parser")
    print(f"→ done in {(time.perf_counter() - t0) / 60:.2f} min")
    print(f"TOTAL time elapsed so far: {(time.perf_counter() - t_total) / 60:.2f} min")
    
    print("creating fr nlp pipe")
    t0 = time.perf_counter()
    docs_fr = list(nlp_fr.pipe(dataframe["fr"].astype(str), n_process=6, batch_size=1000))
    print(f"→ done in {(time.perf_counter() - t0) / 60:.2f} min")
    print(f"TOTAL time elapsed so far: {(time.perf_counter() - t_total) / 60:.2f} min")
    
    print("creating en nlp pipe")
    t0 = time.perf_counter()
    docs_en = list(nlp_en.pipe(dataframe["en"].astype(str), n_process=6, batch_size=1000))
    print(f"→ done in {(time.perf_counter() - t0) / 60:.2f} min")
    print(f"TOTAL time elapsed so far: {(time.perf_counter() - t_total) / 60:.2f} min")
    
    print('appending len_ratio')
    t0 = time.perf_counter()
    dataframe["len_ratio"] = dataframe["fr"].str.len() / dataframe["en"].str.len()
    print(f"→ done in {(time.perf_counter() - t0) / 60:.2f} min")
    print(f"TOTAL time elapsed so far: {(time.perf_counter() - t_total) / 60:.2f} min")
    
    print('appending verb_ratio')
    t0 = time.perf_counter()
    verb_counts_fr = [doc.count_by(spacy.attrs.POS).get(spacy.symbols.VERB, 0) + 1 for doc in docs_fr]
    verb_counts_en = [doc.count_by(spacy.attrs.POS).get(spacy.symbols.VERB, 0) + 1 for doc in docs_en]
    dataframe["verb_ratio"] = np.array(verb_counts_fr) / np.array(verb_counts_en)
    print(f"→ done in {(time.perf_counter() - t0) / 60:.2f} min")
    print(f"TOTAL time elapsed so far: {(time.perf_counter() - t_total) / 60:.2f} min")
    
    print('appending noun_ratio')
    t0 = time.perf_counter()
    noun_counts_fr = [doc.count_by(spacy.attrs.POS).get(spacy.symbols.NOUN, 0) + 1 for doc in docs_fr]
    noun_counts_en = [doc.count_by(spacy.attrs.POS).get(spacy.symbols.NOUN, 0) + 1 for doc in docs_en]
    dataframe["noun_ratio"] = np.array(noun_counts_fr) / np.array(noun_counts_en)
    print(f"→ done in {(time.perf_counter() - t0) / 60:.2f} min")
    print(f"TOTAL time elapsed so far: {(time.perf_counter() - t_total) / 60:.2f} min")
    
    print('appending entity_ratio')
    t0 = time.perf_counter()
    ent_counts_fr = [len(doc.ents) + 1 for doc in docs_fr]
    ent_counts_en = [len(doc.ents) + 1 for doc in docs_en]
    dataframe["entity_ratio"] = np.array(ent_counts_fr) / np.array(ent_counts_en)
    print(f"→ done in {(time.perf_counter() - t0) / 60:.2f} min")
    print(f"TOTAL time elapsed so far: {(time.perf_counter() - t_total) / 60:.2f} min")
    
    print('appending clause_ratio')
    t0 = time.perf_counter()
    clauses_fr = dataframe["fr"].str.count(",") + dataframe["fr"].str.count(";") + 1
    clauses_en = dataframe["en"].str.count(",") + dataframe["en"].str.count(";") + 1
    dataframe["clause_ratio"] = clauses_fr / clauses_en
    print(f"→ done in {(time.perf_counter() - t0) / 60:.2f} min")
    print(f"TOTAL time: {(time.perf_counter() - t_total) / 60:.2f} min")
    
    return dataframe


def add_more_features(dataframe):
    print('appending one char word statistics')
    t0 = time.perf_counter()
    
    # FIXME: should these include always have apostrophe words like "J"
    #  (if so "J" is missing, if not some should not be included)
    # add features - single char words
    actual_one_char_words_fr = ['À', 'A', 'L', 'D', 'N', 'Y', 'M', 'S', 'T', 'à', 'a', 'l', 'd', 'n', 'y', 'm', 's', 't']
    dataframe['one_char_words_fr'] = dataframe['fr'].apply(lambda s: sum(len(w) == 1 for w in s.split() if w not in actual_one_char_words_fr))
    
    actual_one_char_words_en = ['A', 'I', 'O', 'a', 'o']
    dataframe['one_char_words_en'] = dataframe['en'].apply(lambda s: sum(len(w) == 1 for w in s.split() if w not in actual_one_char_words_en))
    print(f"→ done in {(time.perf_counter() - t0) / 60:.2f} min")
    
    # FIXME: should this be earlier? in data cleaning?
    dataframe = clean_ocr_errors(dataframe)
    replacement_dict, potential_accent_issues_uncommon = build_accent_mapping(dataframe)
    dataframe = clean_misaccented_words(dataframe, replacement_dict)
    dataframe = add_misaccented_column(dataframe, potential_accent_issues_uncommon)
    
    return dataframe


def clean_ocr_errors(dataframe):
    print('cleaning OCR errors...')
    t0 = time.perf_counter()
    
    # FIXME: missing some patterns (e.g., "don t" and "J ai")
    
    always_have_apostrophe = ['L', 'D', 'N', 'M', 'S', 'T', 'l', 'd', 'n', 'm', 's', 't']
    
    missing_apostrophe_patterns = []
    replacement_patterns = []
    
    for letter in always_have_apostrophe:
        # mid-sentence
        missing_apostrophe_patterns.append(f" {letter} ")
        replacement_patterns.append(f" {letter}'")
        
        # start of sentence
        missing_apostrophe_patterns.append(f"^{letter} ")
        replacement_patterns.append(f"{letter}'")
        
        # TODO: end of sentence?
    
    n_with_missing = dataframe.loc[
        dataframe['fr'].str.contains('|'.join(missing_apostrophe_patterns), na=False, case=False),
    ].shape[0]
    n_total = dataframe.shape[0]
    print(f"\t→ {n_with_missing} out of {n_total} sentences are missing apostrophes ({n_with_missing / n_total:.0%})")
    
    dataframe['fr'] = dataframe['fr'].replace(
        dict(zip(missing_apostrophe_patterns, replacement_patterns)),
        regex=True
    )
    
    print(f"→ done in {(time.perf_counter() - t0) / 60:.2f} min")
    return dataframe


def build_accent_mapping(dataframe):
    def has_non_english_chars(word):
        return bool(re.search(r'[^\x00-\x7F]', word))
    
    def remove_accents(text):
        return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    
    french_words_with_accents = []
    for sentence in dataframe['fr'].to_list():
        for word in sentence.split():
            clean_word = word.replace('(', '').replace(')', '')
            if clean_word.isalpha() and has_non_english_chars(clean_word):
                french_words_with_accents.append(clean_word.lower())
    
    word_counts = Counter(french_words_with_accents)
    
    accent_mapping = pd.DataFrame([
        {
            'anglicised': remove_accents(word),
            'accented': word,
            'count': count
        }
        for word, count in word_counts.items()
    ]).sort_values('count', ascending=False).reset_index(drop=True)
    
    # check accent_mapping for duplicates
    #  create list of duplicates (to classify as potential quality issues)
    potential_accent_issues_ambiguous = accent_mapping.loc[accent_mapping.duplicated('anglicised', keep="first"), 'anglicised'].to_list()
    #  split into non-duplicates (to clean)
    accent_mapping = accent_mapping.drop_duplicates('anglicised', keep=False)
    
    # check for real words in mispelled list
    spell = SpellChecker(language='fr')
    #  add all anglicised words that are real french words to another different potentially bad word list
    potential_accent_issues_real_words = accent_mapping.loc[accent_mapping['anglicised'].isin(spell), 'anglicised'].to_list()
    #  remove all anglicised words that are real french words
    accent_mapping = accent_mapping[~accent_mapping['anglicised'].isin(spell)]
    
    # take the top 1000 most common words that could be cleaned
    #  add the rest to the potentially bad words
    potential_accent_issues_uncommon = accent_mapping.tail(accent_mapping.shape[0] - 1000).anglicised.to_list()
    # create dict from remaining words for cleaning
    accent_mapping = accent_mapping.head(1000)
    replacement_dict = accent_mapping.set_index('anglicised')['accented'].to_dict()
    
    return replacement_dict, potential_accent_issues_uncommon


def clean_misaccented_words(dataframe, replacement_dict):
    print('cleaning misaccented words...')
    t0 = time.perf_counter()
    
    def create_replacement_regex(replacement_map):
        pattern = r'\b(' + '|'.join([re.escape(k) for k in replacement_map.keys()]) + r')\b'
        
        def replace_func(match):
            matched_word = match.group(1)
            return replacement_map.get(matched_word, matched_word)
        
        return pattern, replace_func
    
    pattern, replace_func = create_replacement_regex(replacement_dict)
    dataframe['fr'] = dataframe['fr'].str.replace(pattern, replace_func, regex=True)
    
    print(f"→ done in {(time.perf_counter() - t0) / 60:.2f} min")
    return dataframe


def add_misaccented_column(dataframe, potential_accent_issues_uncommon):
    print("adding column for potential accent issues (this will take a while :/)..")
    t0 = time.perf_counter()
    
    dataframe['potential_fr_accent_issues'] = dataframe['fr'].apply(lambda s: sum(w in potential_accent_issues_uncommon for w in s.split()))
    
    print(f"→ done in {(time.perf_counter() - t0) / 60:.2f} min")
    return dataframe


def add_features(dataframe):
    some_features = config.MATCHED_DATA_WITH_FEATURES
    all_features = config.MATCHED_DATA_WITH_ALL_FEATURES
    
    if os.path.exists(all_features):
        print(f"Loading {all_features}")
        return pd.read_pickle(all_features)
    
    elif os.path.exists(some_features):
        print(f"Loading {some_features}")
        df = pd.read_pickle(some_features)
        
        print(f"Calculating {all_features}...")
        df = add_more_features(df)
        print("Saving file...")
        df.to_pickle(all_features)
        print("Save complete!\n")
        return df
    
    else:
        print(f"Calculating {some_features}...")
        df = add_some_features(dataframe)
        print("Saving file...")
        df.to_pickle(some_features)
        print("Save complete!\n")
        
        print(f"calculating {all_features}...")
        df = add_more_features(df)
        print("Saving file...")
        df.to_pickle(all_features)
        print("Save complete!\n")
        
        return df



