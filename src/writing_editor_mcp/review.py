"""Mechanical review of a revision against its draft: preserved markers, required terms, sample overlap and style notes."""

from __future__ import annotations

from collections import Counter
import re

# Matches are independent so a number inside a quote can also be checked as a number.
MARKERS = {
    "number": re.compile(
        r"(?<!\w)[+−-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?:[eE][+−-]?\d+)?(?:[ \t]?(?:%|‰|ms\b|s\b|kg\b|mg\b|GB\b|MB\b|mm\b|cm\b|Hz\b))?"
    ),
    "link": re.compile(r"https?://[^\s<>\"\]\)]+"),
    "citation": re.compile(
        r"\[(?:\s*\d+(?:\s*[,;–—-]\s*\d+)*\s*|@[^\]\n]+)\]|\([^()\n]{1,120}?\b(?:19|20)\d{2}[a-z]?(?:[,;][^()\n]+)?\)"
    ),
    # Character escapes such as \% are not commands, so escaping a percent sign is not a change.
    "latex_command": re.compile(r"\\(?:[A-Za-z@]+\*?|[^\s%&#_${}])"),
    # Prose inside commands such as \emph may change. Literal reference arguments must survive.
    "latex_reference": re.compile(
        r"\\(?:[A-Za-z]*[Cc]ite[A-Za-z]*|label|ref|pageref|eqref|autoref|nameref|"
        r"[Cc]ref(?:range)?|[Cc]pageref(?:range)?|begin|end)\*?(?![A-Za-z@])"
        r"(?:\s*(?:\[[^\[\]]*\]\s*)*\{[^{}]+\})+"
    ),
    "quotation": re.compile(
        r"``[^`'\n]+''|“[^”]+”|\"[^\"\n]+\"|(?<!\w)‘[^’\n]+’(?!\w)|(?<![\w'`])\x27[^\x27\n]+\x27(?![\w'])"
    ),
    "code": re.compile(
        r"(?ms)^(?P<fence>`{3,}|~{3,})[^\n]*\n.*?^(?P=fence)[ \t]*(?=\n|$)|(?P<inline>`+)[^`\n]+(?P=inline)"
    ),
}

STYLE_RULES = [
    (
        "cross-reference phrasing",
        r"\brespectively\b|\band/or\b|\bthe (?:former|latter)\b",
        "The reader has to match items across the sentence. Pair each item with its value, choose 'and' or 'or', or repeat the noun.",
    ),
    (
        "non-statistical 'significant'",
        r"\bsignificant(?:ly)?\b",
        "Readers take it as a claim of statistical significance. Keep it only for a reported test; otherwise give the number or a plain word.",
    ),
    (
        "priority or novelty claim",
        r"\bnovel\b|\bto the best of our knowledge\b|\bthe first (?:to|study|work|approach|method|paper|tool|technique|system|attempt)\b",
        "Invites the reader to look for a counterexample. Show what is new by contrast with the closest prior work.",
    ),
    (
        "filler",
        r"\bit (?:is|should be) (?:important to note|worth noting|noted) that\b|\bit can be (?:seen|observed|noted) that\b|\bin order to\b|\bdue to the fact that\b|\ba total of\b",
        "Adds words without adding information.",
    ),
    (
        "inflated word",
        r"\butili[sz](?:e|es|ed|ing|ation)\b|\bleverag(?:e|es|ed|ing)\b|\bfacilitat(?:e|es|ed|ing)\b|\bplethora\b|\bparadigm\b|\bholistic\b|\bsynerg(?:y|ies|istic)\b",
        "A plainer word such as 'use', 'help' or 'many' is usually as accurate and easier for a newcomer.",
    ),
    (
        "stacked hedge",
        r"\b(?:may|might|could) (?:possibly|potentially|perhaps)\b|\bpossibly (?:may|might|could)\b",
        "One hedge per claim is enough.",
    ),
    (
        "sentence starts with a numeral",
        r"(?:^|(?<=[.!?])(?<!e\.g\.)(?<!i\.e\.)(?<!\bal\.)(?<!\bfig\.)(?<!\beq\.)(?<!\bno\.)(?<!\bvs\.)(?<!\bcf\.)(?<!\bsec\.)[ \t]+)"
        r"[+−-]?\d(?:[\d,.]*\d)?%?(?=[ \t]+[A-Za-z])",
        "Hard to read at the start of a sentence. Rephrase so the number comes later.",
    ),
]
STRUCTURAL = re.compile(r"^\s*(?:[\\%#|>$&*+-]|\d+[.)]\s|`{3}|~{3})")
VERBATIM = re.compile(
    r"\\(begin|end)\{(equation|align|gather|multline|eqnarray|displaymath|math|tabular|tabularx|array|verbatim|lstlisting|minted|algorithmic)\*?\}"
)


def hard_wrapped(text: str) -> list[str]:
    """Return the first line of each prose paragraph that continues on the next source line."""
    found, depth, fenced, previous = [], 0, False, ""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("```", "~~~")):
            fenced, previous = not fenced, ""
            continue
        for match in VERBATIM.finditer(line):
            depth += 1 if match.group(1) == "begin" else -1
        prose = (
            bool(stripped)
            and not fenced
            and depth <= 0
            and not STRUCTURAL.match(line)
            and not stripped.endswith("\\\\")
            and "&" not in stripped
        )
        if prose and previous:
            found.append(previous[:80])
            previous = ""
        else:
            previous = stripped if prose else ""
    return found


def style_notes(revision: str) -> list[dict]:
    """Flag phrasing that scientific readers stumble over. Quotations, code and links are ignored."""
    text = revision
    for label in ("code", "quotation", "link"):
        text = MARKERS[label].sub(" ", text)
    notes = []
    for issue, pattern, why in STYLE_RULES:
        hits = [
            m.group().strip()
            for m in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
        ]
        if hits:
            notes.append(
                {
                    "issue": issue,
                    "matches": sorted(set(hits), key=hits.index)[:5],
                    "why": why,
                }
            )
    wrapped = hard_wrapped(revision)
    if wrapped:
        notes.append(
            {
                "issue": "paragraph split across source lines",
                "matches": wrapped[:5],
                "why": "Keep each prose paragraph and caption on one source line so diffs and tracked changes line up with paragraphs.",
            }
        )
    return notes


# Words that set how strongly a claim holds. Swapping words within a class ("every" for "each") keeps the
# strength; a change in a class's count ("often" dropped, "could" or "full" added) can change the claim.
QUALIFIERS = {
    "all or none": "all every each always entire entirely whole none never",
    "most or often": "most mostly largely mainly majority usually often frequently generally typically commonly",
    "some or sometimes": "some sometimes many several occasionally partly partially",
    "few or rarely": "few rarely seldom minority",
    "possibility": "may might could can possibly perhaps probably likely unlikely suggest suggests suggested",
    "intensifier": "full fully complete completely clearly strongly highly very substantially considerably",
    "limiter": "only just solely exclusively merely",
    "negation": "not no nor neither without cannot n't",
}
QUALIFIER_CLASS = {word: label for label, words in QUALIFIERS.items() for word in words.split()}
QUALIFIER_WORD = re.compile(r"[A-Za-z]+(?:['’]t\b)?")


def qualifier_counts(text: str) -> dict[str, Counter]:
    for label in ("code", "link", "latex_command"):
        text = MARKERS[label].sub(" ", text)
    counts: dict[str, Counter] = {}
    for match in QUALIFIER_WORD.finditer(text):
        word = match.group().casefold()
        if word.endswith(("'t", "’t")):
            word = "n't"  # don't, isn't, can't
        label = QUALIFIER_CLASS.get(word)
        if label:
            counts.setdefault(label, Counter())[word] += 1
    return counts


def qualifier_changes(draft: str, revision: str) -> list[dict]:
    """List each class of strength words whose count changed between draft and revision."""
    before, after = qualifier_counts(draft), qualifier_counts(revision)
    found = []
    for label in QUALIFIERS:
        old, new = before.get(label, Counter()), after.get(label, Counter())
        if sum(old.values()) != sum(new.values()):
            found.append({"words": label, "removed": dict(old - new), "added": dict(new - old)})
    return found


LATEX_HINT = re.compile(r"\\[A-Za-z]{2,}")
BARE_PERCENT = re.compile(r"\d[ \t]?%")


def looks_like_latex(text: str) -> bool:
    """True when the text contains a LaTeX command such as \\cite or \\section."""
    return bool(LATEX_HINT.search(text))


def latex_issues(revision: str) -> list[dict]:
    """Find percent signs after a number that LaTeX would read as the start of a comment."""
    hits = []
    for line in MARKERS["code"].sub(" ", revision).splitlines():
        if line.lstrip().startswith("%"):
            continue  # a whole-line comment is intentional
        hits += [
            line[max(0, m.start() - 24) : m.end()].strip()
            for m in BARE_PERCENT.finditer(line)
        ]
    if not hits:
        return []
    return [
        {
            "issue": "unescaped percent sign",
            "matches": hits[:5],
            "why": "In LaTeX an unescaped % starts a comment, so the rest of the line disappears from the compiled document. Write \\% instead.",
        }
    ]


def has_term(term: str, text: str) -> bool:
    """Exact match, allowing the first letter's case to change, as at the start of a sentence."""
    return any(
        variant in text
        for variant in {term, term[:1].upper() + term[1:], term[:1].lower() + term[1:]}
    )


def length_report(draft: str, revision: str, target_words: int | None) -> dict:
    before, after = len(draft.split()), len(revision.split())
    report = {
        "draft_words": before,
        "revision_words": after,
        "change_percent": round(100 * (after - before) / before, 1) if before else None,
    }
    if target_words:
        report.update(
            target_words=target_words,
            within_target=abs(after - target_words) <= 0.1 * target_words,
        )
    return report


def phrases(text: str) -> set[tuple[str, ...]]:
    words = re.findall(r"[\w’']+", text.casefold())
    return set(zip(*(words[i:] for i in range(8))))


def audit(
    draft: str,
    revision: str,
    samples: list[str],
    keep: list[str],
    target_words: int | None = None,
    latex: bool | None = None,
) -> dict:
    if latex is None:
        latex = looks_like_latex(draft)
    changes = {}
    for label, pattern in MARKERS.items():

        def values(text: str) -> Counter:
            if label == "number":
                text = text.replace(
                    "\\%", "%"
                )  # 61.3\% in LaTeX is the same number as 61.3%
            return Counter(
                m.group().rstrip(".,;:!?") if label == "link" else m.group()
                for m in pattern.finditer(text)
            )

        before, after = values(draft), values(revision)
        if before != after:
            changes[label] = {
                "removed": dict(before - after),
                "added": dict(after - before),
            }
    missing = [term for term in dict.fromkeys(keep) if not has_term(term, revision)]
    new_phrases = phrases(revision) - phrases(draft)
    overlaps = []
    for i, sample in enumerate(samples, 1):
        common = sorted(new_phrases & phrases(sample))
        if common:
            overlaps.append(
                {
                    "sample": i,
                    "example": " ".join(common[0]),
                    "matching_eight_word_spans": len(common),
                }
            )
    length = length_report(draft, revision, target_words)
    tex = latex_issues(revision) if latex else []
    flagged = (
        changes or missing or overlaps or tex or length.get("within_target") is False
    )
    return {
        "status": "review_flags" if flagged else "no_mechanical_flags",
        "marker_changes": changes,
        "missing_required_terms": missing,
        "sample_overlap": overlaps,
        "length": length,
        "latex_issues": tex,
        "unchanged": draft == revision,
        "qualifier_changes": qualifier_changes(draft, revision),
        "style_notes": style_notes(revision),
        "human_check": "Read the two passages side by side for changes to meaning, who did what, units, negation, and the strength of each claim. Check every entry in qualifier_changes: each can make a claim stronger or weaker. Check that each part the draft announces is still named where its material appears.",
    }
