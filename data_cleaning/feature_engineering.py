import pandas as pd
import spacy
import numpy as np
import time


def add_features(dataframe):
    total_start = time.perf_counter()
    
    print("loading nlp language models")
    model_start = time.perf_counter()
    nlp_fr = spacy.load("fr_core_news_lg")
    nlp_en = spacy.load("en_core_web_lg")
    nlp_en.disable_pipes("parser")
    nlp_fr.disable_pipes("parser")
    print(f"→ done in {(time.perf_counter() - model_start) / 60:.2f} min")
    print(f"TOTAL time elapsed so far: {(time.perf_counter() - total_start) / 60:.2f} min")
    
    print("creating fr nlp pipe")
    pipe_start = time.perf_counter()
    docs_fr = list(nlp_fr.pipe(dataframe["fr"].astype(str), n_process=6, batch_size=1000))
    print(f"→ done in {(time.perf_counter() - pipe_start) / 60:.2f} min")
    print(f"TOTAL time elapsed so far: {(time.perf_counter() - total_start) / 60:.2f} min")
    
    print("creating en nlp pipe")
    pipe_start = time.perf_counter()
    docs_en = list(nlp_en.pipe(dataframe["en"].astype(str), n_process=6, batch_size=1000))
    print(f"→ done in {(time.perf_counter() - pipe_start) / 60:.2f} min")
    print(f"TOTAL time elapsed so far: {(time.perf_counter() - total_start) / 60:.2f} min")
    
    print('appending len_ratio')
    feature_start = time.perf_counter()
    dataframe["len_ratio"] = dataframe["fr"].str.len() / dataframe["en"].str.len()
    print(f"→ done in {(time.perf_counter() - feature_start) / 60:.2f} min")
    print(f"TOTAL time elapsed so far: {(time.perf_counter() - total_start) / 60:.2f} min")
    
    print('appending verb_ratio')
    feature_start = time.perf_counter()
    verb_counts_fr = [doc.count_by(spacy.attrs.POS).get(spacy.symbols.VERB, 0) + 1 for doc in docs_fr]
    verb_counts_en = [doc.count_by(spacy.attrs.POS).get(spacy.symbols.VERB, 0) + 1 for doc in docs_en]
    dataframe["verb_ratio"] = np.array(verb_counts_fr) / np.array(verb_counts_en)
    print(f"→ done in {(time.perf_counter() - feature_start) / 60:.2f} min")
    print(f"TOTAL time elapsed so far: {(time.perf_counter() - total_start) / 60:.2f} min")
    
    print('appending noun_ratio')
    feature_start = time.perf_counter()
    noun_counts_fr = [doc.count_by(spacy.attrs.POS).get(spacy.symbols.NOUN, 0) + 1 for doc in docs_fr]
    noun_counts_en = [doc.count_by(spacy.attrs.POS).get(spacy.symbols.NOUN, 0) + 1 for doc in docs_en]
    dataframe["noun_ratio"] = np.array(noun_counts_fr) / np.array(noun_counts_en)
    print(f"→ done in {(time.perf_counter() - feature_start) / 60:.2f} min")
    print(f"TOTAL time elapsed so far: {(time.perf_counter() - total_start) / 60:.2f} min")
    
    print('appending entity_ratio')
    feature_start = time.perf_counter()
    entity_counts_fr = [len(doc.ents) + 1 for doc in docs_fr]
    entity_counts_en = [len(doc.ents) + 1 for doc in docs_en]
    dataframe["entity_ratio"] = np.array(entity_counts_fr) / np.array(entity_counts_en)
    print(f"→ done in {(time.perf_counter() - feature_start) / 60:.2f} min")
    print(f"TOTAL time elapsed so far: {(time.perf_counter() - total_start) / 60:.2f} min")
    
    print('appending clause_ratio')
    feature_start = time.perf_counter()
    clauses_fr = dataframe["fr"].str.count(",") + dataframe["fr"].str.count(";") + 1
    clauses_en = dataframe["en"].str.count(",") + dataframe["en"].str.count(";") + 1
    dataframe["clause_ratio"] = clauses_fr / clauses_en
    print(f"→ done in {(time.perf_counter() - feature_start) / 60:.2f} min")
    print(f"TOTAL time elapsed so far: {(time.perf_counter() - total_start) / 60:.2f} min")
    
    print('fixing missing apostrophes in French')
    feature_start = time.perf_counter()
    apostrophe_letters = ['L', 'D', 'N', 'M', 'S', 'T', 'l', 'd', 'n', 'm', 's', 't']
    for letter in apostrophe_letters:
        dataframe["fr"] = dataframe["fr"].str.replace(f" {letter} ", f" {letter}'", regex=False)
        dataframe["fr"] = dataframe["fr"].str.replace(f"^{letter} ", f"{letter}'", regex=True)
    print(f"→ done in {(time.perf_counter() - feature_start) / 60:.2f} min")
    print(f"TOTAL time elapsed so far: {(time.perf_counter() - total_start) / 60:.2f} min")
    
    # TODO: confirm 'J ai' and 'don t' get fixed on second pass
    valid_one_char_words_fr = {'À', 'A', 'L', 'D', 'N', 'Y', 'M', 'S', 'T', 'à', 'a', 'l', 'd', 'n', 'y', 'm', 's', 't'}
    valid_one_char_words_en = {'A', 'I', 'O', 'a', 'i', 'o'}
    
    print('appending one_char_words_fr')
    feature_start = time.perf_counter()
    one_char_words_fr = dataframe["fr"].str.split().apply(lambda words: sum(1 for w in words if len(w) == 1 and w not in valid_one_char_words_fr)) / (dataframe["fr"].str.split().apply(len) + 1)
    dataframe["one_char_words_fr"] = one_char_words_fr
    print(f"→ done in {(time.perf_counter() - feature_start) / 60:.2f} min")
    print(f"TOTAL time elapsed so far: {(time.perf_counter() - total_start) / 60:.2f} min")
    
    print('appending one_char_words_en')
    feature_start = time.perf_counter()
    one_char_words_en = dataframe["en"].str.split().apply(lambda words: sum(1 for w in words if len(w) == 1 and w not in valid_one_char_words_en)) / (dataframe["en"].str.split().apply(len) + 1)
    dataframe["one_char_words_en"] = one_char_words_en
    print(f"→ done in {(time.perf_counter() - feature_start) / 60:.2f} min")
    print(f"TOTAL time: {(time.perf_counter() - total_start) / 60:.2f} min")
    
    return dataframe
