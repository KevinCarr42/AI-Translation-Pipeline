import json
import re

from scitrans.config import PREFERENTIAL_JSON_PATH
from scitrans.proofreader.extract_text import extract_locations
from scitrans.proofreader.glossary import load_glossary, detect_language_from_path


def lexical_constraint_checklist(original_path, source_lang=None, glossary_path=None):
    if glossary_path is None:
        glossary_path = PREFERENTIAL_JSON_PATH
    
    if source_lang is None:
        source_lang = detect_language_from_path(original_path)
        if not source_lang:
            raise ValueError('Could not detect source language. Pass source_lang="en" or "fr".')
    
    glossary = load_glossary(glossary_path, source_lang=source_lang)
    locations = extract_locations(original_path)
    
    # Pre-compile patterns for each glossary term (whole-word, case-insensitive)
    compiled_terms = []
    for source_term, target_term in glossary.items():
        if len(source_term) < 2:
            continue
        pattern = re.compile(rf'\b{re.escape(source_term)}\b', re.IGNORECASE)
        compiled_terms.append((pattern, source_term, target_term))
    
    checklist = []
    for loc_id, text in locations:
        for pattern, source_term, target_term in compiled_terms:
            if pattern.search(text):
                checklist.append({
                    "location": loc_id,
                    "source_text": source_term,
                    "preferred_translation": target_term,
                })
    
    return checklist


def save_checklist(checklist, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(checklist, f, ensure_ascii=False, indent=2)
    return output_path
