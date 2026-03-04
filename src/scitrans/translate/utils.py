import re


def normalize_apostrophes(text):
    return text.replace("'", "'").replace("'", "'")


_PROTECTED_LABEL_PATTERN = re.compile(
    r'\b(?:Figure|Fig|Table|Tableau)\.?\s*\d+\.?', re.IGNORECASE
)
_PLACEHOLDER = '\x00'


def _split_into_sentences(text):
    protected_positions = []
    for match in _PROTECTED_LABEL_PATTERN.finditer(text):
        for i, ch in enumerate(match.group()):
            if ch == '.':
                protected_positions.append(match.start() + i)
    
    chars = list(text)
    for pos in protected_positions:
        chars[pos] = _PLACEHOLDER
    
    sentences = re.split(r'(?<=[.!?])\s+', ''.join(chars))
    return [s.replace(_PLACEHOLDER, '.') for s in sentences]


def split_by_sentences(text):
    lines = text.split('\n')
    chunks = []
    chunk_metadata = []
    
    for line_idx, line in enumerate(lines):
        if not line.strip():
            chunks.append('')
            chunk_metadata.append({
                'line_idx': line_idx,
                'sent_idx': 0,
                'is_last_in_line': True,
                'is_empty': True
            })
            continue
        
        sentences = _split_into_sentences(line)
        for sent_idx, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if sentence:
                chunks.append(sentence)
                chunk_metadata.append({
                    'line_idx': line_idx,
                    'sent_idx': sent_idx,
                    'is_last_in_line': sent_idx == len(sentences) - 1,
                    'is_empty': False
                })
    
    return chunks, chunk_metadata


def split_by_paragraphs(text):
    # Notes:
    #  still get >512 token issues with 1000 characters, use 600 to be conservative
    MAX_CHAR = 600
    
    lines = text.split('\n')
    chunks = []
    chunk_metadata = []
    
    para_idx = 0
    for line_idx, line in enumerate(lines):
        if not line.strip():
            chunks.append('')
            chunk_metadata.append({
                'line_idx': line_idx,
                'para_idx': para_idx,
                'is_empty': True
            })
            para_idx += 1
            continue
        
        if len(line) <= MAX_CHAR:
            chunks.append(line)
            chunk_metadata.append({
                'line_idx': line_idx,
                'para_idx': para_idx,
                'is_last_in_line': True,
                'is_empty': False
            })
        else:
            chunks, chunk_metadata = split_by_sentences(line)
    
    return chunks, chunk_metadata


def split_into_chunks(text, chunk_by="sentences"):
    if chunk_by == "paragraphs":
        return split_by_paragraphs(text)
    else:
        return split_by_sentences(text)
