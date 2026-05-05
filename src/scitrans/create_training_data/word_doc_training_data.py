import json
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
from scitrans.create_training_data.language_classifier.language_classifier import LanguageClassifier
from scitrans.create_training_data.match_languages import (
    align_sentences,
    clean_text,
    split_text,
)
from scitrans.helpers.helpers import print_timing
from scitrans.proofreader.glossary import load_glossary
from scitrans.translate.word_document import _iter_document_elements

_ERRATUM_RE = re.compile(r'[\s\-\(\[]*erratum[\s\-\)\]]*', re.IGNORECASE)
_LANG_RE = re.compile(r'\b(english|french)\b', re.IGNORECASE)
_NUMBER_RE = re.compile(r'\b\d+(?:[.,]\d+)*\b')
_PARAGRAPH_MARKER = "###PARAGRAPH_BREAK_MARKER###"


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


def extract_paragraphs_from_docx(docx_path):
    # Yield full-paragraph text strings in document order. Splitting happens per-paragraph
    # downstream so sentence fragments from one paragraph cannot glue onto the next.
    document = Document(docx_path)
    paragraphs = []
    
    for element, _location, element_type in _iter_document_elements(document):
        if element_type == "paragraph":
            text = element.text
            if text and text.strip():
                paragraphs.append(text)
        elif element_type == "cell":
            for paragraph in element.paragraphs:
                text = paragraph.text
                if text and text.strip():
                    paragraphs.append(text)
    
    return paragraphs


def _extract_clean_paragraphs(docx_path):
    paragraphs = []
    for raw_paragraph in extract_paragraphs_from_docx(docx_path):
        cleaned = clean_text(raw_paragraph)
        if len(cleaned) >= 30:
            paragraphs.append(cleaned)
    return paragraphs


def _split_paragraph_to_sentences(paragraph_text):
    return [s for s in split_text(paragraph_text) if 10 <= len(s) <= 500]


def _similarity_matrix(texts_fr, texts_en, sentence_encoder, device, use_margin):
    # Margin scoring (sim / (mean_topk_fr + mean_topk_en)) helps suppress hubness on large
    # candidate pools (paragraph-level alignment across a whole doc). Inside an aligned
    # paragraph pair the candidate set is tiny (often <5 sentences each), so margin scoring
    # just compresses the dynamic range and we use raw cosine instead.
    embeddings_fr = sentence_encoder.encode(texts_fr, convert_to_tensor=True, device=device, batch_size=512)
    embeddings_en = sentence_encoder.encode(texts_en, convert_to_tensor=True, device=device, batch_size=512)
    embeddings_fr = torch.nn.functional.normalize(embeddings_fr, p=2, dim=1)
    embeddings_en = torch.nn.functional.normalize(embeddings_en, p=2, dim=1)
    sim_matrix = torch.matmul(embeddings_fr, embeddings_en.T)
    
    if not use_margin:
        return sim_matrix
    
    k = min(4, sim_matrix.shape[0], sim_matrix.shape[1])
    if k < 2:
        return sim_matrix
    
    nn_fr = torch.topk(sim_matrix, k, dim=1).values.mean(dim=1, keepdim=True)
    nn_en = torch.topk(sim_matrix, k, dim=0).values.mean(dim=0, keepdim=True)
    return sim_matrix / (nn_fr + nn_en)


def _flatten_with_markers(paragraphs):
    # Append _PARAGRAPH_MARKER after every non-empty paragraph. The DP scores marker->marker
    # at cosine 1.0 (identical text -> identical embedding), so the highest-weight path is
    # forced to step through paragraph boundaries — preventing alignments from drifting
    # across paragraphs when the two docs have differing structure.
    sentences = []
    is_marker = []
    sentence_to_paragraph = []
    for para_idx, paragraph in enumerate(paragraphs):
        para_sentences = _split_paragraph_to_sentences(paragraph)
        if not para_sentences:
            continue
        for sentence in para_sentences:
            sentences.append(sentence)
            is_marker.append(False)
            sentence_to_paragraph.append(para_idx)
        sentences.append(_PARAGRAPH_MARKER)
        is_marker.append(True)
        sentence_to_paragraph.append(para_idx)
    return sentences, is_marker, sentence_to_paragraph


def _refine_with_concatenation(aligned_pairs, sentences_fr, sentences_en, is_marker_fr, is_marker_en, sentence_encoder, device, threshold=0.7, max_gap=4, max_chars=800):
    # Between every consecutive pair of DP anchors, take the unaligned chunks on each side,
    # concatenate them, and check raw-cosine similarity. If above threshold, emit a single
    # row covering the concatenated text. Skip gaps that contain a paragraph marker —
    # those are paragraph boundaries we don't want to glue across.
    n_fr = len(sentences_fr)
    n_en = len(sentences_en)
    anchors = [(-1, -1)] + [(i, j) for i, j, _ in aligned_pairs] + [(n_fr, n_en)]
    
    fr_blocks = []
    en_blocks = []
    spans = []
    for k in range(len(anchors) - 1):
        fr_start = anchors[k][0] + 1
        fr_end = anchors[k + 1][0]
        en_start = anchors[k][1] + 1
        en_end = anchors[k + 1][1]
        if fr_start >= fr_end or en_start >= en_end:
            continue
        if fr_end - fr_start > max_gap or en_end - en_start > max_gap:
            continue
        if any(is_marker_fr[idx] for idx in range(fr_start, fr_end)):
            continue
        if any(is_marker_en[idx] for idx in range(en_start, en_end)):
            continue
        fr_text = ' '.join(sentences_fr[fr_start:fr_end])
        en_text = ' '.join(sentences_en[en_start:en_end])
        if len(fr_text) > max_chars or len(en_text) > max_chars:
            continue
        fr_blocks.append(fr_text)
        en_blocks.append(en_text)
        spans.append((fr_start, fr_end, en_start, en_end))
    
    if not fr_blocks:
        return []
    
    embeddings_fr = sentence_encoder.encode(fr_blocks, convert_to_tensor=True, device=device, batch_size=512)
    embeddings_en = sentence_encoder.encode(en_blocks, convert_to_tensor=True, device=device, batch_size=512)
    embeddings_fr = torch.nn.functional.normalize(embeddings_fr, p=2, dim=1)
    embeddings_en = torch.nn.functional.normalize(embeddings_en, p=2, dim=1)
    diag_scores = (embeddings_fr * embeddings_en).sum(dim=1).cpu().tolist()
    
    refined = []
    for idx, (fr_start, fr_end, en_start, en_end) in enumerate(spans):
        score = float(diag_scores[idx])
        if score >= threshold:
            refined.append((fr_start, fr_end, en_start, en_end, fr_blocks[idx], en_blocks[idx], score))
    return refined


def docx_to_aligned_rows(fr_path, en_path, document_name, sentence_encoder, device, region=None, is_erratum=False):
    paragraphs_fr = _extract_clean_paragraphs(fr_path)
    paragraphs_en = _extract_clean_paragraphs(en_path)
    
    sentences_fr, is_marker_fr, sentence_to_paragraph_fr = _flatten_with_markers(paragraphs_fr)
    sentences_en, is_marker_en, sentence_to_paragraph_en = _flatten_with_markers(paragraphs_en)
    
    n_real_fr = sum(1 for m in is_marker_fr if not m)
    n_real_en = sum(1 for m in is_marker_en if not m)
    
    stats = {
        "document_name": document_name,
        "region": region,
        "is_erratum": is_erratum,
        "n_paragraphs_fr": len(paragraphs_fr),
        "n_paragraphs_en": len(paragraphs_en),
        "n_paragraphs_aligned_fr": 0,
        "n_paragraphs_aligned_en": 0,
        "pct_paragraphs_matched_fr": 0.0,
        "pct_paragraphs_matched_en": 0.0,
        "n_sentences_fr": n_real_fr,
        "n_sentences_en": n_real_en,
        "n_sentences_aligned": 0,
        "pct_sentences_matched_fr": 0.0,
        "pct_sentences_matched_en": 0.0,
        "similarity_mean": None,
        "similarity_min": None,
        "similarity_max": None,
    }
    
    if not sentences_fr or not sentences_en:
        return [], stats
    
    # Whole-document monotonic DP on raw-cosine matrix; markers anchor the path to paragraph
    # boundaries (option 2 with paragraph-marker anchors).
    sim_matrix = _similarity_matrix(sentences_fr, sentences_en, sentence_encoder, device, use_margin=False)
    aligned_pairs = align_sentences(sim_matrix)
    
    refined = _refine_with_concatenation(
        aligned_pairs, sentences_fr, sentences_en, is_marker_fr, is_marker_en, sentence_encoder, device
    )
    
    rows = []
    consumed_fr = set()
    consumed_en = set()
    for i, j, score in aligned_pairs:
        if is_marker_fr[i] or is_marker_en[j]:
            continue
        rows.append((document_name, sentences_fr[i], sentences_en[j], round(score, 3)))
        consumed_fr.add(i)
        consumed_en.add(j)
    
    for fr_start, fr_end, en_start, en_end, fr_text, en_text, score in refined:
        rows.append((document_name, fr_text, en_text, round(score, 3)))
        consumed_fr.update(range(fr_start, fr_end))
        consumed_en.update(range(en_start, en_end))
    
    aligned_paragraphs_fr = {sentence_to_paragraph_fr[i] for i in consumed_fr}
    aligned_paragraphs_en = {sentence_to_paragraph_en[j] for j in consumed_en}
    scores = [r[3] for r in rows]
    
    stats["n_sentences_aligned"] = len(rows)
    if n_real_fr:
        stats["pct_sentences_matched_fr"] = round(100 * len(consumed_fr) / n_real_fr, 1)
    if n_real_en:
        stats["pct_sentences_matched_en"] = round(100 * len(consumed_en) / n_real_en, 1)
    stats["n_paragraphs_aligned_fr"] = len(aligned_paragraphs_fr)
    stats["n_paragraphs_aligned_en"] = len(aligned_paragraphs_en)
    if paragraphs_fr:
        stats["pct_paragraphs_matched_fr"] = round(100 * len(aligned_paragraphs_fr) / len(paragraphs_fr), 1)
    if paragraphs_en:
        stats["pct_paragraphs_matched_en"] = round(100 * len(aligned_paragraphs_en) / len(paragraphs_en), 1)
    
    if scores:
        stats["similarity_mean"] = round(sum(scores) / len(scores), 3)
        stats["similarity_min"] = round(min(scores), 3)
        stats["similarity_max"] = round(max(scores), 3)
    
    return rows, stats


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
    all_stats = []
    for i, (document_name, info) in enumerate(pairs.items(), 1):
        print(f"  [{i}/{len(pairs)}] {document_name}")
        doc_rows, doc_stats = docx_to_aligned_rows(
            info["fr"], info["en"], document_name, sentence_encoder, device,
            region=info.get("region"), is_erratum=info.get("is_erratum", False),
        )
        rows.extend(doc_rows)
        all_stats.append(doc_stats)
    
    df = pd.DataFrame(rows, columns=["document_name", "fr", "en", "similarity"])
    df.to_pickle(config.WORDDOC_MATCHED_DATA)
    print(f"saved {len(df)} matched rows to {config.WORDDOC_MATCHED_DATA}")
    
    _write_match_log(all_stats)
    
    return df


def _write_match_log(per_doc_stats):
    sorted_stats = sorted(per_doc_stats, key=lambda s: s["pct_sentences_matched_fr"])
    
    total_paragraphs_fr = sum(s["n_paragraphs_fr"] for s in per_doc_stats)
    total_paragraphs_en = sum(s["n_paragraphs_en"] for s in per_doc_stats)
    total_paragraphs_aligned_fr = sum(s["n_paragraphs_aligned_fr"] for s in per_doc_stats)
    total_paragraphs_aligned_en = sum(s["n_paragraphs_aligned_en"] for s in per_doc_stats)
    total_sentences_fr = sum(s["n_sentences_fr"] for s in per_doc_stats)
    total_sentences_en = sum(s["n_sentences_en"] for s in per_doc_stats)
    total_sentences_aligned = sum(s["n_sentences_aligned"] for s in per_doc_stats)
    
    summary = {
        "n_documents": len(per_doc_stats),
        "total_paragraphs_fr": total_paragraphs_fr,
        "total_paragraphs_en": total_paragraphs_en,
        "total_paragraphs_aligned_fr": total_paragraphs_aligned_fr,
        "total_paragraphs_aligned_en": total_paragraphs_aligned_en,
        "overall_pct_paragraphs_matched_fr": round(100 * total_paragraphs_aligned_fr / total_paragraphs_fr, 1) if total_paragraphs_fr else 0.0,
        "overall_pct_paragraphs_matched_en": round(100 * total_paragraphs_aligned_en / total_paragraphs_en, 1) if total_paragraphs_en else 0.0,
        "total_sentences_fr": total_sentences_fr,
        "total_sentences_en": total_sentences_en,
        "total_sentences_aligned": total_sentences_aligned,
        "overall_pct_sentences_matched_fr": round(100 * total_sentences_aligned / total_sentences_fr, 1) if total_sentences_fr else 0.0,
        "overall_pct_sentences_matched_en": round(100 * total_sentences_aligned / total_sentences_en, 1) if total_sentences_en else 0.0,
    }
    
    payload = {"summary": summary, "documents": sorted_stats}
    with open(config.WORDDOC_MATCH_LOG, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"wrote match log to {config.WORDDOC_MATCH_LOG}")


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
    # Core motivator of the project: bureau translations sometimes use non-preferred terminology,
    # so any row whose source-language text contains a glossary term but whose target-language
    # text doesn't contain the preferred translation gets excluded. Current method is whole-word
    # case-insensitive regex on each (src, tgt) pair.
    # FUTURE WORK:
    #  1. Lookup is brittle for inflected forms (e.g. plurals, conjugations). Could move to
    #     lemma- or stem-based matching, or a tokenized full-text-search index, so "stocks" matches
    #     a glossary entry for "stock".
    #  2. Rather than dropping these rows, we could rewrite the wrong term to the preferred one
    #     and re-insert as semi-synthetic training data. Risky (could compound errors if the
    #     surrounding sentence depends on the substituted term), so leaving as a future exploration.
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


@print_timing("add wrong language column")
def add_wrong_language_column(df):
    # Catches rows where one or both sides are not actually in the expected language — typically
    # citations, addresses, author names, journal references, or untranslated proper nouns.
    # These are correctly identical in both columns, but they aren't translations and shouldn't
    # train the model to "translate" them.
    # FUTURE WORK: rather than dropping, could fine-tune the model to leave such content
    # untouched, but that's a separate experiment.
    classifier = LanguageClassifier()
    en_classification = df['en'].apply(classifier.classify)
    fr_classification = df['fr'].apply(classifier.classify)
    df['exclude_wrong_language'] = (en_classification != 'en') | (fr_classification != 'fr')
    return df


@print_timing("exclude rows for training data")
def exclude_for_word_doc_training_data(df):
    # exclude_low_similarity is intentionally omitted here. add_exclusion_columns() applies a
    # 0.85 cutoff calibrated for raw cosine, but match_languages.create_similarity_matrix is now
    # margin-based (sim / (mean_topk_fr + mean_topk_en)) and runs on cleaner DOCX text, so the
    # distribution is compressed (median ~0.74, 95th percentile ~0.86). align_sentences() already
    # floors at 0.7 at the matrix level, which is doing the real work. Revisit if scoring changes.
    other_exclusion_columns = [
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
        'exclude_wrong_language',
    ]
    
    # mark duplicates only within the would-be-kept subset, so we don't drop a clean row
    # because an excluded twin appeared first. (en, fr) pair dedup keeps variants where the
    # same source was translated different ways.
    df['is_duplicate'] = False
    keep_mask = ~df[other_exclusion_columns].any(axis=1)
    candidates = df.loc[keep_mask]
    duplicate_indices = candidates[candidates.duplicated(subset=['en', 'fr'], keep='first')].index
    df.loc[duplicate_indices, 'is_duplicate'] = True
    
    df['exclude'] = df[other_exclusion_columns + ['is_duplicate']].any(axis=1)
    df.to_pickle(config.WORDDOC_FINAL_DATA)
    return df


def create_word_doc_training_data_pipeline():
    df = create_matched_data_docx()
    df = add_features_docx(df)
    df = add_exclusion_columns(df)
    df = add_figref_column(df)
    df = add_too_short_column(df)
    df = add_dates_column(df)
    df = add_lexical_constraint_column(df)
    df = add_number_mismatch_column(df)
    df = add_wrong_language_column(df)
    df = exclude_for_word_doc_training_data(df)
    
    df_for_jsonl = add_periods_to_all_sentences(df[~df['exclude']].copy())
    save_jsonl(df_for_jsonl, config.WORDDOC_TRAINING_DATA)
    
    return df


if __name__ == "__main__":
    create_word_doc_training_data_pipeline()
