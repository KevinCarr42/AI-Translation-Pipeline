import subprocess
from pathlib import Path

from scitrans.config import PROJECT_ROOT, PROOFREADING_DIR
from scitrans.proofreader.apply_review import main as apply_review
from scitrans.proofreader.build_prompt import build_prompt
from scitrans.proofreader.fix_formatting import fix_formatting

from run_proofreader_pipeline import (
    _resolve_paths, _make_checkpoint_path,
    step1_lexical_checklist, step2_fix_formatting,
    step3_prepare, step3_apply,
    step4_prepare, step4_apply,
    step5_prepare, step5_apply,
)


def _resolve(path):
    path = Path(path)
    if path.is_absolute():
        return path
    return (PROJECT_ROOT / path).resolve()


def run_fix_formatting(input_path, output_path, source_path=None,
                       lang=None, source_lang=None, track_changes=False):
    input_path = _resolve(input_path)
    output_path = _resolve(output_path)
    if source_path is not None:
        source_path = _resolve(source_path)
    
    result = fix_formatting(
        input_path, output_path,
        lang=lang,
        source_lang=source_lang,
        source_path=source_path,
        track_changes=track_changes,
    )
    print(f'Done: {result["glossary_replacements"]} glossary replacements, '
          f'{result["punctuation_fixes"]} punctuation fixes ({result["lang"]} rules)')
    print(f'Saved to: {output_path}')
    return result


def run_apply_review(translated_path, review_path, output_path):
    translated_path = _resolve(translated_path)
    review_path = _resolve(review_path)
    output_path = _resolve(output_path)
    
    apply_review(translated_path, review_path, output_path)


def run_build_prompt(filename, review_path=None, source_lang=None, copy_to_clipboard=False):
    if review_path is not None:
        review_path = _resolve(review_path)
    prompt_text = build_prompt(filename, review_path, source_lang=source_lang)
    print(prompt_text)
    if copy_to_clipboard:
        subprocess.run("clip", input=prompt_text.encode('utf-8'), check=True)
    return prompt_text


def _wait_for_response(response_path):
    input('\n  Press Enter when the response file is saved...')
    while not response_path.exists():
        input(f'  Response file not found: {response_path}\n  Save the file and press Enter to retry...')


def run_pipeline(original_filename, review_dir=None, source_lang=None):
    original_path, translated_path, source_lang = _resolve_paths(
        original_filename, review_dir, source_lang)
    
    print(f'Pipeline for: {original_filename}')
    print(f'  Original:   {original_path}')
    print(f'  Translated: {translated_path}')
    print(f'  Source language: {source_lang}')
    
    fix_fmt_path = _make_checkpoint_path(translated_path, '_fix_formatting')
    proofread_path = _make_checkpoint_path(translated_path, '_proofreading')
    lexical_path = _make_checkpoint_path(translated_path, '_lexical_constraints')
    checklist_path = original_path.with_name(original_path.stem + '_lexical_checklist.json')
    
    # ── Steps 1-2: deterministic ──
    checklist, checklist_path = step1_lexical_checklist(original_path, source_lang=source_lang)
    step2_fix_formatting(translated_path, original_path, source_lang=source_lang)
    
    # ── Step 3: proofread ──
    clean_path, output_path, response_path = step3_prepare(fix_fmt_path, original_path)
    _wait_for_response(response_path)
    step3_apply(fix_fmt_path, original_path)
    
    # ── Step 4: lexical constraints ──
    clean_path, output_path, response_path = step4_prepare(proofread_path, checklist)
    _wait_for_response(response_path)
    step4_apply(proofread_path, checklist)
    
    # ── Step 5: final pass ──
    clean_path, fmt_path, output_path, response_path = step5_prepare(lexical_path)
    _wait_for_response(response_path)
    final_path = step5_apply(lexical_path)
    
    print(f'\n=== Pipeline complete ===')
    print(f'  Final output: {final_path}')


if __name__ == "__main__":
    run_pipeline("1432_en.docx")
