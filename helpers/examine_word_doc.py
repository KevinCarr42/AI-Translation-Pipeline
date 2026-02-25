from docx import Document
from pathlib import Path


def list_attr(obj):
    return [x for x in dir(obj) if x[0] != "_"]


def print_dir():
    for group in [document.paragraphs, document.tables, document.sections]:
        for item in group:
            print()
            print(item.__class__.__name__)
            print([x for x in dir(item) if x[0] != "_"])
            if item.__class__.__name__ == "Table":
                for row in item.rows:
                    print('\trows:', list_attr(row))
                    for cell in row.cells:
                        print('\t\tcells:', list_attr(cell))
                        for paragraph in cell.paragraphs:
                            print('\t\t\tcell paragraphs:', list_attr(paragraph))
                            for run in paragraph.runs:
                                print('\t\t\t\tcell paragraph runs:', list_attr(run))
                                break
                            break
                        break
                    break


def print_paragraph_details(p, print_text=False, min_runs=1, only_include_format_changes=False):
    rows = []
    changes = None
    has_changes = False
    
    for idx, run in enumerate(p.runs):
        b = "Y" if run.bold else "N"
        it = "Y" if run.italic else "N"
        sz = f"{run.font.size.pt:.1f}" if run.font.size else "Def"
        fnt = str(run.font.name)[:10] if run.font.name else "Def"
        
        color = "Def"
        if run.font.color and run.font.color.rgb:
            color = str(run.font.color.rgb)
            
        if only_include_format_changes and not has_changes:
            if changes is None:
                changes = [b, it, sz, fnt, color]
            elif changes != [b, it, sz, fnt, color]:
                has_changes = True
        
        rows.append(f"{idx:<4} | {b:<4} | {it:<4} | {sz:<5} | {fnt:<10} | {color:<8} | {run.text}")
    
    if (not only_include_format_changes or has_changes) and (idx >= min_runs):
        print()
        print("-" * 80)
        print(f"{'Idx':<4} | {'Bold':<4} | {'Ital':<4} | {'Size':<5} | {'Font':<10} | {'Color':<8} | {'Text'}")
        print("-" * 80)
        print("\n".join(rows))
        if print_text:
            print()
            print(f'-> full text: "{p.text}"')
            print()


def print_section_details(doc):
    w = 20
    for i, section in enumerate(doc.sections):
        print_block(f"Section {i}", major=False)
        print()
        
        print(f"{'Start Type:':<{w}} {section.start_type}")
        print(f"{'Orientation:':<{w}} {section.orientation}")
        print(f"{'Page Size:':<{w}} {section.page_width.inches:.2f}\" x {section.page_height.inches:.2f}\"")
        print(f"{'Margins (L/R):':<{w}} {section.left_margin.inches:.2f}\" / {section.right_margin.inches:.2f}\"")
        print(f"{'First Page Header:':<{w}} {section.different_first_page_header_footer}")
        
        has_header = any(p.text.strip() for p in section.header.paragraphs)
        print(f"{'Header Text:':<{w}} {has_header}")
        print()


def print_block(text, major=True):
    if major:
        centered = f" {text.upper()} ".center(80, "=")
        print(f"\n{'=' * 80}\n{centered}\n{'=' * 80}\n")
    else:
        print(f"    {text}    ".center(80, "-"))


if __name__ == '__main__':
    filepath = Path('..') / "_TRANSLATED_DOCUMENTS" / "EXAMPLE_PROBLEM.docx"
    check_dir = False
    
    document = Document(filepath)
    
    if check_dir:
        print_dir()
        
    kwargs = {"print_text": True, "min_runs": 2, "only_include_format_changes": True}
    
    print_block("sections")
    print_section_details(document)
    
    print_block("paragraphs")
    for i, paragraph in enumerate(document.paragraphs):
        print("Paragraph", i)
        print_paragraph_details(paragraph, **kwargs)
        
    print_block("tables")
    for table in document.tables:
        for i, row in enumerate(table.rows):
            for j, cell in enumerate(row.cells):
                for k, paragraph in enumerate(cell.paragraphs):
                    print_paragraph_details(paragraph, **kwargs)
    
