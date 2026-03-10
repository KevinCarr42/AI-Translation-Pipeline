import json

from docx.oxml.ns import qn
from scitrans.translate.word_formatting import FormattedRun


def _is_auto_handled(formatted_run, detected_patterns):
    text = formatted_run.text.strip()
    
    if formatted_run.superscript and text in (detected_patterns.get('superscript_numbers') or []):
        return True
    
    _ordinal_suffixes = {'th', 'st', 'nd', 'rd'}
    if formatted_run.superscript and text.lower() in _ordinal_suffixes:
        if detected_patterns.get('superscript_ordinals'):
            return True
    
    if formatted_run.subscript and text.lower() in _ordinal_suffixes:
        if detected_patterns.get('subscript_ordinals'):
            return True
    
    ib = detected_patterns.get('italic_brackets', {})
    if formatted_run.italic and not formatted_run.bold and not formatted_run.superscript and not formatted_run.subscript:
        if ib.get('apply'):
            return True
    
    return False


def add_formatting_notes(paragraph, formatting_records, detected_patterns=None, location=None):
    full_paragraph_text = paragraph.text
    
    for run in list(paragraph.runs):
        formatted_run = FormattedRun.create(run)
        
        if formatted_run.has_formatting and formatted_run.text.strip():
            if detected_patterns and _is_auto_handled(formatted_run, detected_patterns):
                continue
            record = {
                'original_text': run.text,
                'full_paragraph': full_paragraph_text,
                'notes': formatted_run.formatting_notes,
                'type': 'formatting',
            }
            if location:
                record['location'] = location
            formatting_records.append(record)


def has_hyperlinks(paragraph, formatting_records, location=None):
    p_elem = paragraph._element
    hyperlink_elems = list(p_elem.findall(qn('w:hyperlink')))
    if not hyperlink_elems:
        return False
    
    # Collect hyperlink data before stripping
    hyperlink_data = []
    for hl_elem in hyperlink_elems:
        r_id = hl_elem.get(qn('r:id'))
        url = ''
        if r_id and r_id in paragraph.part.rels:
            url = paragraph.part.rels[r_id].target_ref
        for r_elem in hl_elem.findall(qn('w:r')):
            t_elem = r_elem.find(qn('w:t'))
            text = t_elem.text if t_elem is not None and t_elem.text else ''
            hyperlink_data.append((text, url))
    
    # Strip hyperlink XML wrappers — move w:r elements up into w:p
    for hl_elem in hyperlink_elems:
        for r_elem in list(hl_elem.findall(qn('w:r'))):
            p_elem.insert(list(p_elem).index(hl_elem), r_elem)
        p_elem.remove(hl_elem)
    
    # Add hyperlink notes
    full_paragraph_text = paragraph.text
    for original_text, url in hyperlink_data:
        record = {
            'original_text': original_text,
            'full_paragraph': full_paragraph_text,
            'notes': url,
            'type': 'url',
        }
        if location:
            record['location'] = location
        formatting_records.append(record)
    
    return True


def _filter_notes(records):
    filtered = []
    for record in records:
        original = record.get('original_text', '')
        if not original or not original.strip():
            continue
        notes = record.get('notes', '')
        if not notes or not notes.strip():
            continue
        # Filter out colour=000000 only notes
        note_lines = [line.strip() for line in notes.split('\n') if line.strip()]
        meaningful = [
            line for line in note_lines
            if line != 'colour=000000' and line.strip() not in ('', ' ')
        ]
        if not meaningful:
            continue
        record = dict(record)
        record['notes'] = '\n'.join(meaningful)
        filtered.append(record)
    return filtered


def _group_notes_by_paragraph(records):
    groups = {}
    for record in records:
        key = record.get('full_paragraph', '')
        if key not in groups:
            groups[key] = []
        # Deduplicate by notes within each paragraph group
        dedup_key = record.get('notes', '')
        existing = [r.get('notes', '') for r in groups[key]]
        if dedup_key not in existing:
            groups[key].append(record)
    return groups


def _get_note_type(details_list):
    has_formatting = any(d.get('type') == 'formatting' for d in details_list)
    has_url = any(d.get('type') == 'url' for d in details_list)
    if has_formatting and has_url:
        return 'mixed'
    if has_url:
        return 'url'
    return 'formatting'


def write_notes_json(formatting_records, output_path):
    filtered = _filter_notes(formatting_records)
    if not filtered:
        return
    
    grouped = _group_notes_by_paragraph(filtered)
    
    paragraphs_section = []
    tables_section = []
    
    for full_paragraph, details in grouped.items():
        # Determine which section based on location of first record that has one
        location = None
        for d in details:
            if 'location' in d:
                location = d['location']
                break
        
        entry = {
            'full_paragraph': full_paragraph,
            'type': _get_note_type(details),
            'notes': [
                {
                    'original_text': d.get('original_text', ''),
                    'detail': d.get('notes', ''),
                    'type': d.get('type', 'formatting'),
                }
                for d in details
            ],
        }
        if location:
            entry['location'] = location
        
        if location and location.get('section') == 'tables':
            tables_section.append(entry)
        else:
            paragraphs_section.append(entry)
    
    output = {
        'paragraphs': paragraphs_section,
        'tables': tables_section,
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)


# Backward-compatible alias
write_translations_notes = write_notes_json
