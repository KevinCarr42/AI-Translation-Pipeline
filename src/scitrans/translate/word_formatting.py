import logging
import re
from copy import deepcopy
from dataclasses import dataclass
from typing import ClassVar

from docx.oxml.ns import qn
from lxml import etree

logger = logging.getLogger(__name__)

BRACKET_PATTERN = re.compile(r'\([^)]+\)')
_SEPARATOR_RE = re.compile(r'\s+[-\u2013\u2212]\s+')
_SPP_PATTERN = re.compile(r'\b(spp?\.)$')
_SENTENCE_BOUNDARY = re.compile(r'(?<=[.!?])\s+')
_FR_ORDINAL_SUFFIXES = re.compile(r'(\d+)(e|er|ère)\b')
_EN_ORDINAL_SUFFIXES = re.compile(r'(\d+)(th|st|nd|rd)\b')


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


def _merge_adjacent_italic_texts(paragraph):
    runs = paragraph.runs
    merged = []
    i = 0
    while i < len(runs):
        if runs[i].italic and runs[i].text.strip():
            combined = runs[i].text
            j = i + 1
            # Absorb whitespace-only runs between italic runs
            while j < len(runs):
                if not runs[j].text.strip() and j + 1 < len(runs) and runs[j + 1].italic and runs[j + 1].text.strip():
                    combined += runs[j].text + runs[j + 1].text
                    j += 2
                else:
                    break
            merged.append(combined)
            i = j
        else:
            i += 1
    return merged


def detect_patterns(paragraph):
    italic_brackets = {"apply": False, "expected_count": 0, "ambiguous_notes": None}
    italic_texts = _merge_adjacent_italic_texts(paragraph)
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
            remaining_stripped = remaining.strip()
            entirely_italic = remaining_stripped == "" or bool(_SPP_PATTERN.search(remaining_stripped))
            
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
    
    # Detect superscript numeric runs
    superscript_numbers = []
    for run in paragraph.runs:
        if run.font.superscript and run.text.strip() and is_numeric(run.text.strip()):
            superscript_numbers.append(run.text.strip())
    
    # Detect subscript ordinal suffixes (th, st, nd, rd)
    _ordinal_suffixes = {'th', 'st', 'nd', 'rd'}
    subscript_ordinals = []
    runs = paragraph.runs
    for i, run in enumerate(runs):
        if run.font.subscript and run.text.strip().lower() in _ordinal_suffixes and i > 0:
            prev_text = runs[i - 1].text.rstrip()
            if prev_text and prev_text[-1].isdigit():
                subscript_ordinals.append(prev_text.split()[-1] + run.text.strip())
    
    superscript_ordinals = []
    for i, run in enumerate(runs):
        if run.font.superscript and run.text.strip().lower() in _ordinal_suffixes and i > 0:
            prev_text = runs[i - 1].text.rstrip()
            if prev_text and prev_text[-1].isdigit():
                superscript_ordinals.append(prev_text.split()[-1] + run.text.strip())
    
    result = {"italic_brackets": italic_brackets}
    if superscript_numbers:
        result["superscript_numbers"] = superscript_numbers
    if subscript_ordinals:
        result["subscript_ordinals"] = subscript_ordinals
    if superscript_ordinals:
        result["superscript_ordinals"] = superscript_ordinals
    return result


# ---------------------------------------------------------------------------
# Italic bracket helpers
# ---------------------------------------------------------------------------

def _build_italic_bracket_parts(content):
    spp_match = _SPP_PATTERN.search(content)
    if spp_match:
        main_content = content[:spp_match.start()].rstrip()
        spp_suffix = spp_match.group(1)
        parts = []
        if main_content:
            parts.append(FormattedRun(text=main_content, italic=True))
            parts.append(FormattedRun(text=" " + spp_suffix))
        else:
            parts.append(FormattedRun(text=spp_suffix))
        return parts
    return [FormattedRun(text=content, italic=True)]


def _build_parts_from_bracket_matches(text, matches):
    parts = []
    last_end = 0
    for match in matches:
        before = text[last_end:match.start()]
        if before:
            parts.append(FormattedRun(text=before))
        content = match.group()[1:-1]
        parts.append(FormattedRun(text="("))
        parts.extend(_build_italic_bracket_parts(content))
        parts.append(FormattedRun(text=")"))
        last_end = match.end()
    remainder = text[last_end:]
    if remainder:
        parts.append(FormattedRun(text=remainder))
    return parts


def _write_formatted_parts_to_paragraph(paragraph, parts):
    paragraph.clear()
    for part in parts:
        run = paragraph.add_run(part.text)
        if part.italic:
            run.italic = True


def _apply_italic_brackets(paragraph, matches, text):
    parts = _build_parts_from_bracket_matches(text, matches)
    _write_formatted_parts_to_paragraph(paragraph, parts)


def _try_italic_brackets_per_sentence(paragraph, total_expected):
    text = paragraph.text
    sentences = _SENTENCE_BOUNDARY.split(text)
    total_found = sum(len(BRACKET_PATTERN.findall(s)) for s in sentences)
    
    if total_found != total_expected:
        return False
    
    parts = []
    for i, sentence in enumerate(sentences):
        if i > 0:
            parts.append(FormattedRun(text=" "))
        matches = list(BRACKET_PATTERN.finditer(sentence))
        if matches:
            parts.extend(_build_parts_from_bracket_matches(sentence, matches))
        else:
            parts.append(FormattedRun(text=sentence))
    
    _write_formatted_parts_to_paragraph(paragraph, parts)
    return True


# ---------------------------------------------------------------------------
# Vertical alignment (superscript / subscript) — unified run splitter
# ---------------------------------------------------------------------------

def _split_run_for_vertical_align(paragraph, run, text_fragment, align_type, offset=None):
    run_elem = run._element
    text = run.text
    idx = offset if offset is not None else text.find(text_fragment)
    if idx == -1:
        return False
    
    before = text[:idx]
    after = text[idx + len(text_fragment):]
    
    if before:
        run.text = before
        new_r = deepcopy(run_elem)
        t_elem = new_r.find(qn('w:t'))
        t_elem.text = text_fragment
        rPr = new_r.find(qn('w:rPr'))
        if rPr is None:
            rPr = etree.SubElement(new_r, qn('w:rPr'))
            new_r.insert(0, rPr)
        vert = rPr.find(qn('w:vertAlign'))
        if vert is None:
            vert = etree.SubElement(rPr, qn('w:vertAlign'))
        vert.set(qn('w:val'), align_type)
        run_elem.addnext(new_r)
        
        if after:
            after_r = deepcopy(run_elem)
            t_elem = after_r.find(qn('w:t'))
            t_elem.text = after
            if after[0] == ' ':
                t_elem.set(qn('xml:space'), 'preserve')
            new_r.addnext(after_r)
    else:
        run.text = text_fragment
        rPr_elem = run_elem.find(qn('w:rPr'))
        if rPr_elem is None:
            rPr_elem = etree.SubElement(run_elem, qn('w:rPr'))
            run_elem.insert(0, rPr_elem)
        vert = rPr_elem.find(qn('w:vertAlign'))
        if vert is None:
            vert = etree.SubElement(rPr_elem, qn('w:vertAlign'))
        vert.set(qn('w:val'), align_type)
        
        if after:
            after_r = deepcopy(run_elem)
            t_elem = after_r.find(qn('w:t'))
            t_elem.text = after
            if after[0] == ' ':
                t_elem.set(qn('xml:space'), 'preserve')
            after_rPr = after_r.find(qn('w:rPr'))
            if after_rPr is not None:
                after_vert = after_rPr.find(qn('w:vertAlign'))
                if after_vert is not None:
                    after_rPr.remove(after_vert)
            run_elem.addnext(after_r)
    
    return True


def _apply_superscript_numbers(paragraph, numbers):
    for num in numbers:
        for run in list(paragraph.runs):
            if num in run.text:
                if _split_run_for_vertical_align(paragraph, run, num, 'superscript'):
                    break


def _apply_ordinals(paragraph, ordinals, formatting_records, source_text, align_type, location=None):
    for ordinal in ordinals:
        found = False
        text = paragraph.text
        for pattern in [_EN_ORDINAL_SUFFIXES, _FR_ORDINAL_SUFFIXES]:
            for match in pattern.finditer(text):
                full_match = match.group(0)
                suffix = match.group(2)
                if full_match == ordinal or ordinal.rstrip('thstndrd') == match.group(1):
                    suffix_start = match.start(2)
                    char_offset = 0
                    for run in list(paragraph.runs):
                        run_end = char_offset + len(run.text)
                        if char_offset <= suffix_start < run_end:
                            local_offset = suffix_start - char_offset
                            if _split_run_for_vertical_align(paragraph, run, suffix, align_type, offset=local_offset):
                                found = True
                                break
                        char_offset = run_end
                    if found:
                        break
            if found:
                break
        if not found:
            record = {
                'original_text': source_text,
                'full_paragraph': source_text,
                'notes': f"{align_type.capitalize()} ordinal '{ordinal}' could not be matched in translated text",
            }
            if location:
                record['location'] = location
            formatting_records.append(record)


# Backward-compatible wrappers (used by tests)
def _apply_subscript_ordinals(paragraph, ordinals, formatting_records, source_text):
    _apply_ordinals(paragraph, ordinals, formatting_records, source_text, 'subscript')


def _apply_superscript_ordinals(paragraph, ordinals, formatting_records, source_text):
    _apply_ordinals(paragraph, ordinals, formatting_records, source_text, 'superscript')


# ---------------------------------------------------------------------------
# Formatting rules registry
# ---------------------------------------------------------------------------

def _rule_italic_brackets(paragraph, detected_patterns, formatting_records, source_text, location):
    ib = detected_patterns.get("italic_brackets")
    if not ib:
        return
    
    if ib["ambiguous_notes"]:
        record = {
            'original_text': source_text,
            'full_paragraph': source_text,
            'notes': ib["ambiguous_notes"],
        }
        if location:
            record['location'] = location
        formatting_records.append(record)
    
    if ib["apply"]:
        text = paragraph.text
        matches = list(BRACKET_PATTERN.finditer(text))
        if len(matches) == ib["expected_count"]:
            _apply_italic_brackets(paragraph, matches, text)
        else:
            success = _try_italic_brackets_per_sentence(paragraph, ib["expected_count"])
            if not success:
                record = {
                    'original_text': "check formatting",
                    'full_paragraph': source_text,
                    'notes': (
                        "Italic bracket formatting could not be automatically applied "
                        "— bracket count mismatch after translation"
                    ),
                }
                if location:
                    record['location'] = location
                formatting_records.append(record)


def _rule_superscript_numbers(paragraph, detected_patterns, formatting_records, source_text, location):
    numbers = detected_patterns.get("superscript_numbers")
    if numbers:
        _apply_superscript_numbers(paragraph, numbers)


def _rule_subscript_ordinals(paragraph, detected_patterns, formatting_records, source_text, location):
    ordinals = detected_patterns.get("subscript_ordinals")
    if ordinals:
        _apply_ordinals(paragraph, ordinals, formatting_records, source_text, 'subscript', location)


def _rule_superscript_ordinals(paragraph, detected_patterns, formatting_records, source_text, location):
    ordinals = detected_patterns.get("superscript_ordinals")
    if ordinals:
        _apply_ordinals(paragraph, ordinals, formatting_records, source_text, 'superscript', location)


FORMATTING_RULES = [
    ("italic_brackets", _rule_italic_brackets),
    ("superscript_numbers", _rule_superscript_numbers),
    ("subscript_ordinals", _rule_subscript_ordinals),
    ("superscript_ordinals", _rule_superscript_ordinals),
]


def apply_formatting_rules(paragraph, detected_patterns, formatting_records, source_text=None, location=None):
    if source_text is None:
        source_text = paragraph.text
    for rule_name, rule_fn in FORMATTING_RULES:
        rule_fn(paragraph, detected_patterns, formatting_records, source_text, location)


# ---------------------------------------------------------------------------
# Numeric detection and conversion
# ---------------------------------------------------------------------------

def _is_single_numeric(text):
    if re.search(r'\d/\d', text):
        return False
    if re.search(r'\d\s*[-\u2013\u2212]\s*\d', text):
        return False
    
    cleaned = text
    cleaned = re.sub(r'[Ee][+\-]', '', cleaned)
    cleaned = re.sub(r'[\s,.\u00a0\u202f\+\-\u2212/%<>()\[\]=#×÷±≤≥*–^°]', '', cleaned)
    
    return cleaned != '' and cleaned.isdigit()


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
