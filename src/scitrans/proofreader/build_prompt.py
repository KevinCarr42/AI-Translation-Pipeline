from pathlib import Path

from scitrans.config import PREFERENTIAL_JSON_PATH, PROOFREADING_DIR
from scitrans.proofreader.glossary import (
    load_glossary, extract_text, build_sub_glossary, detect_language_from_path,
)

MIN_LENGTH = 3


def build_prompt(filename, review_path=None, source_lang=None):
    if review_path is None:
        review_path = Path(PROOFREADING_DIR)
    source_path = review_path / filename
    if source_lang is None:
        source_lang = detect_language_from_path(source_path)
        if not source_lang:
            raise ValueError(f'Could not detect source language from {source_path}. Pass source_lang="en" or "fr".')
    translated_filename = filename.replace(".docx", "_translated.docx")
    glossary = load_glossary(PREFERENTIAL_JSON_PATH, source_lang=source_lang)
    source_text = extract_text(review_path / filename)
    sub_glossary = build_sub_glossary(source_text, glossary)
    prompt = (
        f"In {review_path}/, the file {filename} has been translated and is saved "
        f"as {translated_filename}. Please follow instructions.md to review "
        f"the translation.\n"
    )
    if sub_glossary:
        prompt += "\nPreferential terminology (use these as your reference when reviewing):\n"
        for source_term, target_term in sub_glossary.items():
            if len(source_term) >= MIN_LENGTH and len(target_term) >= MIN_LENGTH:
                prompt += f"- {source_term} -> {target_term}\n"
    return prompt
