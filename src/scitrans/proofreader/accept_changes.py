import docx
from lxml import etree

W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
W = f'{{{W_NS}}}'


def _accept_insertions(root):
    # Unwrap <w:ins> — keep child content, remove wrapper
    count = 0
    for ins in list(root.iter(f'{W}ins')):
        parent = ins.getparent()
        if parent is None:
            continue
        idx = list(parent).index(ins)
        for child in list(ins):
            ins.remove(child)
            parent.insert(idx, child)
            idx += 1
        parent.remove(ins)
        count += 1
    return count


def _accept_deletions(root):
    # Remove <w:del> entirely — the deleted content goes away
    count = 0
    for del_elem in list(root.iter(f'{W}del')):
        parent = del_elem.getparent()
        if parent is not None:
            parent.remove(del_elem)
            count += 1
    return count


def _accept_format_changes(root):
    # Remove <w:rPrChange> — accept the new formatting
    count = 0
    for rpr_change in list(root.iter(f'{W}rPrChange')):
        parent = rpr_change.getparent()
        if parent is not None:
            parent.remove(rpr_change)
            count += 1
    return count


def _accept_paragraph_changes(root):
    # Remove <w:pPrChange> — accept paragraph formatting changes
    count = 0
    for ppr_change in list(root.iter(f'{W}pPrChange')):
        parent = ppr_change.getparent()
        if parent is not None:
            parent.remove(ppr_change)
            count += 1
    return count


def accept_all_changes(input_path, output_path):
    doc = docx.Document(input_path)
    root = doc.element
    
    ins_count = _accept_insertions(root)
    del_count = _accept_deletions(root)
    fmt_count = _accept_format_changes(root)
    para_count = _accept_paragraph_changes(root)
    
    doc.save(output_path)
    return {
        "insertions_accepted": ins_count,
        "deletions_accepted": del_count,
        "format_changes_accepted": fmt_count,
        "paragraph_changes_accepted": para_count,
    }
