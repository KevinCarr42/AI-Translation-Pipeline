import os
import spacy
import time

import pandas as pd
import numpy as np

import config
from helpers.helpers import print_timing


@print_timing("loading nlp language models")
def loading_nlp_language_models():
    nlp_fr = spacy.load("fr_core_news_lg")
    nlp_en = spacy.load("en_core_web_lg")
    nlp_en.disable_pipes("parser")
    nlp_fr.disable_pipes("parser")
    return nlp_fr, nlp_en


@print_timing("creating fr nlp pipe")
def creating_fr_nlp_pipe(dataframe, nlp_fr):
    docs_fr = list(nlp_fr.pipe(dataframe["fr"].astype(str), n_process=6, batch_size=1000))
    return docs_fr


@print_timing("creating en nlp pipe")
def creating_en_nlp_pipe(dataframe, nlp_en):
    docs_en = list(nlp_en.pipe(dataframe["en"].astype(str), n_process=6, batch_size=1000))
    return docs_en


@print_timing("appending len_ratio")
def appending_len_ratio(dataframe):
    dataframe["len_ratio"] = dataframe["fr"].str.len() / dataframe["en"].str.len()
    return dataframe


@print_timing("appending verb_ratio")
def appending_verb_ratio(dataframe, docs_fr, docs_en):
    verb_counts_fr = [doc.count_by(spacy.attrs.POS).get(spacy.symbols.VERB, 0) + 1 for doc in docs_fr]
    verb_counts_en = [doc.count_by(spacy.attrs.POS).get(spacy.symbols.VERB, 0) + 1 for doc in docs_en]
    dataframe["verb_ratio"] = np.array(verb_counts_fr) / np.array(verb_counts_en)
    return dataframe


@print_timing("appending noun_ratio")
def appending_noun_ratio(dataframe, docs_fr, docs_en):
    noun_counts_fr = [doc.count_by(spacy.attrs.POS).get(spacy.symbols.NOUN, 0) + 1 for doc in docs_fr]
    noun_counts_en = [doc.count_by(spacy.attrs.POS).get(spacy.symbols.NOUN, 0) + 1 for doc in docs_en]
    dataframe["noun_ratio"] = np.array(noun_counts_fr) / np.array(noun_counts_en)
    return dataframe


@print_timing("appending entity_ratio")
def appending_entity_ratio(dataframe, docs_fr, docs_en):
    ent_counts_fr = [len(doc.ents) + 1 for doc in docs_fr]
    ent_counts_en = [len(doc.ents) + 1 for doc in docs_en]
    dataframe["entity_ratio"] = np.array(ent_counts_fr) / np.array(ent_counts_en)
    return dataframe


@print_timing("appending clause_ratio")
def appending_clause_ratio(dataframe):
    clauses_fr = dataframe["fr"].str.count(",") + dataframe["fr"].str.count(";") + 1
    clauses_en = dataframe["en"].str.count(",") + dataframe["en"].str.count(";") + 1
    dataframe["clause_ratio"] = clauses_fr / clauses_en
    return dataframe


def add_some_features(dataframe):
    t_total = time.perf_counter()
    
    nlp_fr, nlp_en = loading_nlp_language_models()
    print(f"TOTAL time elapsed so far: {(time.perf_counter() - t_total) / 60:.2f} min")
    
    docs_fr = creating_fr_nlp_pipe(dataframe, nlp_fr)
    print(f"TOTAL time elapsed so far: {(time.perf_counter() - t_total) / 60:.2f} min")
    
    docs_en = creating_en_nlp_pipe(dataframe, nlp_en)
    print(f"TOTAL time elapsed so far: {(time.perf_counter() - t_total) / 60:.2f} min")
    
    dataframe = appending_len_ratio(dataframe)
    print(f"TOTAL time elapsed so far: {(time.perf_counter() - t_total) / 60:.2f} min")
    
    dataframe = appending_verb_ratio(dataframe, docs_fr, docs_en)
    print(f"TOTAL time elapsed so far: {(time.perf_counter() - t_total) / 60:.2f} min")
    
    dataframe = appending_noun_ratio(dataframe, docs_fr, docs_en)
    print(f"TOTAL time elapsed so far: {(time.perf_counter() - t_total) / 60:.2f} min")
    
    dataframe = appending_entity_ratio(dataframe, docs_fr, docs_en)
    print(f"TOTAL time elapsed so far: {(time.perf_counter() - t_total) / 60:.2f} min")
    
    dataframe = appending_clause_ratio(dataframe)
    print(f"TOTAL time: {(time.perf_counter() - t_total) / 60:.2f} min")
    
    return dataframe


@print_timing("appending one char word statistics")
def appending_one_char_word_statistics(dataframe):
    # FIXME: should these include always have apostrophe words like "J"
    #  (if so "J" is missing, if not some should not be included)
    actual_one_char_words_fr = ['À', 'A', 'L', 'D', 'N', 'Y', 'M', 'S', 'T', 'à', 'a', 'l', 'd', 'n', 'y', 'm', 's', 't']
    dataframe['one_char_words_fr'] = dataframe['fr'].apply(lambda s: sum(len(w) == 1 for w in s.split() if w not in actual_one_char_words_fr))
    
    actual_one_char_words_en = ['A', 'I', 'O', 'a', 'o']
    dataframe['one_char_words_en'] = dataframe['en'].apply(lambda s: sum(len(w) == 1 for w in s.split() if w not in actual_one_char_words_en))
    return dataframe


@print_timing("adding column for potential accent issues (this will take a while :/)..")
def add_misaccented_column(dataframe, potential_accent_issues_uncommon):
    dataframe['potential_fr_accent_issues'] = dataframe['fr'].apply(lambda s: sum(w in potential_accent_issues_uncommon for w in s.split()))
    return dataframe


def add_more_features(dataframe, accent_mapping):
    dataframe = appending_one_char_word_statistics(dataframe)
    
    potential_accent_issues = accent_mapping.tail(accent_mapping.shape[0] - 1000).anglicised.to_list()
    dataframe = add_misaccented_column(dataframe, potential_accent_issues)
    
    return dataframe


def add_features(dataframe, accent_mapping):
    some_features = config.MATCHED_DATA_WITH_FEATURES
    all_features = config.MATCHED_DATA_WITH_ALL_FEATURES
    
    if os.path.exists(all_features):
        print(f"Loading {all_features}")
        return pd.read_pickle(all_features)
    
    elif os.path.exists(some_features):
        print(f"Loading {some_features}")
        df = pd.read_pickle(some_features)
        
        print(f"Calculating {all_features}...")
        df = add_more_features(df, accent_mapping)
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
        df = add_more_features(df, accent_mapping)
        print("Saving file...")
        df.to_pickle(all_features)
        print("Save complete!\n")
        
        return df
