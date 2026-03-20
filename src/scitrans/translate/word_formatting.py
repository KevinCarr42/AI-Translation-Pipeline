import re
from copy import deepcopy
from dataclasses import dataclass

from docx.oxml.ns import qn
from lxml import etree

BRACKET_PATTERN = re.compile(r'\([^)]+\)')
_SEPARATOR_RE = re.compile(r'\s+[-\u2013\u2212]\s+')
_SPP_PATTERN = re.compile(r'\b(spp?\.)$')
_SENTENCE_BOUNDARY = re.compile(r'(?<=[.!?])\s+')
_FR_ORDINAL_SUFFIXES = re.compile(r'(\d+)(e|er|ère)\b')
_EN_ORDINAL_SUFFIXES = re.compile(r'(\d+)(th|st|nd|rd)\b')


@dataclass(frozen=True)
class FormattedRun:
    _DEFAULT_COLOUR = "default"
    _FORMATTING_BOOLS = ('bold', 'italic', 'underline', 'superscript', 'subscript')
    text: str
    bold: bool = False
    italic: bool = False
    underline: bool = False
    superscript: bool = False
    subscript: bool = False
    colour: str = "default"
    
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
        notes = [attr for attr in self._FORMATTING_BOOLS if getattr(self, attr)]
        if self.colour != self._DEFAULT_COLOUR:
            notes.append(f'colour={self.colour}')
        return ", ".join(notes) if notes else "no formatting"


class RuleRegistry:
    _rules = []
    
    @classmethod
    def register(cls, rule_class):
        cls._rules.append(rule_class())
        return rule_class
    
    @classmethod
    def apply_all(cls, paragraph, formatting_records, source_text=None, location=None):
        if source_text is None:
            source_text = paragraph.text
        for rule in cls._rules:
            matches = rule.detect(paragraph)
            if matches is not None and matches != []:
                success = rule.apply(paragraph, matches)
                if not success or getattr(rule, 'always_note', False):
                    rule.add_notes(formatting_records, source_text, location)
    
    @classmethod
    def detect_all(cls, paragraph):
        detected = {}
        for rule in cls._rules:
            matches = rule.detect(paragraph)
            if matches is not None and matches != []:
                detected[rule] = matches
        return detected
    
    @classmethod
    def apply_detected(cls, paragraph, detected, formatting_records, source_text, location):
        for rule, matches in detected.items():
            success = rule.apply(paragraph, matches)
            if not success or getattr(rule, 'always_note', False):
                rule.add_notes(formatting_records, source_text, location)
    
    @classmethod
    def is_auto_handled(cls, formatted_run, detected_rules):
        for rule in detected_rules:
            if hasattr(rule, 'handles_run') and rule.handles_run(formatted_run):
                return True
        return False


class FormattingRule:
    note_message = "Formatting applied or failed"
    
    def detect(self, paragraph):
        raise NotImplementedError
    
    def apply(self, paragraph, matches):
        raise NotImplementedError
    
    def add_notes(self, formatting_records, source_text, location):
        record = {
            'original_text': source_text,
            'full_paragraph': source_text,
            'notes': self.note_message,
        }
        if location:
            record['location'] = location
        formatting_records.append(record)


def _set_single_run_text(run_elem, text):
    for child in list(run_elem):
        if child.tag in (qn('w:t'), qn('w:br')):
            run_elem.remove(child)
    t = etree.SubElement(run_elem, qn('w:t'))
    t.text = text
    if text and (text[0] == ' ' or text[-1] == ' '):
        t.set(qn('xml:space'), 'preserve')


def _split_run_for_vertical_align(paragraph, run, text_fragment, align_type, offset=None):
    run_elem = run._element
    text = run.text
    idx = offset if offset is not None else text.find(text_fragment)
    if idx == -1:
        return False

    before = text[:idx]
    after = text[idx + len(text_fragment):]

    if before:
        new_r = deepcopy(run_elem)
        _set_single_run_text(run_elem, before)
        _set_single_run_text(new_r, text_fragment)
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
            _set_single_run_text(after_r, after)
            new_r.addnext(after_r)
    else:
        new_r = deepcopy(run_elem)
        _set_single_run_text(run_elem, text_fragment)
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
            _set_single_run_text(after_r, after)
            after_rPr = after_r.find(qn('w:rPr'))
            if after_rPr is not None:
                after_vert = after_rPr.find(qn('w:vertAlign'))
                if after_vert is not None:
                    after_rPr.remove(after_vert)
            run_elem.addnext(after_r)

    return True


@RuleRegistry.register
class SuperscriptNumbersRule(FormattingRule):
    def detect(self, paragraph):
        return [run.text.strip() for run in paragraph.runs if run.font.superscript and run.text.strip() and is_numeric(run.text.strip())]
    
    def handles_run(self, formatted_run):
        return formatted_run.superscript and is_numeric(formatted_run.text.strip())
    
    def apply(self, paragraph, matches):
        for num in matches:
            for run in list(paragraph.runs):
                if num in run.text:
                    if _split_run_for_vertical_align(paragraph, run, num, 'superscript'):
                        break
        return True


@RuleRegistry.register
class SubscriptOrdinalsRule(FormattingRule):
    note_message = "Subscript ordinal could not be matched in translated text"
    
    def detect(self, paragraph):
        _ordinal_suffixes = {'th', 'st', 'nd', 'rd'}
        matches = []
        runs = paragraph.runs
        for i, run in enumerate(runs):
            if run.font.subscript and run.text.strip().lower() in _ordinal_suffixes and i > 0:
                prev_text = runs[i - 1].text.rstrip()
                if prev_text and prev_text[-1].isdigit():
                    matches.append(prev_text.split()[-1] + run.text.strip())
        return matches
    
    def handles_run(self, formatted_run):
        _suffixes = {'th', 'st', 'nd', 'rd'}
        return formatted_run.subscript and formatted_run.text.strip().lower() in _suffixes
    
    def apply(self, paragraph, matches):
        all_found = True
        for ordinal in matches:
            found = False
            text = paragraph.text
            for pattern in [_EN_ORDINAL_SUFFIXES, _FR_ORDINAL_SUFFIXES]:
                for match in pattern.finditer(text):
                    if match.group(0) == ordinal or ordinal.rstrip('thstndrd') == match.group(1):
                        suffix_start = match.start(2)
                        char_offset = 0
                        for run in list(paragraph.runs):
                            run_end = char_offset + len(run.text)
                            if char_offset <= suffix_start < run_end:
                                local_offset = suffix_start - char_offset
                                if _split_run_for_vertical_align(paragraph, run, match.group(2), 'subscript', offset=local_offset):
                                    found = True
                                    break
                            char_offset = run_end
                        if found:
                            break
                if found:
                    break
            if not found:
                all_found = False
        return all_found


@RuleRegistry.register
class SuperscriptOrdinalsRule(FormattingRule):
    note_message = "Superscript ordinal could not be matched in translated text"
    
    def detect(self, paragraph):
        _ordinal_suffixes = {'th', 'st', 'nd', 'rd'}
        matches = []
        runs = paragraph.runs
        for i, run in enumerate(runs):
            if run.font.superscript and run.text.strip().lower() in _ordinal_suffixes and i > 0:
                prev_text = runs[i - 1].text.rstrip()
                if prev_text and prev_text[-1].isdigit():
                    matches.append(prev_text.split()[-1] + run.text.strip())
        return matches
    
    def handles_run(self, formatted_run):
        _suffixes = {'th', 'st', 'nd', 'rd'}
        return formatted_run.superscript and formatted_run.text.strip().lower() in _suffixes
    
    def apply(self, paragraph, matches):
        all_found = True
        for ordinal in matches:
            found = False
            text = paragraph.text
            for pattern in [_EN_ORDINAL_SUFFIXES, _FR_ORDINAL_SUFFIXES]:
                for match in pattern.finditer(text):
                    if match.group(0) == ordinal or ordinal.rstrip('thstndrd') == match.group(1):
                        suffix_start = match.start(2)
                        char_offset = 0
                        for run in list(paragraph.runs):
                            run_end = char_offset + len(run.text)
                            if char_offset <= suffix_start < run_end:
                                local_offset = suffix_start - char_offset
                                if _split_run_for_vertical_align(paragraph, run, match.group(2), 'superscript', offset=local_offset):
                                    found = True
                                    break
                            char_offset = run_end
                        if found:
                            break
                if found:
                    break
            if not found:
                all_found = False
        return all_found


@RuleRegistry.register
class ItalicBracketsRule(FormattingRule):
    def handles_run(self, formatted_run):
        return formatted_run.italic and not formatted_run.bold and not formatted_run.superscript and not formatted_run.subscript
    
    def add_notes(self, formatting_records, source_text, location):
        record = {
            'original_text': 'check formatting',
            'full_paragraph': source_text,
            'notes': self.note_message,
        }
        if location:
            record['location'] = location
        formatting_records.append(record)
    
    def detect(self, paragraph):
        runs = paragraph.runs
        merged = []
        i = 0
        while i < len(runs):
            if runs[i].italic and runs[i].text.strip():
                combined = runs[i].text
                j = i + 1
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
        
        if not merged:
            return None
        
        full_text = paragraph.text
        bracket_matches = list(BRACKET_PATTERN.finditer(full_text))
        all_italic_count = 0
        any_partial = False
        
        for match in bracket_matches:
            content = match.group()[1:-1]
            if not any(it in content for it in merged):
                continue
            remaining = content
            for it in merged:
                remaining = remaining.replace(it, "")
            remaining_stripped = remaining.strip()
            if remaining_stripped == "" or bool(_SPP_PATTERN.search(remaining_stripped)):
                all_italic_count += 1
            else:
                any_partial = True
        
        if any_partial:
            return None
        
        if all_italic_count > 0:
            return all_italic_count
        return None
    
    def apply(self, paragraph, expected_count):
        text = paragraph.text
        matches = list(BRACKET_PATTERN.finditer(text))
        if len(matches) == expected_count:
            self._apply_matches(paragraph, matches, text)
            return True
        
        sentences = _SENTENCE_BOUNDARY.split(text)
        sentence_counts = [len(BRACKET_PATTERN.findall(s)) for s in sentences]
        total_found = sum(sentence_counts)
        
        if total_found == expected_count:
            apply_indices = set(range(len(sentences)))
        elif total_found > expected_count:
            apply_indices = set()
            for i, count in enumerate(sentence_counts):
                if count == expected_count:
                    apply_indices = {i}
                    break
        else:
            apply_indices = set()
        
        if not apply_indices:
            self.note_message = "Italic bracket formatting could not be automatically applied — bracket count mismatch after translation"
            return False
        
        parts = []
        for i, sentence in enumerate(sentences):
            if i > 0:
                parts.append(FormattedRun(text=" "))
            s_matches = list(BRACKET_PATTERN.finditer(sentence))
            if s_matches and i in apply_indices:
                parts.extend(self._build_parts(sentence, s_matches))
            else:
                parts.append(FormattedRun(text=sentence))
        
        paragraph.clear()
        for part in parts:
            run = paragraph.add_run(part.text)
            if part.italic:
                run.italic = True
        return True
    
    def _build_parts(self, text, matches):
        parts = []
        last_end = 0
        for match in matches:
            before = text[last_end:match.start()]
            if before:
                parts.append(FormattedRun(text=before))
            content = match.group()[1:-1]
            parts.append(FormattedRun(text="("))
            spp_match = _SPP_PATTERN.search(content)
            if spp_match:
                main_content = content[:spp_match.start()].rstrip()
                spp_suffix = spp_match.group(1)
                if main_content:
                    parts.append(FormattedRun(text=main_content, italic=True))
                    parts.append(FormattedRun(text=" " + spp_suffix))
                else:
                    parts.append(FormattedRun(text=spp_suffix))
            else:
                parts.append(FormattedRun(text=content, italic=True))
            parts.append(FormattedRun(text=")"))
            last_end = match.end()
        remainder = text[last_end:]
        if remainder:
            parts.append(FormattedRun(text=remainder))
        return parts
    
    def _apply_matches(self, paragraph, matches, text):
        parts = self._build_parts(text, matches)
        paragraph.clear()
        for part in parts:
            run = paragraph.add_run(part.text)
            if part.italic:
                run.italic = True


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


def _is_single_numeric(text):
    if re.search(r'\d/\d', text):
        return False
    if re.search(r'\d\s*[-\u2013\u2212]\s*\d', text):
        return False
    cleaned = re.sub(r'[Ee][+\-]', '', text)
    cleaned = re.sub(r'[\s,.\u00a0\u202f\+\-\u2212/%<>()\[\]=#×÷±≤≥*–^°]', '', cleaned)
    return cleaned != '' and cleaned.isdigit()


def is_numeric(text):
    if not text or not text.strip():
        return False
    parts = _SEPARATOR_RE.split(text.strip())
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


def apply_formatting_rules(paragraph, formatting_records, source_text=None, location=None, detected=None):
    if detected is not None:
        RuleRegistry.apply_detected(paragraph, detected, formatting_records, source_text, location)
    else:
        RuleRegistry.apply_all(paragraph, formatting_records, source_text, location)
