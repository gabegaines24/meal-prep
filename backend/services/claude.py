import base64
import json
import os

import anthropic

PROMPT = (
    "Look at this fridge photo carefully. "
    "Return ONLY a JSON array of ingredient names you can identify, "
    "e.g. [\"chicken breast\", \"broccoli\", \"eggs\"]. "
    "No explanation, no markdown, just the raw JSON array."
)


def _client() -> anthropic.Anthropic:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    return anthropic.Anthropic(api_key=key)


async def detect_ingredients(image_bytes: bytes, media_type: str = "image/jpeg") -> list[str]:
    """
    Send an image to Claude and return a list of detected ingredient names.

    Parameters
    ----------
    image_bytes : raw bytes of the uploaded image
    media_type  : MIME type, e.g. "image/jpeg" or "image/png"
    """
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    client = _client()

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64,
                        },
                    },
                    {"type": "text", "text": PROMPT},
                ],
            }
        ],
    )

    raw = message.content[0].text.strip()

    # Claude sometimes wraps the array in backtick fences; strip them
    if raw.startswith("```"):
        raw = raw.split("```")[1].lstrip("json").strip()

    try:
        ingredients = json.loads(raw)
        if isinstance(ingredients, list):
            return [str(i) for i in ingredients]
    except json.JSONDecodeError:
        pass

    # Fallback: treat each line as an ingredient
    return [line.strip().lstrip("-• ") for line in raw.splitlines() if line.strip()]
