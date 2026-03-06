import logging
import re
from dataclasses import dataclass
from typing import ClassVar

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FormattedRun:
    _DEFAULT_COLOUR: ClassVar[str] = "default"
    _FORMATTING_BOOLS: ClassVar[tuple[str, ...]] = ('bold', 'italic', 'underline', 'superscript', 'subscript')
    text: str
    bold: bool = False
    italic: bool = False
    underline: bool = False
    superscript: bool = False
    subscript: bool = False
    colour: str = _DEFAULT_COLOUR
    
    @classmethod
    def create(cls, run):
        colour = "default"
        if run.font.color and run.font.color.rgb:
            colour = str(run.font.color.rgb)
        return cls(
            text=run.text,
            bold=run.bold,
            italic=run.italic,
            underline=run.underline,
            superscript=run.font.superscript or False,
            subscript=run.font.subscript or False,
            colour=colour,
        )
    
    @property
    def has_formatting(self):
        return any(getattr(self, attr) for attr in self._FORMATTING_BOOLS) or self.colour != self._DEFAULT_COLOUR
    
    @property
    def formatting_notes(self):
        notes = []
        for attr in self._FORMATTING_BOOLS:
            if getattr(self, attr):
                notes.append(attr)
        if self.colour != self._DEFAULT_COLOUR:
            notes.append(f'colour={self.colour}')
        
        if notes:
            return ", ".join(notes)
        return "no formatting"


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
    

BRACKET_PATTERN = re.compile(r'\([^)]+\)')
PATTERNS_TO_FORMAT = {
    'italic': [BRACKET_PATTERN],
    'bold': [],
    'underline': [],
}


def detect_patterns():
    for pattern in PATTERNS_TO_DETECT:
        pass


def apply_formatting_rules(paragraph, detected_patterns):
    # TODO: split by pattern(s)
    
    # TODO: apply appropriate formatting
    for pattern in patterns:
        _apply_cyan = has_hyperlinks(paragraph, formatting_records)
        # do formatting
        
        
# TODO: delete this once refactor is complete
def old_formatting_stuff_removed():
    for run in all_runs:
        run.text = ''
    for i, fmt_run in enumerate(formatted_runs):
        if i < len(content_runs):
            content_runs[i].text = fmt_run.text
            content_runs[i].italic = fmt_run.italic
            if fmt_run.superscript:
                content_runs[i].font.superscript = True
            if fmt_run.subscript:
                content_runs[i].font.subscript = True
        else:
            # More formatted runs than content runs — append to last run
            content_runs[-1].text += fmt_run.text

    if _apply_cyan:
        for run in list(paragraph.runs):
            if hasattr(run, 'font') and hasattr(run.font, 'highlight_color'):
                run.font.highlight_color = WD_COLOR_INDEX.TURQUOISE
         

# def rule_italic_brackets(paragraph_text, runs):
#     italic_texts = [run.text for run in runs if run.italic and run.text.strip()]
#     if not italic_texts:
#         return None
#
#     for match in BRACKET_PATTERN.finditer(paragraph_text):
#         bracketed_content = match.group()[1:-1]
#         has_italic_inside = any(
#             italic_text in bracketed_content for italic_text in italic_texts
#         )
#         if not has_italic_inside:
#             continue
#
#         start, end = match.start(), match.end()
#         before = paragraph_text[:start]
#         after = paragraph_text[end:]
#
#         formatted_runs = [
#             FormattedRun(text=before),
#             FormattedRun(text="("),
#             FormattedRun(text=bracketed_content, italic=True),
#             FormattedRun(text=")"),
#             FormattedRun(text=after),
#         ]
#         return [run for run in formatted_runs if run.text]
#
#     return None
#
#
# FORMATTING_RULES = [rule_italic_brackets]
#
#
# def apply_formatting_rules(paragraph_text, translated_text, runs):
#     for rule in FORMATTING_RULES:
#         result = rule(translated_text, runs)
#         # NOTE: only returns the first rule. refactor to include all rules?
#         if result is not None:
#             return True, result
#     return False, [FormattedRun(translated_text)]


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
