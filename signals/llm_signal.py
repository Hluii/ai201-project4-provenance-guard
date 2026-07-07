"""Signal 1: LLM classification via Groq (llama-3.3-70b-versatile).

Asks the model to judge whether text reads as human- or AI-generated and
returns a float in [0.0, 1.0] where 1.0 = confident AI-generated.
"""

import json
import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = (
    "You are a text-provenance classifier. Assess whether the given text reads "
    "as human-written or AI-generated. Consider hedged phrasing (e.g. 'it is "
    "important to note'), overuse of transitional language, and unnaturally "
    "even sentence rhythm as AI indicators. Respond with ONLY a JSON object of "
    'the form {"score": <float 0.0-1.0>, "reasoning": "<brief>"} where 1.0 '
    "means you are highly confident the text is AI-generated and 0.0 means "
    "highly confident it is human-written."
)


def classify_with_llm(text: str) -> float:
    """Return an AI-generated confidence score in [0.0, 1.0] for `text`.

    1.0 = confident AI-generated, 0.0 = confident human-written. On any API or
    parsing failure, returns a neutral 0.5 so the pipeline can continue.
    """
    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        payload = json.loads(response.choices[0].message.content)
        score = float(payload["score"])
    except (KeyError, ValueError, TypeError, json.JSONDecodeError):
        return 0.5

    # Clamp defensively in case the model returns something out of range.
    return max(0.0, min(1.0, score))


if __name__ == "__main__":
    samples = [
        "hey so i finally tried that ramen place downtown lol. honestly? kinda "
        "mid. the broth was fine but nothing wrote home about.",
        "It is important to note that effective time management encompasses a "
        "variety of strategies. Furthermore, prioritization plays a crucial "
        "role in achieving optimal productivity across diverse contexts.",
    ]
    for s in samples:
        print(f"{classify_with_llm(s):.3f}  <-  {s[:60]}...")
