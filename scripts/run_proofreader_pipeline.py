import json
import shutil
import subprocess
import sys
from pathlib import Path

from scitrans.config import PROOFREADING_DIR
from scitrans.proofreader.accept_changes import accept_all_changes
from scitrans.proofreader.apply_review import main as apply_review
from scitrans.proofreader.extract_text import extract_text_with_ids
from scitrans.proofreader.fix_formatting import fix_formatting
from scitrans.proofreader.glossary import detect_language_from_path
from scitrans.proofreader.lexical_checklist import (
    lexical_constraint_checklist, save_checklist,
)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / 'src' / 'scitrans' / 'proofreader' / 'prompts'

# Known step suffixes — used for checkpoint filename replacement
STEP_SUFFIXES = [
    '_fix_formatting',
    '_proofreading',
    '_lexical_constraints',
    '_recommended_updates',
]


def _make_checkpoint_path(translated_path, step_suffix):
    stem = translated_path.stem
    # Strip any existing step suffix
    for suffix in STEP_SUFFIXES:
        if stem.endswith(suffix):
            stem = stem[:-len(suffix)]
            break
    return translated_path.parent / f'{stem}{step_suffix}.docx'


def _load_prompt(name):
    path = PROMPTS_DIR / name
    return path.read_text(encoding='utf-8')


def _save_prompt_file(prompt_text, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(prompt_text)
    # Copy to clipboard
    subprocess.run('clip', input=prompt_text.encode('utf-8'), check=False)
    print(f'  Prompt saved to: {output_path}')
    print(f'  Prompt copied to clipboard.')


def _load_response_json(response_path):
    with open(response_path, 'r', encoding='utf-8') as f:
        text = f.read().strip()
    # Strip markdown code fences if present
    if text.startswith('```'):
        first_newline = text.index('\n')
        text = text[first_newline + 1:]
    if text.endswith('```'):
        text = text[:-3]
    text = text.strip()
    return json.loads(text)


def _apply_errors_to_doc(errors, input_path, output_path):
    if not errors:
        shutil.copy2(input_path, output_path)
        print(f'  No errors found, copied as-is.')
        return 0
    
    # Save errors to a JSON file for apply_review
    review_path = output_path.with_suffix('.json')
    with open(review_path, 'w', encoding='utf-8') as f:
        json.dump(errors, f, ensure_ascii=False, indent=2)
    
    apply_review(input_path, review_path, output_path)
    return len(errors)


def _get_base_stem(translated_path):
    stem = translated_path.stem
    for suffix in STEP_SUFFIXES:
        if stem.endswith(suffix):
            stem = stem[:-len(suffix)]
            break
    return stem


# ── Step 1: Lexical constraint checklist ─────────────────────────────────

def step1_lexical_checklist(original_path, source_lang=None):
    print('\n=== Step 1: Building lexical constraint checklist ===')
    checklist = lexical_constraint_checklist(original_path, source_lang=source_lang)
    checklist_path = original_path.with_name(
        original_path.stem + '_lexical_checklist.json'
    )
    save_checklist(checklist, checklist_path)
    print(f'  Found {len(checklist)} glossary term occurrences across the original document.')
    print(f'  Saved to: {checklist_path}')
    return checklist, checklist_path


# ── Step 2: Fix formatting with glossary ─────────────────────────────────

def step2_fix_formatting(translated_path, original_path, source_lang=None):
    print('\n=== Step 2: Fix formatting (with glossary replacements) ===')
    output_path = _make_checkpoint_path(translated_path, '_fix_formatting')
    
    result = fix_formatting(
        translated_path, output_path,
        source_lang=source_lang,
        source_path=original_path,
        use_glossary=True,
        track_changes=True,
    )
    print(f'  {result["glossary_replacements"]} glossary replacements, '
          f'{result["punctuation_fixes"]} punctuation fixes ({result["lang"]} rules)')
    print(f'  Saved to: {output_path}')
    return output_path


# ── Step 3: Proofread — prepare prompt or apply response ─────────────────

def step3_prepare(prev_checkpoint, original_path):
    print('\n=== Step 3: Preparing proofreading prompt ===')
    output_path = _make_checkpoint_path(prev_checkpoint, '_proofreading')
    
    # Accept previous track changes into a clean temp file
    clean_path = output_path.with_name('_step3_clean.docx')
    changes = accept_all_changes(prev_checkpoint, clean_path)
    print(f'  Accepted {sum(changes.values())} previous track changes.')
    
    # Extract text from both documents
    original_text = extract_text_with_ids(original_path)
    translated_text = extract_text_with_ids(clean_path)
    
    system_prompt = _load_prompt('proofreading.md')
    full_prompt = (
        f'{system_prompt}\n\n---\n\n'
        f'## Original document\n\n{original_text}\n\n'
        f'## Translated document\n\n{translated_text}'
    )
    
    prompt_path = output_path.with_name('_step3_prompt.md')
    _save_prompt_file(full_prompt, prompt_path)
    response_path = output_path.with_name('_step3_response.json')
    print(f'\n  >> Paste this prompt into Claude, then save the JSON response to:')
    print(f'     {response_path}')
    print(f'  >> Then re-run with: --step 3')
    return clean_path, output_path, response_path


def step3_apply(prev_checkpoint, original_path):
    print('\n=== Step 3: Applying proofreading response ===')
    output_path = _make_checkpoint_path(prev_checkpoint, '_proofreading')
    clean_path = output_path.with_name('_step3_clean.docx')
    response_path = output_path.with_name('_step3_response.json')
    
    if not response_path.exists():
        print(f'  Error: Response file not found: {response_path}')
        print(f'  Run with --step 3-prepare first, then paste the LLM response.')
        sys.exit(1)
    
    errors = _load_response_json(response_path)
    print(f'  Loaded {len(errors)} errors from response.')
    
    if not clean_path.exists():
        # Re-create clean file if missing
        changes = accept_all_changes(prev_checkpoint, clean_path)
        print(f'  Re-accepted {sum(changes.values())} previous track changes.')
    
    _apply_errors_to_doc(errors, clean_path, output_path)
    clean_path.unlink(missing_ok=True)
    print(f'  Saved to: {output_path}')
    return output_path


# ── Step 4: Lexical constraints — prepare prompt or apply response ───────

def step4_prepare(prev_checkpoint, checklist):
    print('\n=== Step 4: Preparing lexical constraint prompt ===')
    output_path = _make_checkpoint_path(prev_checkpoint, '_lexical_constraints')
    
    clean_path = output_path.with_name('_step4_clean.docx')
    changes = accept_all_changes(prev_checkpoint, clean_path)
    print(f'  Accepted {sum(changes.values())} previous track changes.')
    
    translated_text = extract_text_with_ids(clean_path)
    
    system_prompt = _load_prompt('lexical_constraints.md')
    checklist_json = json.dumps(checklist, ensure_ascii=False, indent=2)
    full_prompt = (
        f'{system_prompt}\n\n---\n\n'
        f'## Translated document\n\n{translated_text}\n\n'
        f'## Lexical constraint checklist\n\n```json\n{checklist_json}\n```'
    )
    
    prompt_path = output_path.with_name('_step4_prompt.md')
    _save_prompt_file(full_prompt, prompt_path)
    response_path = output_path.with_name('_step4_response.json')
    print(f'\n  >> Paste this prompt into Claude, then save the JSON response to:')
    print(f'     {response_path}')
    print(f'  >> Then re-run with: --step 4')
    return clean_path, output_path, response_path


def step4_apply(prev_checkpoint, checklist):
    print('\n=== Step 4: Applying lexical constraint response ===')
    output_path = _make_checkpoint_path(prev_checkpoint, '_lexical_constraints')
    clean_path = output_path.with_name('_step4_clean.docx')
    response_path = output_path.with_name('_step4_response.json')
    
    if not response_path.exists():
        print(f'  Error: Response file not found: {response_path}')
        print(f'  Run with --step 4-prepare first, then paste the LLM response.')
        sys.exit(1)
    
    errors = _load_response_json(response_path)
    print(f'  Loaded {len(errors)} terminology corrections from response.')
    
    if not clean_path.exists():
        changes = accept_all_changes(prev_checkpoint, clean_path)
        print(f'  Re-accepted {sum(changes.values())} previous track changes.')
    
    _apply_errors_to_doc(errors, clean_path, output_path)
    clean_path.unlink(missing_ok=True)
    print(f'  Saved to: {output_path}')
    return output_path


# ── Step 5: Final pass — prepare prompt or apply response ────────────────

def step5_prepare(prev_checkpoint):
    print('\n=== Step 5: Preparing final pass ===')
    output_path = _make_checkpoint_path(prev_checkpoint, '_recommended_updates')
    
    clean_path = output_path.with_name('_step5_clean.docx')
    changes = accept_all_changes(prev_checkpoint, clean_path)
    print(f'  Accepted {sum(changes.values())} previous track changes.')
    
    # Run fix_formatting WITHOUT glossary (punctuation only), with track changes
    fmt_path = output_path.with_name('_step5_fmt.docx')
    result = fix_formatting(
        clean_path, fmt_path,
        use_glossary=False,
        track_changes=True,
    )
    print(f'  {result["punctuation_fixes"]} punctuation fixes ({result["lang"]} rules)')
    
    # Accept formatting changes so the LLM sees clean text for grammar review
    grammar_input = output_path.with_name('_step5_grammar_input.docx')
    accept_all_changes(fmt_path, grammar_input)
    
    translated_text = extract_text_with_ids(grammar_input)
    
    system_prompt = _load_prompt('grammar_review.md')
    full_prompt = f'{system_prompt}\n\n---\n\n## Translated document\n\n{translated_text}'
    
    prompt_path = output_path.with_name('_step5_prompt.md')
    _save_prompt_file(full_prompt, prompt_path)
    response_path = output_path.with_name('_step5_response.json')
    grammar_input.unlink(missing_ok=True)
    print(f'\n  >> Paste this prompt into Claude, then save the JSON response to:')
    print(f'     {response_path}')
    print(f'  >> Then re-run with: --step 5')
    return clean_path, fmt_path, output_path, response_path


def step5_apply(prev_checkpoint):
    print('\n=== Step 5: Applying final pass response ===')
    output_path = _make_checkpoint_path(prev_checkpoint, '_recommended_updates')
    fmt_path = output_path.with_name('_step5_fmt.docx')
    clean_path = output_path.with_name('_step5_clean.docx')
    response_path = output_path.with_name('_step5_response.json')
    
    if not response_path.exists():
        print(f'  Error: Response file not found: {response_path}')
        print(f'  Run with --step 5-prepare first, then paste the LLM response.')
        sys.exit(1)
    
    # If fmt_path is missing, we need to redo the formatting step
    if not fmt_path.exists():
        if not clean_path.exists():
            changes = accept_all_changes(prev_checkpoint, clean_path)
            print(f'  Re-accepted {sum(changes.values())} previous track changes.')
        result = fix_formatting(
            clean_path, fmt_path,
            use_glossary=False,
            track_changes=True,
        )
        print(f'  {result["punctuation_fixes"]} punctuation fixes ({result["lang"]} rules)')
    
    errors = _load_response_json(response_path)
    print(f'  Loaded {len(errors)} grammar corrections from response.')
    
    # Apply grammar fixes on top of the formatting tracked changes
    _apply_errors_to_doc(errors, fmt_path, output_path)
    
    clean_path.unlink(missing_ok=True)
    fmt_path.unlink(missing_ok=True)
    print(f'  Saved to: {output_path}')
    return output_path


# ── Pipeline orchestrator ────────────────────────────────────────────────

def _resolve_paths(original_filename, review_dir, source_lang):
    if review_dir is None:
        review_dir = PROOFREADING_DIR
    review_dir = Path(review_dir)
    
    original_path = review_dir / original_filename
    if not original_path.exists():
        print(f'Error: Original file not found: {original_path}')
        sys.exit(1)
    
    translated_name = original_filename.replace('.docx', '_translated.docx')
    translated_path = review_dir / translated_name
    if not translated_path.exists():
        print(f'Error: Translated file not found: {translated_path}')
        sys.exit(1)
    
    if source_lang is None:
        source_lang = detect_language_from_path(original_path)
        if not source_lang:
            print('Error: Could not detect source language. Use --source-lang en or --source-lang fr.')
            sys.exit(1)
    
    return original_path, translated_path, source_lang


def run_pipeline(original_filename, review_dir=None, source_lang=None, step=None):
    original_path, translated_path, source_lang = _resolve_paths(
        original_filename, review_dir, source_lang)
    
    print(f'Pipeline for: {original_filename}')
    print(f'  Original:   {original_path}')
    print(f'  Translated: {translated_path}')
    print(f'  Source language: {source_lang}')
    
    # Determine checkpoint paths for resuming
    fix_fmt_path = _make_checkpoint_path(translated_path, '_fix_formatting')
    proofread_path = _make_checkpoint_path(translated_path, '_proofreading')
    lexical_path = _make_checkpoint_path(translated_path, '_lexical_constraints')
    
    # Load or build checklist
    checklist_path = original_path.with_name(original_path.stem + '_lexical_checklist.json')
    
    # ── Run all deterministic steps (1-2) if no specific step requested ──
    if step is None or step == '1':
        checklist, checklist_path = step1_lexical_checklist(original_path, source_lang=source_lang)
    
    if step is None or step == '2':
        step2_fix_formatting(translated_path, original_path, source_lang=source_lang)
    
    if step is None or step == '2':
        # After step 2, prepare step 3 prompt
        step3_prepare(fix_fmt_path, original_path)
        if step is None:
            print('\n--- Pipeline paused. Complete the LLM step above, then re-run with --step 3 ---')
        return
    
    # ── Step 3: apply response, then prepare step 4 ──
    if step == '3':
        step3_apply(fix_fmt_path, original_path)
        # Load checklist for step 4
        if checklist_path.exists():
            with open(checklist_path, 'r', encoding='utf-8') as f:
                checklist = json.load(f)
        else:
            checklist, _ = step1_lexical_checklist(original_path, source_lang=source_lang)
        step4_prepare(proofread_path, checklist)
        print('\n--- Complete the LLM step above, then re-run with --step 4 ---')
        return
    
    # ── Step 4: apply response, then prepare step 5 ──
    if step == '4':
        if checklist_path.exists():
            with open(checklist_path, 'r', encoding='utf-8') as f:
                checklist = json.load(f)
        else:
            checklist, _ = step1_lexical_checklist(original_path, source_lang=source_lang)
        step4_apply(proofread_path, checklist)
        step5_prepare(lexical_path)
        print('\n--- Complete the LLM step above, then re-run with --step 5 ---')
        return
    
    # ── Step 5: apply response ──
    if step == '5':
        final_path = step5_apply(lexical_path)
        print(f'\n=== Pipeline complete ===')
        print(f'  Final output: {final_path}')
        return final_path


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Run the proofreader pipeline',
        epilog=(
            'Workflow:\n'
            '  1. Run without --step to execute steps 1-2 and generate the step 3 prompt.\n'
            '  2. Paste the prompt into Claude, save the JSON response.\n'
            '  3. Run with --step 3 to apply and generate the step 4 prompt.\n'
            '  4. Repeat for --step 4 and --step 5.\n'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('filename', help='Original document filename (e.g. 1432_en.docx)')
    parser.add_argument('--review-dir', default=None, help=f'Review directory (default: {PROOFREADING_DIR})')
    parser.add_argument('--source-lang', choices=['en', 'fr'], default=None,
                        help='Source document language (auto-detected if omitted)')
    parser.add_argument('--step', choices=['1', '2', '3', '4', '5'], default=None,
                        help='Run a specific step (default: run steps 1-2 then pause)')
    args = parser.parse_args()
    
    run_pipeline(args.filename, review_dir=args.review_dir,
                 source_lang=args.source_lang, step=args.step)
