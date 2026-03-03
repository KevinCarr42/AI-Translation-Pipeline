import re


_SEPARATOR_RE = re.compile(r'\s+[-\u2013\u2212]\s+')


def _is_single_numeric(text):
    if re.search(r'\d/\d', text):
        return False
    if re.search(r'\d\s*[-\u2013\u2212]\s*\d', text):
        return False

    cleaned = text
    cleaned = re.sub(r'[Ee][+\-]', '', cleaned)
    cleaned = re.sub(r'[\s,.\u00a0\u202f\+\-\u2212/%<>()\[\]=#×÷±≤≥*–^°]', '', cleaned)

    return cleaned == '' or cleaned.isdigit()


def is_numeric(text):
    if not text or not text.strip():
        return False

    stripped = text.strip()
    parts = _SEPARATOR_RE.split(stripped)
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
