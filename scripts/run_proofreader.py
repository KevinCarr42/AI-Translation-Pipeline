import subprocess
from pathlib import Path

from scitrans.config import PROJECT_ROOT
from scitrans.proofreader.apply_review import main as apply_review
from scitrans.proofreader.build_prompt import build_prompt
from scitrans.proofreader.fix_formatting import fix_formatting


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


if __name__ == '__main__':
    # run_build_prompt("1432_en.docx", review_path=Path("EXAMPLES"))
    
    folder_path = Path("EXAMPLES")
    input_path = folder_path / "1432_en_translated.docx"
    output_path = folder_path / "1432_en_translated_FIXED.docx"
    source_path = folder_path / "1432_en.docx"

    run_fix_formatting(
        input_path=input_path,
        output_path=output_path,
        source_path=source_path,
        track_changes=False,
    )
