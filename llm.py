"""
llm.py
------
Thin wrapper around the Groq API (OpenAI-compatible) calling
Llama 3 70B to answer questions about a scraped product, grounded
in the actual scraped page data so it doesn't hallucinate specs.
"""

import os
from groq import Groq

MODEL = "llama3-70b-8192"

SYSTEM_PROMPT = """You are KnowBeforeBuy, a shopping assistant embedded in a \
browser extension. You help someone decide whether to buy a product they are \
currently viewing.

Rules:
- Base your answers ONLY on the product data provided below. Do not invent \
specs, prices, or reviews that aren't in the data.
- If the data needed to answer isn't available, say so plainly rather than \
guessing.
- Be concise and direct - this is a popup window, not an essay. 2-4 sentences \
unless the user asks for more detail.
- If asked for a recommendation, weigh price, rating, and review count \
explicitly rather than giving a generic "it depends."
"""


def _build_product_context(product: dict) -> str:
    lines = [f"Product URL: {product.get('url')}"]
    lines.append(f"Title: {product.get('title') or 'Not available'}")
    lines.append(f"Price: {product.get('price') or 'Not available'}")
    lines.append(f"Rating: {product.get('rating') or 'Not available'}")
    lines.append(f"Review count: {product.get('review_count') or 'Not available'}")

    bullets = product.get("bullets")
    if bullets:
        lines.append("Feature bullets:")
        lines.extend(f"  - {b}" for b in bullets)
    else:
        lines.append("Feature bullets: Not available")

    lines.append(f"Description: {product.get('description') or 'Not available'}")
    return "\n".join(lines)


def ask_about_product(product: dict, question: str, history: list[dict] | None = None) -> str:
    """
    product: dict from scraper.scrape_amazon_product()
    question: the user's current question
    history: optional prior turns as [{"role": "user"/"assistant", "content": str}, ...]
              so follow-up questions keep context within the popup session
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Get a free key at https://console.groq.com/keys "
            "and put it in backend/.env"
        )

    client = Groq(api_key=api_key)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + _build_product_context(product)}
    ]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": question})

    completion = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.3,
        max_tokens=400,
    )
    return completion.choices[0].message.content
