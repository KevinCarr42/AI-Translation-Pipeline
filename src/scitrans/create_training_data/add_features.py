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


def get_single_letter_words(text):
    if not isinstance(text, str):
        return []
    words = text.split()
    single_letters = []
    for i, word in enumerate(words):
        cleaned = word.strip('.,!?;:"\'-()[]{}')
        if len(cleaned) == 1:
            single_letters.append((i, cleaned.lower(), word))
    return single_letters


def is_legitimate_single_letter(letter, lang):
    legitimate_english = {'i', 'a'}
    legitimate_french = {'à', 'a', 'y', 'ô', 'ù'}
    
    letter_lower = letter.lower()
    if lang == 'en':
        return letter_lower in legitimate_english
    else:
        return letter_lower in legitimate_french


@print_timing("appending OCR_issue")
def add_ocr_issue_feature(dataframe):
    def check_text_for_ocr_issues(text, lang):
        if not isinstance(text, str):
            return False
        
        if " '" in text or " '" in text or "' " in text or "' " in text:
            return True
        
        singles = get_single_letter_words(text)
        for letter_info in singles:
            _, letter, _ = letter_info
            if letter.isdigit():
                continue
            if not is_legitimate_single_letter(letter, lang):
                return True
        
        return False
    
    ocr_issues = []
    
    for idx, row in dataframe.iterrows():
        has_issue = False
        
        if 'fr' in dataframe.columns and pd.notna(row.get('fr')):
            if check_text_for_ocr_issues(row['fr'], 'fr'):
                has_issue = True
        
        if 'en' in dataframe.columns and pd.notna(row.get('en')):
            if check_text_for_ocr_issues(row['en'], 'en'):
                has_issue = True
        
        ocr_issues.append(has_issue)
    
    dataframe['OCR_issue'] = ocr_issues
    return dataframe


def add_all_features(dataframe):
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
    
    dataframe = add_ocr_issue_feature(dataframe)
    print(f"TOTAL time: {(time.perf_counter() - t_total) / 60:.2f} min")
    
    return dataframe


def add_features(dataframe):
    all_features = config.MATCHED_DATA_WITH_FEATURES
    
    if os.path.exists(all_features):
        print(f"Loading {all_features}")
        return pd.read_pickle(all_features)
    
    else:
        print(f"calculating {all_features}...")
        df = add_all_features(dataframe)
        print("Saving file...")
        df.to_pickle(all_features)
        print("Save complete!\n")
        
        return df
