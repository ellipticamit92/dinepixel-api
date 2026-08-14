"""
Prompts for menu extraction.
Version prompts so you can A/B test them later.
"""

EXTRACTION_PROMPT_V1 = """
You are a menu extraction specialist. Analyze this menu image and extract every food and drink item you can see.

For each item, return:
- name: exact name as written on the menu
- description: any description text near the item (or null)
- price: the price as a number only (e.g. 250, not "Rs. 250"). Null if not visible.
- currency: currency code, default "INR" for Indian menus, "USD" for US menus, etc.
- category: which section of the menu it belongs to (appetizer, main, dessert, beverage, side, breads, rice, etc.)
- ingredients: list of ingredients. If the menu lists them, use those. Otherwise, infer typical ingredients from the dish name (e.g. "Paneer Butter Masala" → ["paneer", "butter", "tomato", "cream", "spices"]).
- dietary_tags: list from: vegetarian, vegan, non-vegetarian, jain, gluten-free. Infer from dish name if not marked.
- allergens: list from: dairy, nuts, gluten, eggs, shellfish, soy. Infer conservatively.
- confidence: 0.0 to 1.0. Use lower values when the price is blurry, name is unclear, or you had to guess.
 
Also try to identify the restaurant name if visible.
 
CRITICAL RULES:
1. Only extract items you can actually see. Do NOT invent items.
2. If a price is unclear, set it to null and lower the confidence.
3. Keep original spelling of dish names, even if unusual.
4. For Indian menus, common categories: Starters, Main Course, Breads, Rice, Dal, Desserts, Beverages, Tandoor.
5. Return valid JSON matching the schema exactly.
 
Return ONLY the JSON object, no markdown fences, no explanation."""


CATEGORIZATION_PROMPT_V1 = """
You are a menu categorization specialist. You will be given a JSON list of menu items, each with a name and an optional description.

For EACH item, output exactly one line containing a single compact JSON object with these fields:
- name: the item name, copied exactly as given in the input
- category: the menu section it belongs to (e.g. Starters, Main Course, Breads, Rice, Dal, Desserts, Beverages, Tandoor, or another section name that fits). Infer the best category from the name and description.
- confidence: 0.0 to 1.0, how confident you are in the category assignment. Use a lower value when the name is ambiguous and you had to guess.

CRITICAL RULES:
1. Output ONE JSON object per line, in the SAME order as the input items.
2. Do NOT wrap the output in a JSON array or markdown fences.
3. Do NOT add any explanation, headers, or blank lines — only the JSON lines.
4. Every input item must produce exactly one output line.

Menu items:
{items_json}
"""
