# Provenance Guard — planning.md

## Architecture

### Submission Flow

```
POST /submit
    │
    ▼
Input validation + cleaning
(strip leading/trailing whitespace, reject empty text)
    │
    ▼
Signal 1: LLM Classification (Groq — llama-3.3-70b-versatile)
Prompt asks model to assess whether text reads as human or AI-generated.
Returns: llm_score (float 0.0–1.0, where 1.0 = confident AI)
    │
    ▼
Signal 2: Stylometric Heuristics (pure Python)
Computes 3 structural metrics:
  - Sentence length variance (low variance → more AI-like)
  - Type-token ratio / vocabulary diversity (high uniformity → more AI-like)
  - Punctuation density (AI text tends toward moderate, consistent density)
Returns: stylo_score (float 0.0–1.0, where 1.0 = confident AI)
    │
    ▼
Confidence Scoring
combined_score = (llm_score * 0.7) + (stylo_score * 0.3)
    │
    ▼
Transparency Label Generation
combined_score >= 0.75  → "Likely AI-generated"
combined_score <= 0.40  → "Likely human-written"
between 0.40 and 0.75  → "Uncertain"
    │
    ▼
Audit Log Entry written (JSON)
    │
    ▼
JSON response returned to caller
```

### Appeal Flow

```
POST /appeal
    │
    ▼
Validate content_id exists in audit log
    │
    ▼
Capture creator_reasoning
    │
    ▼
Update content status → "under_review"
    │
    ▼
Append appeal entry to audit log
    │
    ▼
Return confirmation response
```

---

## Detection Signals

### Signal 1: LLM Classification (Groq)

**What it measures:** Semantic and stylistic coherence holistically — whether the text "reads" like AI output. The LLM can detect things like hedged phrasing ("it is important to note"), overuse of transitional language, and unnaturally even sentence rhythm that are hard to quantify statistically.

**Output format:** A float between 0.0 and 1.0. The model is prompted to return only a JSON object with a `score` field and a `reasoning` field. Score of 1.0 = high confidence the text is AI-generated; 0.0 = high confidence it is human-written.

**Blind spots:** The LLM can be fooled by AI text that has been lightly edited by a human, or by formal human writing (academic papers, legal documents) that stylistically resembles AI output. It also has no access to structural/statistical properties — it reasons purely from the surface text.

---

### Signal 2: Stylometric Heuristics (pure Python)

**What it measures:** Three statistical properties of the text's structure:

1. **Sentence length variance** — AI text tends to have more uniform sentence lengths. Human writing is more variable (short punchy sentences mixed with long complex ones). Computed as the standard deviation of sentence token counts.

2. **Type-token ratio (TTR)** — vocabulary diversity. `unique_words / total_words`. AI text tends toward slightly lower TTR due to repetition of transitional phrases. Human informal writing tends higher.

3. **Punctuation density** — ratio of punctuation characters to total characters. AI text tends toward moderate, consistent density; human writing varies more (especially informal text with heavy use of dashes, ellipses, or almost none at all).

Each metric is normalized to a 0–1 scale and averaged into a single `stylo_score`.

**Output format:** A float between 0.0 and 1.0, where 1.0 = structurally AI-like.

**Blind spots:** Formal human writing (academic, legal, journalistic) will often score as AI-like because those genres naturally have uniform sentence length and controlled vocabulary. Short texts (under ~100 words) produce unreliable variance estimates. Poetry will almost always confuse this signal.

---

## Confidence Scoring and Uncertainty Representation

**Combination formula:**
```
combined_score = (llm_score * 0.7) + (stylo_score * 0.3)
```

The LLM signal is weighted higher because it captures semantic properties that stylometrics cannot. Stylometrics serves as a corroborating structural signal.

**What scores mean:**

| Score range | Interpretation |
|---|---|
| 0.75 – 1.00 | System is confident the text is AI-generated |
| 0.41 – 0.74 | System is uncertain — signals are mixed or text is ambiguous |
| 0.00 – 0.40 | System is confident the text is human-written |

**Design rationale:** The uncertain band is intentionally wide (0.41–0.74) because a false positive — labeling a human's work as AI — is a more serious error than a false negative on a writing platform. When in doubt, the system should say so rather than confidently misclassify.

A score of 0.51 and a score of 0.95 should produce meaningfully different labels and different label language. A 0.51 is uncertain; a 0.95 is a strong positive classification.

---

## Transparency Label Variants

All three variants are designed to be readable by a non-technical user.

**High-confidence AI (combined_score >= 0.75):**
```
AI-Assisted Content Detected
Our analysis found strong indicators that this content was likely generated
or substantially written by an AI tool. Confidence: [XX]%.
If you believe this is incorrect, you can submit an appeal below.
```

**Uncertain (0.40 < combined_score < 0.75):**
```
Attribution Unclear
Our analysis found mixed signals for this content. We are not confident
whether this was written by a human or generated by an AI tool. Confidence: [XX]%.
If you are the creator, you can submit an appeal to provide more context.
```

**High-confidence human (combined_score <= 0.40):**
```
Human-Written Content
Our analysis found strong indicators that this content was written by a human.
Confidence: [XX]%. Attribution signals are recorded for platform transparency.
```

---

## Appeals Workflow

**Who can submit:** Any creator with a valid `content_id` from a prior `/submit` response.

**Required fields:**
- `content_id` (string) — the ID returned by `/submit`
- `creator_reasoning` (string) — the creator's explanation of why the classification is wrong

**What the system does on appeal:**
1. Looks up the original audit log entry by `content_id`
2. Updates the entry's `status` field from `"classified"` to `"under_review"`
3. Appends an appeal record to the audit log with: `content_id`, `timestamp`, `creator_reasoning`, `original_attribution`, `original_confidence`
4. Returns a confirmation JSON response with the updated status

**What a human reviewer would see:** The audit log entry for the content, including both signal scores, the original classification, the confidence score, and the creator's written reasoning. No automated re-classification is performed.

---

## Anticipated Edge Cases

1. **Formal human writing misclassified as AI:** An academic essay or legal brief written by a human will have low sentence length variance, controlled vocabulary, and measured punctuation — all of which the stylometric signal interprets as AI-like. The LLM signal may also score it high if the prose is particularly polished. This is the most likely false positive scenario.

2. **Short text (under 80 words):** Stylometric metrics like sentence length variance are statistically unreliable with very few sentences. A haiku or a two-sentence bio will produce a near-meaningless `stylo_score`. The system should still run but should be understood to be operating with low signal quality for short content.

3. **Lightly edited AI output:** A creator who generates text with an AI tool and then edits it moderately may land in the uncertain range rather than the high-confidence AI range. The system is not designed to detect this precisely — it can only flag probability, not intent.

4. **Non-native English writing:** Formal, careful writing by non-native English speakers may resemble AI output stylistically (consistent structure, conservative vocabulary) and produce a higher confidence score than warranted. This is a known limitation of both signals.

---

## API Surface

| Endpoint | Method | Input | Output |
|---|---|---|---|
| `/submit` | POST | `{text, creator_id}` | `{content_id, attribution, confidence, label}` |
| `/appeal` | POST | `{content_id, creator_reasoning}` | `{status, message}` |
| `/log` | GET | — | `{entries: [...]}` |

---

## AI Tool Plan

### M3 — Submission endpoint + Signal 1
**Spec sections to provide:** Detection Signals (Signal 1 only) + Architecture diagram (submission flow)
**What to ask for:** Flask app skeleton with `POST /submit` route stub + Groq LLM signal function that returns a float score
**How to verify:** Test the function in isolation with 2–3 text inputs before wiring into the endpoint. Check that the return type is a float 0–1, not a string or binary flag.

### M4 — Signal 2 + Confidence Scoring
**Spec sections to provide:** Detection Signals (Signal 2) + Confidence Scoring section + Architecture diagram
**What to ask for:** Stylometric heuristics function (sentence length variance, TTR, punctuation density) + scoring logic that combines both signals using the 0.7/0.3 weighted formula
**How to verify:** Run the 4 sample inputs from the spec. Clearly AI text should score above 0.75. Clearly human informal text should score below 0.40. If either doesn't hold, print both signal scores separately to diagnose which signal is misbehaving.

### M5 — Production layer
**Spec sections to provide:** Transparency Label Variants + Appeals Workflow + Architecture diagram (both flows)
**What to ask for:** Label generation function that maps confidence score to the correct label text + `POST /appeal` endpoint
**How to verify:** Test that all three label variants are reachable by submitting inputs that produce different confidence levels. Test the appeal endpoint with a real `content_id` and verify the status updates to `"under_review"` in `GET /log`.