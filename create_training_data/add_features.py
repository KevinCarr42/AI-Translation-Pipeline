import os
import spacy
import time

import pandas as pd
import numpy as np

import config
from create_training_data.clean_data import build_accent_mapping


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
    
    # FIXME: should bein data cleaning
    # dataframe = clean_ocr_errors(dataframe) # FIXME: moved to clean_data.py
    accent_mapping = build_accent_mapping(dataframe)
    potential_accent_issues = accent_mapping.tail(accent_mapping.shape[0] - 1000).anglicised.to_list()
    # dataframe = clean_misaccented_words(dataframe, replacement_dict) # FIXME: moved to clean_data.py
    dataframe = add_misaccented_column(dataframe, potential_accent_issues)
    
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



