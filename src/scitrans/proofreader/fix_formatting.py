import argparse
import re
import sys

from pathlib import Path

import docx

from scitrans.config import PREFERENTIAL_JSON_PATH
from scitrans.proofreader.glossary import (
    load_glossary, extract_text, build_sub_glossary, detect_language,
    detect_language_from_path,
)

W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
W = f'{{{W_NS}}}'
XML_SPACE = '{http://www.w3.org/XML/1998/namespace}space'
NBSP = '\u00a0'

# ── Language-specific punctuation spacing rules ──────────────────────────
#
# Each rule is (compiled_regex, replacement_string).
# Applied in order to every <w:t> text node in the document.
#
# French: non-breaking space before : ; ? ! and before %
#         space inside guillemets: « text » (with NBSP)
#
# English: no space before : ; ? ! %
#          straight quotes, no inner spacing

FRENCH_RULES = [
    # Space before colon — but skip URLs (://), time patterns (10:30),
    # and already-correct NBSP
    (re.compile(r'(?<![:/\d\u00a0]) ?(:)(?!/)'), NBSP + r'\1'),
    # Space before semicolon
    (re.compile(r'(?<!\u00a0) ?(;)'), NBSP + r'\1'),
    # Space before question mark
    (re.compile(r'(?<!\u00a0) ?(\?)'), NBSP + r'\1'),
    # Space before exclamation mark
    (re.compile(r'(?<!\u00a0) ?(!)'), NBSP + r'\1'),
    # Space before percent sign (digit%)  →  digit NBSP %
    (re.compile(r'(\d) ?(%)', re.UNICODE), r'\1' + NBSP + r'\2'),
    # Guillemets: ensure NBSP inside
    (re.compile(r'«\s*'), '«' + NBSP),
    (re.compile(r'\s*»'), NBSP + '»'),
]

ENGLISH_RULES = [
    # Remove space before colon (but not double-space scenarios)
    (re.compile(r' +(:)'), r'\1'),
    # Remove space before semicolon
    (re.compile(r' +(;)'), r'\1'),
    # Remove space before question mark
    (re.compile(r' +(\?)'), r'\1'),
    # Remove space before exclamation mark
    (re.compile(r' +(!)'), r'\1'),
    # Remove space before percent
    (re.compile(r'(\d) +(%)', re.UNICODE), r'\1\2'),
]

RULES_BY_LANG = {
    'fr': FRENCH_RULES,
    'en': ENGLISH_RULES,
}


def is_in_deletion(node):
    while node is not None:
        if node.tag == f'{W}del':
            return True
        node = node.getparent()
    return False


def iter_text_elements(doc):
    for t_elem in doc.element.body.iter(f'{W}t'):
        if is_in_deletion(t_elem.getparent()):
            continue
        if not (t_elem.text or ''):
            continue
        yield t_elem


def apply_rules(text, rules):
    result = text
    for pattern, replacement in rules:
        result = pattern.sub(replacement, result)
    return result


def apply_punctuation_rules(doc, rules):
    count = 0
    for t_elem in iter_text_elements(doc):
        old = t_elem.text
        new = apply_rules(old, rules)
        if new != old:
            t_elem.text = new
            t_elem.set(XML_SPACE, 'preserve')
            count += 1
    return count


def apply_glossary_replacements(doc, sub_glossary):
    # Sort by key length descending so longer matches take priority
    # (e.g. "Shrimp Fishing Area" before "Shrimp")
    sorted_terms = sorted(sub_glossary.items(), key=lambda x: len(x[0]), reverse=True)
    
    # Pre-compile patterns: whole-word, case-sensitive
    compiled = []
    for source_term, target_term in sorted_terms:
        pattern = re.compile(rf'\b{re.escape(source_term)}\b')
        compiled.append((pattern, target_term))
    
    count = 0
    for t_elem in iter_text_elements(doc):
        old = t_elem.text
        new = old
        for pattern, target_term in compiled:
            new = pattern.sub(target_term, new)
        if new != old:
            t_elem.text = new
            t_elem.set(XML_SPACE, 'preserve')
            count += 1
    return count


MIN_TERM_LENGTH = 3


def fix_formatting(input_path, output_path, lang=None, source_lang=None,
                   source_path=None, glossary_path=None, use_glossary=True):
    doc = docx.Document(input_path)
    
    if not lang:
        lang = detect_language(doc)
        if not lang:
            raise ValueError('Could not detect language from document. Pass lang="fr" or lang="en".')
    
    rules = RULES_BY_LANG[lang]
    
    # Build sub-glossary if glossary and source provided.
    # Only acronyms, taxon, and table entries are safe for mechanical
    # replacement. Generic nomenclature terms (stock, catch, data)
    # need context that only the LLM review can provide.
    # Short table entries (<=2 chars) like "NO", "AI" are skipped
    # to avoid false positives.
    sub_glossary = {}
    if use_glossary and source_path:
        if source_lang is None:
            source_lang = detect_language_from_path(source_path)
            if not source_lang:
                raise ValueError('Could not detect source language. Pass source_lang="en" or "fr".')
        if glossary_path is None:
            glossary_path = PREFERENTIAL_JSON_PATH
        glossary = load_glossary(glossary_path, categories=["acronym", "taxon", "table"],
                                 source_lang=source_lang)
        source_text = extract_text(source_path)
        sub_glossary = build_sub_glossary(source_text, glossary)
        sub_glossary = {k: v for k, v in sub_glossary.items() if len(k) >= MIN_TERM_LENGTH}
    
    # Apply glossary replacements first, then punctuation rules
    glossary_count = 0
    if sub_glossary:
        glossary_count = apply_glossary_replacements(doc, sub_glossary)
    
    punctuation_count = apply_punctuation_rules(doc, rules)
    
    doc.save(output_path)
    return {
        "lang": lang,
        "glossary_replacements": glossary_count,
        "glossary_terms_matched": len(sub_glossary),
        "punctuation_fixes": punctuation_count,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='Input .docx file')
    parser.add_argument('output', help='Output .docx file')
    parser.add_argument('--lang', choices=['fr', 'en'],
                        help='Target language (auto-detected if omitted)')
    parser.add_argument('--source-lang', choices=['en', 'fr'], default=None,
                        help='Source document language (auto-detected if omitted)')
    parser.add_argument('--glossary', help='Path to preferential_translations.json')
    parser.add_argument('--source', help='Path to original source .docx (required with --glossary)')
    args = parser.parse_args()
    
    if args.glossary and not args.source:
        print('--source is required when using --glossary.')
        sys.exit(1)
    
    result = fix_formatting(
        args.input, args.output,
        lang=args.lang,
        source_lang=args.source_lang,
        source_path=args.source,
        glossary_path=args.glossary,
    )
    print(f'Done: {result["glossary_replacements"]} glossary replacements, '
          f'{result["punctuation_fixes"]} punctuation fixes ({result["lang"]} rules)')
    print(f'Saved to: {args.output}')
