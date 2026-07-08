"""Signal 2: Stylometric heuristics (pure Python).

Computes three structural metrics of a text, each normalized to [0.0, 1.0]
where 1.0 = structurally AI-like, and averages them into a single
`stylo_score`. See planning.md, "Signal 2".

Blind spots (per spec): formal human writing scores AI-like, and texts under
~80 words produce unreliable variance estimates.
"""

import re

# Sentence-length variance: human writing mixes short and long sentences, so a
# high standard deviation of sentence lengths reads as human. We treat a stddev
# at or above this many tokens as fully human-like (score 0).
SENTENCE_STDDEV_HUMAN = 8.0

# Type-token ratio: AI text trends toward lower vocabulary diversity. TTR at or
# below LOW reads as fully AI-like; at or above HIGH as fully human-like.
TTR_AI = 0.40
TTR_HUMAN = 0.75

# TTR is inversely tied to length: short texts have few chances to repeat a word,
# so they score high TTR regardless of authorship. Below this word count the
# metric carries no reliable signal and abstains (returns neutral).
TTR_MIN_WORDS = 80

# Punctuation density: AI text clusters around a moderate, consistent density.
# Deviation in either direction reads as more human.
PUNCT_TARGET = 0.05
PUNCT_TOLERANCE = 0.05

_SENTENCE_SPLIT = re.compile(r"[.!?]+")
_WORD = re.compile(r"[a-zA-Z']+")
_PUNCT = re.compile(r"[^\w\s]")


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _sentence_variance_score(text: str) -> float:
    """1.0 = uniform sentence lengths (AI-like), 0.0 = highly variable."""
    sentences = [s for s in _SENTENCE_SPLIT.split(text) if s.strip()]
    if len(sentences) < 2:
        # Not enough sentences to estimate variance; treat as neutral.
        return 0.5

    lengths = [len(_WORD.findall(s)) for s in sentences]
    mean = sum(lengths) / len(lengths)
    variance = sum((n - mean) ** 2 for n in lengths) / len(lengths)
    stddev = variance ** 0.5

    # Low stddev -> AI-like (high score); high stddev -> human (low score).
    return _clamp(1.0 - stddev / SENTENCE_STDDEV_HUMAN)


def _ttr_score(text: str) -> float:
    """1.0 = low vocabulary diversity (AI-like), 0.0 = high diversity."""
    words = [w.lower() for w in _WORD.findall(text)]
    if len(words) < TTR_MIN_WORDS:
        # Too short for TTR to be meaningful; abstain rather than vote "human".
        return 0.5

    ttr = len(set(words)) / len(words)
    # Map TTR from [TTR_AI, TTR_HUMAN] onto an AI-likeness score of [1.0, 0.0].
    return _clamp((TTR_HUMAN - ttr) / (TTR_HUMAN - TTR_AI))


def _punctuation_score(text: str) -> float:
    """1.0 = moderate/consistent density (AI-like), 0.0 = far from target."""
    total = len(text)
    if total == 0:
        return 0.5

    density = len(_PUNCT.findall(text)) / total
    # Deviation from the moderate target in either direction reads as human.
    deviation = abs(density - PUNCT_TARGET)
    return _clamp(1.0 - deviation / PUNCT_TOLERANCE)


def classify_with_stylometrics(text: str) -> float:
    """Return a structural AI-likeness score in [0.0, 1.0] for `text`.

    1.0 = structurally AI-like, 0.0 = structurally human-like. Computed as the
    average of the sentence-variance, type-token-ratio, and punctuation-density
    metrics.
    """
    scores = (
        _sentence_variance_score(text),
        _ttr_score(text),
        _punctuation_score(text),
    )
    return sum(scores) / len(scores)


if __name__ == "__main__":
    samples = [
        "hey so i finally tried that ramen place downtown lol. honestly? kinda "
        "mid. the broth was fine but nothing wrote home about. maybe i'll go "
        "back — dunno.",
        "It is important to note that effective time management encompasses a "
        "variety of strategies. Furthermore, prioritization plays a crucial "
        "role in achieving optimal productivity. Additionally, consistent "
        "planning contributes to sustained performance over time.",
    ]
    for s in samples:
        print(f"{classify_with_stylometrics(s):.3f}  <-  {s[:60]}...")
