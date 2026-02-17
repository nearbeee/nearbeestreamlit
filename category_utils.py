# category_utils.py
FIXED_CATEGORIES = {
    "Cafe": ["cafe", "coffee", "coffee shop"],
    "Restaurant": ["restaurant", "dhaba", "eatery", "food"],
    "Grocery": ["grocery", "supermarket", "general store", "department store"],
    "Medical": ["medical", "pharmacy", "chemist", "drug"],
    "Salon": ["salon", "parlour", "beauty"],
    "Electronics": ["electronics", "mobile", "computer"],
    "Hardware": ["hardware"],
    "Hospital": ["hospital", "clinic"],
    "Gym": ["gym", "fitness"],
}

def normalize_category(raw_category: str) -> str:
    if not raw_category:
        return "Others"
    raw = raw_category.lower()
    for fixed, keywords in FIXED_CATEGORIES.items():
        for key in keywords:
            if key in raw:
                return fixed
    return "Others"