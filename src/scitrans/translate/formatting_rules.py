import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

BRACKET_PATTERN = re.compile(r'\([^)]+\)')


@dataclass(frozen=True)
class FormattedRun:
    text: str
    italic: bool = False
    superscript: bool = False
    subscript: bool = False

    def __str__(self):
        s = self.text
        if self.italic:
            s = f"/{s}/"
        if self.superscript:
            s = f"^{{{s}}}"
        if self.subscript:
            s = f"_{{{s}}}"
        return s


def rule_italic_brackets(paragraph_text, runs):
    italic_texts = [run.text for run in runs if run.italic and run.text.strip()]
    if not italic_texts:
        return None

    for match in BRACKET_PATTERN.finditer(paragraph_text):
        bracketed_content = match.group()[1:-1]
        has_italic_inside = any(
            italic_text in bracketed_content for italic_text in italic_texts
        )
        if not has_italic_inside:
            continue

        start, end = match.start(), match.end()
        before = paragraph_text[:start]
        after = paragraph_text[end:]

        formatted_runs = [
            FormattedRun(text=before),
            FormattedRun(text="("),
            FormattedRun(text=bracketed_content, italic=True),
            FormattedRun(text=")"),
            FormattedRun(text=after),
        ]
        return [run for run in formatted_runs if run.text]

    return None


FORMATTING_RULES = [rule_italic_brackets]


def apply_formatting_rules(paragraph_text, translated_text, runs):
    for rule in FORMATTING_RULES:
        try:
            result = rule(translated_text, runs)
        except Exception:
            logger.warning("Formatting rule %s failed", rule.__name__, exc_info=True)
            continue
        if result is not None:
            return True, result
    return False, None
