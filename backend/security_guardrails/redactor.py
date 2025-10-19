import re
from typing import List, Dict, Any, Tuple

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+\d{1,3}[- ]?)?(?:\(?\d{3}\)?[- ]?)?\d{3}[- ]?\d{4}")
MRN_RE = re.compile(r"\b(?:MRN|Medical\s*Record\s*Number)[:#]?\s*([A-Za-z0-9-]{5,})\b", re.IGNORECASE)
PERSON_LIKE_RE = re.compile(r"\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b")

MASKS = {
    'EMAIL': '[REDACTED_EMAIL]',
    'PHONE': '[REDACTED_PHONE]',
    'MRN': '[REDACTED_MRN]',
    'PERSON': '[REDACTED_PERSON]'
}

def detect_entities(text: str) -> List[Dict[str, Any]]:
    ents: List[Dict[str, Any]] = []
    for m in EMAIL_RE.finditer(text):
        ents.append({'start': m.start(), 'end': m.end(), 'text': m.group(0), 'label': 'EMAIL'})
    for m in PHONE_RE.finditer(text):
        ents.append({'start': m.start(), 'end': m.end(), 'text': m.group(0), 'label': 'PHONE'})
    for m in MRN_RE.finditer(text):
        ents.append({'start': m.start(1), 'end': m.end(1), 'text': m.group(1), 'label': 'MRN'})
    for m in PERSON_LIKE_RE.finditer(text):
        ents.append({'start': m.start(1), 'end': m.end(1), 'text': m.group(1), 'label': 'PERSON'})
    ents.sort(key=lambda x: x['start'])
    merged: List[Dict[str, Any]] = []
    last_end = -1
    for e in ents:
        if e['start'] >= last_end:
            merged.append(e)
            last_end = e['end']
    return merged


def redact_text(text: str) -> Tuple[str, List[Dict[str, Any]]]:
    ents = detect_entities(text)
    if not ents:
        return text, []
    out = []
    i = 0
    for e in ents:
        out.append(text[i:e['start']])
        out.append(MASKS.get(e['label'], '[REDACTED]'))
        i = e['end']
    out.append(text[i:])
    return ''.join(out), ents
