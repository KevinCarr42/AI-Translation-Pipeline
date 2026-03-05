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


def parse_formatted_string(s):
    results = []
    i = 0
    while i < len(s):
        char = s[i]
        if char in ('/', '_', '^'):
            marker = char
            i += 1
            is_braced = i < len(s) and s[i] == '{'
            
            if is_braced:
                start = i + 1
                count = 1
                j = start
                while j < len(s) and count > 0:
                    if s[j] == '{':
                        count += 1
                    elif s[j] == '}':
                        count -= 1
                    j += 1
                inner = s[start:j - 1]
                i = j
            else:
                start = i
                while i < len(s) and s[i] not in ('/', '_', '^', ' ', '}', '{'):
                    i += 1
                inner = s[start:i]
                if marker == '/' and i < len(s) and s[i] == '/':
                    i += 1
            
            nested = parse_formatted_string(inner)
            for run in nested:
                results.append(FormattedRun(
                    text=run.text,
                    italic=run.italic or marker == '/',
                    superscript=run.superscript or marker == '^',
                    subscript=run.subscript or marker == '_'
                ))
        else:
            start = i
            while i < len(s) and s[i] not in ('/', '_', '^'):
                i += 1
            results.append(FormattedRun(text=s[start:i]))
    return results


# FIXME: create test once refactored
#  TODO: this is actually bad, we should be
#   checking for the pattern
#   translating as a block
#   creating formatted runs
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
        result = rule(translated_text, runs)
        # NOTE: only returns the first rule. refactor to include all rules?
        if result is not None:
            return True, result
    return False, [FormattedRun(translated_text)]


def _is_single_numeric(text):
    if re.search(r'\d/\d', text):
        return False
    if re.search(r'\d\s*[-\u2013\u2212]\s*\d', text):
        return False
    
    cleaned = text
    cleaned = re.sub(r'[Ee][+\-]', '', cleaned)
    cleaned = re.sub(r'[\s,.\u00a0\u202f\+\-\u2212/%<>()\[\]=#×÷±≤≥*–^°]', '', cleaned)
    
    return cleaned != '' and cleaned.isdigit()


_SEPARATOR_RE = re.compile(r'\s+[-\u2013\u2212]\s+')


def is_numeric(text):
    if not text or not text.strip():
        return False
    
    stripped = text.strip()
    parts = _SEPARATOR_RE.split(stripped)
    return all(_is_single_numeric(p) for p in parts)


def _convert_single_numeric(text, to_fr=True):
    cleaned = re.sub(r'[Ee][+\-]', '', text)
    cleaned = re.sub(r'[\s,.\u00a0\u202f\+\-\u2212/%<>()\[\]=#×÷±≤≥*–^°]', '', cleaned)
    
    sci_match = re.search(r'[Ee][+\-]\d+', text)
    sci_part = sci_match.group(0) if sci_match else ""
    
    if to_fr:
        if "." in text:
            parts = text.split(".")
            int_part = re.sub(r'[^0-9]', '', parts[0])
            dec_part = re.sub(r'[^0-9]', '', parts[1].split('E')[0].split('%')[0])
            res = f"{int(int_part):,}".replace(",", "\u00a0") + f",{dec_part}"
        else:
            res = f"{int(cleaned):,}".replace(",", "\u00a0")
        
        res += sci_part
        return f"{res}\u00a0%" if "%" in text else res
    else:
        if "," in text:
            parts = text.split(",")
            int_part = re.sub(r'[^0-9]', '', parts[0])
            dec_part = re.sub(r'[^0-9]', '', parts[1].split('E')[0].split('%')[0])
            res = f"{int(int_part):,}.{dec_part}"
        else:
            res = f"{int(cleaned):,}"
        
        res += sci_part
        return f"{res}%" if "%" in text else res


def convert_numeric(text, to_fr=True):
    parts = _SEPARATOR_RE.split(text)
    if len(parts) == 1:
        return _convert_single_numeric(text, to_fr)
    converted = [_convert_single_numeric(p.strip(), to_fr) for p in parts]
    return " - ".join(converted)
