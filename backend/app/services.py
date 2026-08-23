import json
import re
from collections import Counter
from dataclasses import dataclass

import httpx
from sqlmodel import Session, select

from .models import HistoryEvent, ShoppingItem, Suggestion
from .settings import get_settings

CATEGORY_KEYWORDS = {
    "Produce": {"apple", "apples", "banana", "bananas", "orange", "oranges", "tomato", "tomatoes", "potato", "potatoes", "onion", "onions", "avocado", "spinach", "lettuce", "mango", "grapes", "strawberry", "carrot", "carrots", "cilantro"},
    "Dairy & Eggs": {"milk", "cheese", "yogurt", "butter", "eggs", "cream"},
    "Bakery": {"bread", "bagel", "bagels", "tortilla", "tortillas", "bun", "buns"},
    "Pantry": {"rice", "pasta", "flour", "sugar", "oil", "beans", "cereal", "coffee", "tea", "salt", "pepper"},
    "Beverages": {"water", "juice", "soda", "coffee", "tea", "sparkling water"},
    "Snacks": {"chips", "cookies", "chocolate", "nuts", "popcorn", "crackers"},
    "Personal Care": {"toothpaste", "shampoo", "soap", "deodorant", "tissue", "toilet paper"},
    "Household": {"detergent", "cleaner", "trash bags", "sponges"},
}

SUBSTITUTES = {
    "milk": ("almond milk", "Try a dairy-free alternative."),
    "bread": ("whole-wheat bread", "A more filling everyday option."),
    "butter": ("olive-oil spread", "A lighter alternative."),
    "chips": ("popcorn", "A crunchy pantry swap."),
}


def categorise(name: str) -> str:
    text = name.lower()
    for category, words in CATEGORY_KEYWORDS.items():
        if any(word in text for word in words):
            return category
    return "Other"


@dataclass
class ParsedCommand:
    intent: str
    name: str | None = None
    quantity: float = 1
    unit: str | None = None
    brand: str | None = None
    max_price: float | None = None


def _clean_name(value: str) -> str:
    value = re.sub(r"\b(to my (shopping )?list|from my (shopping )?list|please|kharidari suchi mein|meri list mein|se hatao)\b", "", value, flags=re.I)
    value = re.sub(r"^\s*(of|ka|ki|ke)\s+", "", value, flags=re.I)
    value = re.sub(r"\s+", " ", value).strip(" .,!?\"")
    return value.title() if value else ""


def parse_command(transcript: str, language: str = "en-US") -> ParsedCommand:
    text = transcript.strip().lower()
    # Supports common English and Hindi/Hinglish command stems.
    if re.search(r"\b(remove|delete|take off|hatao|nikal)\b", text):
        name = re.sub(r"^.*?\b(remove|delete|take off|hatao|nikal)\b", "", transcript, flags=re.I)
        return ParsedCommand("remove", _clean_name(name))
    if re.search(r"\b(clear|empty|saaf karo)\b.*\b(list|suchi)\b", text):
        return ParsedCommand("clear")
    if re.search(r"\b(find|search|look for|dhoondo|dhundo)\b", text):
        max_price_match = re.search(r"(?:under|below|less than|se kam)\s*[$₹€]?\s*(\d+(?:\.\d+)?)", text)
        brand_match = re.search(r"brand\s+([\w-]+)", text)
        name = re.sub(r"^.*?\b(find|search|look for|dhoondo|dhundo)\b", "", transcript, flags=re.I)
        name = re.sub(r"\b(under|below|less than|se kam)\s*[$₹€]?\s*\d+(?:\.\d+)?", "", name, flags=re.I)
        return ParsedCommand("search", _clean_name(name), brand=brand_match.group(1).title() if brand_match else None, max_price=float(max_price_match.group(1)) if max_price_match else None)
    if re.search(r"\b(show|what('| i)s on|read|list|dikhाओ|dikhao)\b.*\b(list|suchi)\b", text):
        return ParsedCommand("list")

    name = re.sub(r"^.*?\b(add|need|want|buy|put|jodo|jod|chahiye)\b", "", transcript, flags=re.I)
    quantity_match = re.search(r"\b(\d+(?:\.\d+)?)\s*(bottles?|packs?|bags?|loaves?|kg|g|lit(?:er|re)?s?|pcs?|pieces?)?\b", name, flags=re.I)
    quantity = float(quantity_match.group(1)) if quantity_match else 1
    unit = quantity_match.group(2).rstrip("s") if quantity_match and quantity_match.group(2) else None
    if quantity_match:
        name = name[:quantity_match.start()] + name[quantity_match.end():]
    return ParsedCommand("add", _clean_name(name), quantity, unit)


async def groq_parse(transcript: str, language: str) -> ParsedCommand | None:
    settings = get_settings()
    if not settings.groq_api_key:
        return None
    prompt = f'''Extract a shopping-list command from this multilingual transcript: {transcript!r}. Language hint: {language}.
Return ONLY JSON: {{"intent":"add|remove|search|list|clear","name":"string or null","quantity":number,"unit":"string or null","brand":"string or null","max_price":number or null}}. Do not invent values.'''
    try:
        async with httpx.AsyncClient(timeout=4) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                json={"model": "llama-3.1-8b-instant", "temperature": 0, "messages": [{"role": "user", "content": prompt}], "response_format": {"type": "json_object"}},
            )
            response.raise_for_status()
            data = json.loads(response.json()["choices"][0]["message"]["content"])
            if data.get("intent") in {"add", "remove", "search", "list", "clear"}:
                return ParsedCommand(**data)
    except (httpx.HTTPError, KeyError, ValueError, TypeError):
        return None
    return None


def seed_history(session: Session, user_id: int | None = None) -> None:
    if session.exec(select(HistoryEvent).where(HistoryEvent.user_id == user_id)).first():
        return
    for name in ("Milk", "Bread", "Eggs", "Bananas", "Milk", "Coffee", "Bread", "Tomatoes"):
        session.add(HistoryEvent(item_name=name, user_id=user_id))
    session.commit()


def build_suggestions(session: Session, user_id: int) -> list[Suggestion]:
    history = session.exec(select(HistoryEvent).where(HistoryEvent.user_id == user_id)).all()
    counts = Counter(event.item_name for event in history)
    list_names = {item.name.lower() for item in session.exec(select(ShoppingItem).where(ShoppingItem.user_id == user_id)).all()}
    suggestions: list[Suggestion] = []
    for name, _ in counts.most_common(4):
        if name.lower() not in list_names:
            suggestions.append(Suggestion(name=name, reason="Often bought", category=categorise(name)))
    seasonal = [Suggestion(name="Mangoes", reason="In season now", category="Produce"), Suggestion(name="Iced tea", reason="Warm-weather pick", category="Beverages")]
    for suggestion in seasonal:
        if suggestion.name.lower() not in list_names:
            suggestions.append(suggestion)
    return suggestions[:5]
