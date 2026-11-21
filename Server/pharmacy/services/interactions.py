"""Drug interaction pairs (v87.07). Warnings only: a sale is never blocked by this module.

Rules:
- Pairs are entered by staff. Nothing here knows about drugs; the list is only as complete as what was entered.
- A pair is stored once, lower medicine id first. A medicine cannot be paired with itself.
- Severity: minor, moderate, major.
"""
from itertools import combinations

SEVERITIES = ('minor', 'moderate', 'major')
SEVERITY_RANK = {s: i for i, s in enumerate(SEVERITIES)}
NOTE_MAX = 255


class InteractionError(ValueError):
    """A problem the user can fix. The message is shown as it is."""


def normalise_pair(a, b):
    try:
        a, b = int(a), int(b)
    except (TypeError, ValueError):
        raise InteractionError('Medicine ids must be numbers.')
    if a == b:
        raise InteractionError('A medicine cannot interact with itself. Choose two different medicines.')
    return (min(a, b), max(a, b))


def check_severity(value):
    if value not in SEVERITIES:
        raise InteractionError('Severity must be minor, moderate or major.')
    return value


def find_in_bill(medicine_ids, rules):
    """rules: {(low_id, high_id): (severity, note)}. Returns [(a, b, severity, note)], worst first."""
    ids = sorted({int(m) for m in medicine_ids})
    found = []
    for a, b in combinations(ids, 2):
        if (a, b) in rules:
            severity, note = rules[(a, b)]
            found.append((a, b, severity, note or ''))
    found.sort(key=lambda x: (-SEVERITY_RANK.get(x[2], 0), x[0], x[1]))
    return found


def load_rules(cur, medicine_ids):
    ids = sorted({int(m) for m in medicine_ids})
    if len(ids) < 2:
        return {}
    marks = ','.join(['%s'] * len(ids))
    cur.execute(f"""SELECT med_a_id, med_b_id, severity, note FROM drug_interactions
                    WHERE med_a_id IN ({marks}) AND med_b_id IN ({marks})""", ids + ids)
    return {(r['med_a_id'], r['med_b_id']): (r['severity'], r['note']) for r in cur.fetchall()}


def warnings_for_bill(cur, medicine_ids):
    """Plain-text warning lines for a bill. Empty list when no entered pair matches."""
    rules = load_rules(cur, medicine_ids)
    if not rules:
        return []
    hits = find_in_bill(medicine_ids, rules)
    if not hits:
        return []
    names = {}
    ids = sorted({x for h in hits for x in h[:2]})
    marks = ','.join(['%s'] * len(ids))
    cur.execute(f"SELECT medicine_id, name FROM medicines WHERE medicine_id IN ({marks})", ids)
    names = {r['medicine_id']: r['name'] for r in cur.fetchall()}
    out = []
    for a, b, severity, note in hits:
        line = f"Drug interaction ({severity}): {names.get(a, a)} with {names.get(b, b)}"
        if note:
            line += f" - {note}"
        out.append(line + '. Check with the pharmacist before giving both.')
    return out
