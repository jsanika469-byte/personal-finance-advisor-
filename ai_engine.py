import os
import json
import google.generativeai as genai

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")


def build_finance_prompt(income, expenses, goals):
    """
    income: float
    expenses: list of dicts -> [{"category": "Food", "amount": 3000}, ...]
    goals: str (optional user-stated savings goal)
    """
    expenses_formatted = "\n".join(
        f"- {e['category']}: ₹{e['amount']}" for e in expenses
    )
    total_expenses = sum(e["amount"] for e in expenses)

    prompt = f"""
You are a certified personal finance advisor AI. Analyze the user's financial data below and respond ONLY in valid JSON — no extra text, no markdown formatting.

User Financial Data:
- Monthly Income: ₹{income}
- Total Expenses: ₹{total_expenses}
- Expense Breakdown:
{expenses_formatted}
- User's Stated Goal: {goals if goals else "Not specified"}

Your task:
1. Identify which expense categories are overspent relative to standard budgeting rules (e.g., 50/30/20 rule: 50% needs, 30% wants, 20% savings).
2. Generate a recommended monthly budget plan per category.
3. Provide 3-5 actionable, specific saving suggestions (not generic advice).
4. Calculate the projected monthly savings if the plan is followed.
5. Give a short overall financial health summary (2-3 sentences).

Respond strictly in this JSON structure:
{{
  "overspent_categories": ["category1", "category2"],
  "recommended_budget": {{
    "category_name": recommended_amount
  }},
  "saving_suggestions": [
    "suggestion 1",
    "suggestion 2"
  ],
  "projected_monthly_savings": amount,
  "financial_health_summary": "summary text"
}}
"""
    return prompt.strip()


def generate_budget_plan(income, expenses, goals):
    """Calls Gemini and returns a parsed dict. Raises ValueError on bad JSON."""
    prompt = build_finance_prompt(income, expenses, goals)
    response = model.generate_content(prompt)

    raw_text = response.text.strip()
    # Strip accidental markdown code fences if the model adds them
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        raw_text = raw_text.replace("json\n", "", 1).strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"AI response could not be parsed as JSON: {exc}")
