import re

_PROTECTED_LABEL_PATTERN = re.compile(r'\b(Figure|Fig|Table|Tableau)\.?\s*\d+\.?', re.IGNORECASE)
_LABEL_PREFIX_RE = re.compile(r'^((?:Figure|Fig|Table|Tableau)\.?\s*\d+)\.\s+', re.IGNORECASE)
_PLACEHOLDER = '\x00'


def split_label_prefix(text):
    m = _LABEL_PREFIX_RE.match(text)
    if not m:
        return None, text
    label = m.group(1) + '.'
    rest = text[m.end():]
    return label, rest


def ensure_label_period(translated_label):
    m = _PROTECTED_LABEL_PATTERN.search(translated_label)
    if m and not m.group(0).endswith('.'):
        return translated_label[:m.end()] + '.' + translated_label[m.end():]
    if not m and not translated_label.rstrip().endswith('.'):
        return translated_label.rstrip() + '.'
    return translated_label


def normalize_apostrophes(text):
    return text.replace("'", "'").replace("'", "'")


def _protect_labels(match):
    return match.group(0).replace('.', _PLACEHOLDER)


def _split_into_sentences(text):
    protected_text = _PROTECTED_LABEL_PATTERN.sub(_protect_labels, text)
    sentences = re.split(r'(?<=[.!?])\s+', protected_text)
    return [s.replace(_PLACEHOLDER, '.') for s in sentences]


def split_by_sentences(text):
    lines = text.split('\n')
    chunks = []
    chunk_metadata = []
    
    for line_idx, line in enumerate(lines):
        if not line.strip():
            chunks.append('')
            chunk_metadata.append({'line_idx': line_idx, 'sent_idx': 0, 'is_last_in_line': True, 'is_empty': True})
            continue
        
        sentences = _split_into_sentences(line)
        for sent_idx, sentence in enumerate(sentences):
            stripped = sentence.strip()
            if stripped:
                chunks.append(stripped)
                chunk_metadata.append({
                    'line_idx': line_idx,
                    'sent_idx': sent_idx,
                    'is_last_in_line': sent_idx == len(sentences) - 1,
                    'is_empty': False
                })
    
    return chunks, chunk_metadata


def split_by_paragraphs(text):
    MAX_CHAR = 600
    lines = text.split('\n')
    chunks = []
    chunk_metadata = []
    
    para_idx = 0
    for line_idx, line in enumerate(lines):
        if not line.strip():
            chunks.append('')
            chunk_metadata.append({'line_idx': line_idx, 'para_idx': para_idx, 'is_empty': True})
            para_idx += 1
            continue
        
        if len(line) <= MAX_CHAR:
            chunks.append(line)
            chunk_metadata.append({'line_idx': line_idx, 'para_idx': para_idx, 'is_last_in_line': True, 'is_empty': False})
        else:
            s_chunks, s_meta = split_by_sentences(line)
            for meta in s_meta:
                meta['para_idx'] = para_idx
            chunks.extend(s_chunks)
            chunk_metadata.extend(s_meta)
    
    return chunks, chunk_metadata


def split_into_chunks(text, chunk_by="sentences"):
    if chunk_by == "paragraphs":
        return split_by_paragraphs(text)
    return split_by_sentences(text)


def reassemble_chunks(translated_chunks, chunk_metadata):
    lines_dict = {}
    for chunk, metadata in zip(translated_chunks, chunk_metadata):
        line_idx = metadata['line_idx']
        lines_dict.setdefault(line_idx, []).append(chunk)
    
    for line_idx, parts in lines_dict.items():
        if isinstance(parts, list):
            lines_dict[line_idx] = ' '.join(parts)
    
    return '\n'.join(lines_dict[i] for i in sorted(lines_dict.keys()))


def reassemble_sentences(translated_chunks, chunk_metadata):
    return reassemble_chunks(translated_chunks, chunk_metadata)


def reassemble_paragraphs(translated_chunks, chunk_metadata):
    return reassemble_chunks(translated_chunks, chunk_metadata)
