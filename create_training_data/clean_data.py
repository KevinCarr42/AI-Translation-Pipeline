import unicodedata
import re
import pandas as pd

from collections import Counter
from spellchecker import SpellChecker
from helpers.helpers import print_timing


def clean_text(text):
    allow_numbers = True
    
    if allow_numbers:
        allowed_chars = r"[^a-zA-ZÀ-ÖØ-öø-ÿ0-9.,;:!?()'\"-]"
    else:
        allowed_chars = r"[^a-zA-ZÀ-ÖØ-öø-ÿ.,;:!?()'\"-]"
    text = re.sub(allowed_chars, ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


@print_timing("cleaning OCR errors...")
def clean_ocr_errors(dataframe):
    # FIXME: missing some patterns (e.g., "don t" and "J ai")
    #  use updated contraction cleaning algorithm
    
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
        
        # TODO: check end of sentence?
    
    # TODO: also fix english apostrophe errors
    dataframe['fr'] = dataframe['fr'].replace(
        dict(zip(missing_apostrophe_patterns, replacement_patterns)),
        regex=True
    )
    
    return dataframe


@print_timing("cleaning misaccented words...")
def clean_misaccented_words(dataframe, replacement_dict):
    def create_replacement_regex(replacement_map):
        pattern = r'\b(' + '|'.join([re.escape(k) for k in replacement_map.keys()]) + r')\b'
        
        def func(match):
            matched_word = match.group(1)
            return replacement_map.get(matched_word, matched_word)
        
        return pattern, func
    
    replace_pattern, replace_func = create_replacement_regex(replacement_dict)
    dataframe['fr'] = dataframe['fr'].str.replace(replace_pattern, replace_func, regex=True)
    
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
    
    accent_mapping = accent_mapping.drop_duplicates('anglicised', keep=False)
    spell = SpellChecker(language='fr')
    
    return accent_mapping[~accent_mapping['anglicised'].isin(spell)]


def clean_data(dataframe):
    # cleaning formerly done in create_matched_data()
    dataframe['fr'] = dataframe['fr'].apply(clean_text)
    dataframe['en'] = dataframe['en'].apply(clean_text)
    
    # cleaning formerly done in add_features()
    dataframe = clean_ocr_errors(dataframe)
    accent_mapping = build_accent_mapping(dataframe)
    replacement_dict = accent_mapping.head(1000).set_index('anglicised')['accented'].to_dict()
    dataframe = clean_misaccented_words(dataframe, replacement_dict)
    
    return dataframe, accent_mapping
