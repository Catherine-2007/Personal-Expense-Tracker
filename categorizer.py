"""
Auto-categorization engine.

Lightweight, dependency-free classifier: merchant/note text is matched
against weighted keyword sets per category. This keeps the project runnable
with zero external ML downloads while remaining a genuine, extensible
classification component (swap in scikit-learn/transformers later without
changing the calling contract).
"""
from __future__ import annotations

import re

CATEGORY_KEYWORDS = {
    "Food": ["swiggy", "zomato", "restaurant", "cafe", "food", "dinner", "lunch",
             "breakfast", "delivery", "dominos", "pizza", "starbucks", "eat",
             "snack", "candy", "chocolate", "ice cream", "sweets", "biryani", "burger",
             "coffee", "chai", "tea", "bakery", "kitchen", "dhaba", "paneer", "naan",
             "thali", "sandwich", "juice", "mcdonald", "kfc", "subway", "barbeque"],
    "Shopping": ["amazon", "flipkart", "myntra", "mall", "shopping", "store",
                 "clothes", "shoes", "electronics", "lifestyle", "westside", "decathlon", "croma",
                 "ikea", "pantaloons", "zara"],
    "Transport": ["uber", "ola", "petrol", "fuel", "metro", "bus", "taxi",
                  "auto", "cab", "rapido", "parking", "toll", "irctc", "railway", "indian oil",
                  "bpcl", "hpcl", "shell", "flight", "indigo"],
    "Bills": ["electricity", "water bill", "recharge", "broadband", "wifi",
              "rent", "emi", "insurance", "subscription", "netflix", "spotify"],
    "Entertainment": ["movie", "cinema", "bookmyshow", "concert", "game",
                       "netflix", "prime video", "party", "pvr", "inox", "hotstar"],
    "Health": ["pharmacy", "hospital", "doctor", "medicine", "gym", "clinic", "medical", "chemist",
               "apollo", "medplus", "tablet", "diagnostic", "lab"],
    "Groceries": ["grocery", "supermarket", "bigbasket", "blinkit", "zepto",
                  "vegetables", "dmart", "milk", "bread", "atta", "rice", "dal", "eggs",
                  "fruits", "reliance fresh", "more retail", "big bazaar", "spencer"],
}

DEFAULT_CATEGORY = "Others"


def _matches(keyword: str, text: str) -> bool:
    """Short keywords ("ola", "bus", "emi", "dal") must match whole words so
    they don't fire inside longer words ("chocolate", "business")."""
    if len(keyword) <= 4:
        return re.search(rf"\b{re.escape(keyword)}\b", text) is not None
    return keyword in text


def categorize(merchant: str, note: str = "") -> str:
    text = f"{merchant} {note}".lower()
    best_category, best_score = DEFAULT_CATEGORY, 0
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if _matches(kw, text))
        if score > best_score:
            best_category, best_score = category, score
    return best_category
