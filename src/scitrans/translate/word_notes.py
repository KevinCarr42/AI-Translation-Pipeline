from docx import Document
from docx.oxml.ns import qn
from lxml import etree
from scitrans.translate.word_formatting import FormattedRun


def add_formatting_notes(paragraph, formatting_records):
    full_paragraph_text = paragraph.text

    for run in list(paragraph.runs):
        formatted_run = FormattedRun.create(run)

        if formatted_run.has_formatting and formatted_run.text.strip():
            formatting_records.append({
                'original_text': run.text,
                'full_sentence': full_paragraph_text,
                'notes': formatted_run.formatting_notes,
                'type': 'formatting',
            })


def has_hyperlinks(paragraph, formatting_records):
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
        formatting_records.append({
            'original_text': original_text,
            'full_sentence': full_paragraph_text,
            'notes': url,
            'type': 'hyperlink',
        })
    
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
        key = record.get('full_sentence', '')
        if key not in groups:
            groups[key] = []
        # Deduplicate by (original_text, notes) within each group
        dedup_key = (record.get('original_text', ''), record.get('notes', ''))
        existing = [(r.get('original_text', ''), r.get('notes', '')) for r in groups[key]]
        if dedup_key not in existing:
            groups[key].append(record)
    return groups


def _get_cell_color(details_list):
    has_formatting = any(d.get('type') == 'formatting' for d in details_list)
    has_hyperlink = any(d.get('type') == 'hyperlink' for d in details_list)
    if has_formatting and has_hyperlink:
        return 'BRIGHT_GREEN'
    if has_hyperlink:
        return 'TURQUOISE'
    return 'YELLOW'


def _set_cell_shading(cell, color_name):
    color_map = {
        'YELLOW': 'FFFF00',
        'TURQUOISE': '00FFFF',
        'BRIGHT_GREEN': '00FF00',
    }
    hex_color = color_map.get(color_name, 'FFFF00')
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shading = tcPr.find(qn('w:shd'))
    if shading is None:
        shading = etree.SubElement(tcPr, qn('w:shd'))
    shading.set(qn('w:val'), 'clear')
    shading.set(qn('w:color'), 'auto')
    shading.set(qn('w:fill'), hex_color)


def _write_bulleted_details(cell, details_list):
    from docx.shared import Pt
    cell.text = ''
    for i, detail in enumerate(details_list):
        original = detail.get('original_text', '')
        notes = detail.get('notes', '')
        line = f'- "{original}": {notes}'
        if i == 0:
            paragraph = cell.paragraphs[0]
            paragraph.text = line
        else:
            paragraph = cell.add_paragraph(line)
        for run in paragraph.runs:
            run.font.size = Pt(11)
            run.font.name = 'Calibri'

    _set_cell_shading(cell, _get_cell_color(details_list))


def write_translations_notes(translations_notes, output_path):
    from docx.shared import Inches, Pt
    
    filtered = _filter_notes(translations_notes)
    if not filtered:
        return
    
    grouped = _group_notes_by_paragraph(filtered)
    
    document = Document()
    
    # Set narrow margins
    for section in document.sections:
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)
        section.left_margin = Inches(0.5)
        section.right_margin = Inches(0.5)
    
    heading = document.add_heading('Formatting Notes', level=1)
    
    table = document.add_table(rows=1, cols=2)
    table.style = 'Table Grid'
    
    header_cells = table.rows[0].cells
    header_cells[0].text = 'Full Paragraph (source language)'
    header_cells[1].text = 'Details'
    for cell in header_cells:
        for run in cell.paragraphs[0].runs:
            run.font.size = Pt(11)
            run.font.name = 'Calibri'
            run.bold = True
    
    for full_sentence, details in grouped.items():
        row_cells = table.add_row().cells
        row_cells[0].text = full_sentence
        for run in row_cells[0].paragraphs[0].runs:
            run.font.size = Pt(11)
            run.font.name = 'Calibri'
        _write_bulleted_details(row_cells[1], details)
    
    document.save(output_path)
