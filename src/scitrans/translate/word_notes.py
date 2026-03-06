from docx import Document
from docx.oxml.ns import qn
from scitrans.translate.word_formatting import FormattedRun


def add_formatting_notes(paragraph, formatting_records):
    full_paragraph_text = paragraph.text
    original_text = []
    notes = []
    
    for run in list(paragraph.runs):
        formatted_run = FormattedRun.create(run)
        
        if formatted_run.has_formatting and formatted_run.text.strip():
            original_text.append(run.text)
            notes.append(formatted_run.formatting_notes)
    
    formatting_records.append({
        'original_text': "\n".join(original_text),
        'full_sentence': full_paragraph_text,
        'notes': "\n".join(notes),
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
        })
    
    return True


def write_translations_notes(translations_notes, output_path):
    document = Document()
    document.add_heading('Hyperlink Translation Notes', level=1)
    
    table = document.add_table(rows=1, cols=3)
    table.style = 'Table Grid'
    
    header_cells = table.rows[0].cells
    header_cells[0].text = 'Original Text'
    header_cells[1].text = 'Full Sentence'
    header_cells[2].text = 'Notes'
    
    for record in translations_notes:
        row_cells = table.add_row().cells
        row_cells[0].text = record['original_text']
        row_cells[1].text = record['full_sentence']
        row_cells[2].text = record['notes']
    
    document.save(output_path)
