from docx import Document


# FIXME:
#  add formatting notes
#  create tests
def add_translations_notes(paragraph, notes):
    print(notes)
    pass


# FIXME
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