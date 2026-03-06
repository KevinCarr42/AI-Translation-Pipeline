import logging
import re
from dataclasses import dataclass
from typing import ClassVar

from docx.enum.text import WD_COLOR_INDEX

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
    

def detect_patterns(paragraph):
    BRACKET_PATTERN = re.compile(r'\([^)]+\)')

    italic_brackets = {"apply": False, "expected_count": 0, "ambiguous_notes": None}
    italic_texts = [run.text for run in paragraph.runs if run.italic and run.text.strip()]
    if italic_texts:
        full_text = paragraph.text
        bracket_matches = list(BRACKET_PATTERN.finditer(full_text))
        all_italic_count = 0
        any_partial = False

        for match in bracket_matches:
            content = match.group()[1:-1]
            # Check if any italic text overlaps this bracket content
            overlap = any(it in content for it in italic_texts)
            if not overlap:
                continue
            # Check if the entire bracket content is covered by italic text
            remaining = content
            for it in italic_texts:
                remaining = remaining.replace(it, "")
            entirely_italic = remaining.strip() == ""

            if entirely_italic:
                all_italic_count += 1
            else:
                any_partial = True

        if any_partial:
            italic_brackets["ambiguous_notes"] = (
                "Italic bracket formatting could not be automatically applied "
                "— partial italic detected in bracketed text"
            )
        elif all_italic_count > 0:
            italic_brackets["apply"] = True
            italic_brackets["expected_count"] = all_italic_count

    return {"italic_brackets": italic_brackets}


def apply_formatting_rules(paragraph, detected_patterns, formatting_records):
    ib = detected_patterns["italic_brackets"]

    if ib["ambiguous_notes"]:
        formatting_records.append({
            'original_text': paragraph.text,
            'full_sentence': paragraph.text,
            'notes': ib["ambiguous_notes"],
        })

    if ib["apply"]:
        text = paragraph.text
        matches = list(BRACKET_PATTERN.finditer(text))
        if len(matches) == ib["expected_count"]:
            parts = []
            last_end = 0
            for match in matches:
                before = text[last_end:match.start()]
                if before:
                    parts.append(FormattedRun(text=before))
                content = match.group()[1:-1]
                parts.append(FormattedRun(text="("))
                parts.append(FormattedRun(text=content, italic=True))
                parts.append(FormattedRun(text=")"))
                last_end = match.end()
            remainder = text[last_end:]
            if remainder:
                parts.append(FormattedRun(text=remainder))

            paragraph.clear()
            for part in parts:
                run = paragraph.add_run(part.text)
                if part.italic:
                    run.italic = True
        else:
            formatting_records.append({
                'original_text': paragraph.text,
                'full_sentence': paragraph.text,
                'notes': (
                    "Italic bracket formatting could not be automatically applied "
                    "— bracket count mismatch after translation"
                ),
            })

    if detected_patterns["has_hyperlinks"]:
        for run in list(paragraph.runs):
            if run.text and run.text.strip():
                run.font.highlight_color = WD_COLOR_INDEX.TURQUOISE


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
