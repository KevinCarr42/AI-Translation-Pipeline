from lxml import etree
from docx import Document
from docx.enum.shape import WD_INLINE_SHAPE
from pathlib import Path


def replace_images(doc1_path, doc2_path, output_path):
    doc1 = Document(doc1_path)
    doc2 = Document(doc2_path)
    
    shapes1 = [s for s in doc1.inline_shapes if s.type == WD_INLINE_SHAPE.PICTURE]
    shapes2 = [s for s in doc2.inline_shapes if s.type == WD_INLINE_SHAPE.PICTURE]
    
    if len(shapes1) != len(shapes2):
        raise ValueError(f"Mismatch: Doc1 has {len(shapes1)}, Doc2 has {len(shapes2)}.")
    
    for s1, s2 in zip(shapes1, shapes2):
        rId1 = s1._inline.graphic.graphicData.pic.blipFill.blip.embed
        rId2 = s2._inline.graphic.graphicData.pic.blipFill.blip.embed
        
        image_part2 = doc2.part.related_parts[rId2]
        doc1.part.related_parts[rId1]._blob = image_part2._blob
        
        blip_fill1 = s1._inline.graphic.graphicData.pic.blipFill
        nsmap = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
        for src_rect in blip_fill1.findall('.//a:srcRect', nsmap):
            src_rect.getparent().remove(src_rect)
        
        if blip_fill1.find('a:stretch', nsmap) is None:
            stretch = etree.SubElement(
                blip_fill1,
                '{http://schemas.openxmlformats.org/drawingml/2006/main}stretch',
            )
            etree.SubElement(
                stretch,
                '{http://schemas.openxmlformats.org/drawingml/2006/main}fillRect',
            )
        
        s1.width = s2.width
        s1.height = s2.height
    
    doc1.save(output_path)


if __name__ == '__main__':
    root = Path("image_replacing_script_tests")
    file_to_replace = root / "1432_en_translated_KC.docx"
    file_to_replace_from = root / "1432_en_translated_TB.docx"
    updated_file = root / "1432_en_translated_img_replaced.docx"
    replace_images(file_to_replace, file_to_replace_from, updated_file)
