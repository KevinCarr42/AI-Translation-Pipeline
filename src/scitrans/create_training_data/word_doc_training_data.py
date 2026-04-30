import os
import re

import pandas as pd
import torch

from docx import Document
from sentence_transformers import SentenceTransformer

from scitrans import config
from scitrans.create_training_data.add_features import add_all_features
from scitrans.create_training_data.create_training_data import (
    add_dates_column,
    add_exclusion_columns,
    add_figref_column,
    add_periods_to_all_sentences,
    add_too_short_column,
    save_jsonl,
)
from scitrans.create_training_data.match_languages import (
    align_sentences,
    clean_text,
    create_similarity_matrix,
    split_text,
)
from scitrans.helpers.helpers import print_timing
from scitrans.proofreader.glossary import load_glossary
from scitrans.translate.word_document import _iter_document_elements

_ERRATUM_RE = re.compile(r'[\s\-\(\[]*erratum[\s\-\)\]]*', re.IGNORECASE)
_LANG_RE = re.compile(r'\b(english|french)\b', re.IGNORECASE)
_NUMBER_RE = re.compile(r'\b\d+(?:[.,]\d+)*\b')


def _normalise_filename(stem):
    erratum_match = _ERRATUM_RE.search(stem)
    is_erratum = erratum_match is not None
    working = _ERRATUM_RE.sub(' ', stem) if is_erratum else stem
    
    lang_match = _LANG_RE.search(working)
    if not lang_match:
        return None, None, is_erratum
    
    lang = "en" if lang_match.group(1).lower() == "english" else "fr"
    document_name = _LANG_RE.sub(' ', working)
    document_name = re.sub(r'\s+', ' ', document_name).strip(' -_')
    
    return document_name, lang, is_erratum


def pair_documents(root_path, regions=None):
    candidates = {}
    
    for dirpath, _, filenames in os.walk(root_path):
        region = os.path.basename(dirpath)
        if regions is not None and region not in regions:
            continue
        
        for filename in filenames:
            if filename.startswith('~$'):
                continue
            if not filename.lower().endswith('.docx'):
                continue
            
            stem = os.path.splitext(filename)[0]
            document_name, lang, is_erratum = _normalise_filename(stem)
            if document_name is None or lang is None:
                continue
            
            path = os.path.join(dirpath, filename)
            candidates.setdefault(document_name, {"region": region})
            candidates[document_name][(lang, is_erratum)] = path
    
    paired = {}
    for document_name in sorted(candidates):
        entry = candidates[document_name]
        region = entry.get("region")
        
        fr_erratum = entry.get(("fr", True))
        en_erratum = entry.get(("en", True))
        fr_normal = entry.get(("fr", False))
        en_normal = entry.get(("en", False))
        
        if fr_erratum and en_erratum:
            fr_path, en_path, is_erratum = fr_erratum, en_erratum, True
        elif fr_normal and en_normal:
            fr_path, en_path, is_erratum = fr_normal, en_normal, False
        else:
            continue
        
        paired[document_name] = {
            "fr": fr_path,
            "en": en_path,
            "is_erratum": is_erratum,
            "region": region,
        }
    
    return paired


def extract_text_from_docx(docx_path):
    document = Document(docx_path)
    parts = []
    
    for element, _location, element_type in _iter_document_elements(document):
        if element_type == "paragraph":
            text = element.text
            if text:
                parts.append(text)
        elif element_type == "cell":
            for paragraph in element.paragraphs:
                text = paragraph.text
                if text:
                    parts.append(text)
    
    return " ".join(parts)


def docx_to_aligned_rows(fr_path, en_path, document_name, sentence_encoder, device):
    text_fr = clean_text(extract_text_from_docx(fr_path))
    text_en = clean_text(extract_text_from_docx(en_path))
    
    sentences_fr = [s for s in split_text(text_fr) if 10 <= len(s) <= 500]
    sentences_en = [s for s in split_text(text_en) if 10 <= len(s) <= 500]
    
    if not sentences_fr or not sentences_en:
        return []
    
    similarity_matrix = create_similarity_matrix(sentences_fr, sentences_en, sentence_encoder, device)
    aligned_pairs = align_sentences(similarity_matrix)
    
    return [
        (document_name, sentences_fr[i], sentences_en[j], round(score, 3))
        for i, j, score in aligned_pairs
    ]


@print_timing("create matched docx data")
def create_matched_data_docx():
    if os.path.exists(config.WORDDOC_MATCHED_DATA):
        print(f"loading {config.WORDDOC_MATCHED_DATA}")
        return pd.read_pickle(config.WORDDOC_MATCHED_DATA)
    
    print("pairing documents...")
    pairs = pair_documents(config.TRANSLATED_DOCX_PUBLICATIONS_PATH)
    print(f"found {len(pairs)} paired documents")
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"using device: {device}")
    
    print("loading sentence encoder...")
    sentence_encoder = SentenceTransformer(
        'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
    ).to(device)
    
    rows = []
    for i, (document_name, info) in enumerate(pairs.items(), 1):
        print(f"  [{i}/{len(pairs)}] {document_name}")
        rows.extend(docx_to_aligned_rows(
            info["fr"], info["en"], document_name, sentence_encoder, device
        ))
    
    df = pd.DataFrame(rows, columns=["document_name", "fr", "en", "similarity"])
    df.to_pickle(config.WORDDOC_MATCHED_DATA)
    print(f"saved {len(df)} matched rows to {config.WORDDOC_MATCHED_DATA}")
    
    return df


@print_timing("add docx features")
def add_features_docx(df):
    if os.path.exists(config.WORDDOC_MATCHED_DATA_WITH_FEATURES):
        print(f"loading {config.WORDDOC_MATCHED_DATA_WITH_FEATURES}")
        return pd.read_pickle(config.WORDDOC_MATCHED_DATA_WITH_FEATURES)
    
    df = add_all_features(df)
    df.to_pickle(config.WORDDOC_MATCHED_DATA_WITH_FEATURES)
    return df


def _build_compiled_glossary(glossary_path):
    en_glossary = load_glossary(glossary_path, source_lang="en")
    fr_glossary = load_glossary(glossary_path, source_lang="fr")
    
    en_compiled = [
        (re.compile(rf'\b{re.escape(src)}\b', re.IGNORECASE),
         re.compile(rf'\b{re.escape(tgt)}\b', re.IGNORECASE))
        for src, tgt in en_glossary.items() if len(src) >= 2
    ]
    fr_compiled = [
        (re.compile(rf'\b{re.escape(src)}\b', re.IGNORECASE),
         re.compile(rf'\b{re.escape(tgt)}\b', re.IGNORECASE))
        for src, tgt in fr_glossary.items() if len(src) >= 2
    ]
    return en_compiled, fr_compiled


def _row_has_unmatched_constraint(en_text, fr_text, en_compiled, fr_compiled):
    for src_pat, tgt_pat in en_compiled:
        if src_pat.search(en_text) and not tgt_pat.search(fr_text):
            return True
    for src_pat, tgt_pat in fr_compiled:
        if src_pat.search(fr_text) and not tgt_pat.search(en_text):
            return True
    return False


@print_timing("add lexical constraints column")
def add_lexical_constraint_column(df, glossary_path=None):
    if glossary_path is None:
        glossary_path = config.PREFERENTIAL_JSON_PATH
    
    en_compiled, fr_compiled = _build_compiled_glossary(glossary_path)
    
    df['unmatched_lexical_constraints'] = df.apply(
        lambda row: _row_has_unmatched_constraint(row['en'], row['fr'], en_compiled, fr_compiled),
        axis=1,
    )
    return df


def _numbers_in(text):
    # strip decimal/thousands separators so "1.5" and "1,5" compare equal
    return frozenset(re.sub(r'[.,]', '', m) for m in _NUMBER_RE.findall(text))


@print_timing("add number mismatch column")
def add_number_mismatch_column(df):
    df['has_number_mismatch'] = df.apply(
        lambda row: _numbers_in(row['en']) != _numbers_in(row['fr']),
        axis=1,
    )
    return df


@print_timing("exclude rows for training data")
def exclude_for_word_doc_training_data(df):
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
        'unmatched_lexical_constraints',
        'has_number_mismatch',
    ]
    df['exclude'] = df[exclusion_columns].any(axis=1)
    df.to_pickle(config.WORDDOC_FINAL_DATA)
    return df


def create_word_doc_training_data_pipeline():
    # TODO: still need to control for:
    #  duplicates
    #  untranslated text (references etc)
    #  names, references, etc
    
    # TODO:
    #  consider making a helper function that can summarize each df rows/cols, n excluded, etc - basic stats
    
    df = create_matched_data_docx()
    df = add_features_docx(df)
    df = add_exclusion_columns(df)
    df = add_figref_column(df)
    df = add_too_short_column(df)
    df = add_dates_column(df)
    df = add_lexical_constraint_column(df)
    df = add_number_mismatch_column(df)
    df = exclude_for_word_doc_training_data(df)
    
    df_for_jsonl = add_periods_to_all_sentences(df[~df['exclude']].copy())
    save_jsonl(df_for_jsonl, config.WORDDOC_TRAINING_DATA)
    
    return df


if __name__ == "__main__":
    create_word_doc_training_data_pipeline()
