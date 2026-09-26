"""
Personal Finance Advisor Bot — single-file version
Stack: Python (Flask + SQLAlchemy + SQLite) + JavaScript (frontend)

Run:
    pip install Flask Flask-SQLAlchemy google-generativeai
    set GEMINI_API_KEY=your_key_here      (Windows)
    export GEMINI_API_KEY=your_key_here   (Mac/Linux)
    python app.py
"""

import os
import json
from datetime import datetime

from flask import Flask, request, jsonify, render_template_string
from flask_sqlalchemy import SQLAlchemy
import google.generativeai as genai

# ============================================================
# APP + DB CONFIG
# ============================================================

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(BASE_DIR, 'finance.db')}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
ai_model = genai.GenerativeModel("gemini-1.5-flash")


# ============================================================
# MODELS
# ============================================================

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    incomes = db.relationship("Income", backref="user", lazy=True, cascade="all, delete-orphan")
    expenses = db.relationship("Expense", backref="user", lazy=True, cascade="all, delete-orphan")
    reports = db.relationship("BudgetReport", backref="user", lazy=True, cascade="all, delete-orphan")


class Income(db.Model):
    __tablename__ = "incomes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    source = db.Column(db.String(120), default="Salary")
    month = db.Column(db.String(7), nullable=False)  # "2026-09"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Expense(db.Model):
    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    note = db.Column(db.String(255))
    month = db.Column(db.String(7), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {"category": self.category, "amount": self.amount}


class BudgetReport(db.Model):
    __tablename__ = "budget_reports"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    month = db.Column(db.String(7), nullable=False)
    overspent_categories = db.Column(db.Text)
    recommended_budget = db.Column(db.Text)
    saving_suggestions = db.Column(db.Text)
    projected_monthly_savings = db.Column(db.Float)
    financial_health_summary = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


with app.app_context():
    db.create_all()


# ============================================================
# AI ENGINE
# ============================================================

def build_finance_prompt(income, expenses, goals):
    expenses_formatted = "\n".join(
        f"- {e['category']}: ₹{e['amount']}" for e in expenses
    )
    total_expenses = sum(e["amount"] for e in expenses)

    return f"""
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
  "recommended_budget": {{"category_name": recommended_amount}},
  "saving_suggestions": ["suggestion 1", "suggestion 2"],
  "projected_monthly_savings": amount,
  "financial_health_summary": "summary text"
}}
""".strip()


def generate_budget_plan(income, expenses, goals):
    prompt = build_finance_prompt(income, expenses, goals)
    response = ai_model.generate_content(prompt)

    raw_text = response.text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        raw_text = raw_text.replace("json\n", "", 1).strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"AI response could not be parsed as JSON: {exc}")


# ============================================================
# FRONTEND (inline HTML + JS)
# ============================================================

INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Personal Finance Advisor Bot</title>
<style>
  body { font-family: Arial, sans-serif; max-width: 640px; margin: 40px auto; padding: 0 16px; color: #222; }
  h1 { font-size: 22px; }
  fieldset { margin-bottom: 20px; padding: 16px; border-radius: 8px; }
  label { display: block; margin: 8px 0 4px; font-size: 14px; }
  input { width: 100%; padding: 6px; box-sizing: border-box; }
  #expenseRows div { display: flex; gap: 8px; margin-bottom: 6px; }
  button { margin-top: 12px; padding: 8px 16px; cursor: pointer; }
  #results { margin-top: 24px; padding: 16px; border-radius: 8px; background: #f7f7f7; display: none; }
  #results h2 { font-size: 18px; }
  #suggestions li { margin-bottom: 4px; }
</style>
</head>
<body>

<h1>Personal Finance Advisor Bot</h1>

<fieldset>
  <legend>Setup</legend>
  <label>User ID</label>
  <input type="number" id="userId" value="1">
  <label>Month (YYYY-MM)</label>
  <input type="text" id="month" value="2026-09">
</fieldset>

<fieldset>
  <legend>Monthly Income</legend>
  <label>Amount (₹)</label>
  <input type="number" id="incomeAmount" placeholder="e.g. 60000">
  <button onclick="submitIncome()">Save Income</button>
</fieldset>

<fieldset>
  <legend>Expenses</legend>
  <div id="expenseRows">
    <div>
      <input type="text" class="expCategory" placeholder="Category (e.g. Rent)">
      <input type="number" class="expAmount" placeholder="Amount">
    </div>
  </div>
  <button onclick="addExpenseRow()">+ Add Category</button>
  <button onclick="submitExpenses()">Save Expenses</button>
</fieldset>

<fieldset>
  <legend>Goals (optional)</legend>
  <input type="text" id="goals" placeholder="e.g. Save ₹15,000/month for emergency fund">
</fieldset>

<button onclick="generateBudgetPlan()">Generate Budget Plan</button>

<div id="results">
  <h2>Financial Health Summary</h2>
  <p id="summary"></p>
  <p id="savings"></p>
  <h2>Saving Suggestions</h2>
  <ul id="suggestions"></ul>
  <h2>Overspent Categories</h2>
  <p id="overspent"></p>
  <h2>Recommended Budget</h2>
  <ul id="recommendedBudget"></ul>
</div>

<script>
function getUserId() { return parseInt(document.getElementById("userId").value, 10); }
function getMonth() { return document.getElementById("month").value; }

async function submitIncome() {
  const amount = parseFloat(document.getElementById("incomeAmount").value);
  if (!amount) return alert("Enter an income amount first.");
  const res = await fetch("/api/income", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: getUserId(), amount, month: getMonth() })
  });
  alert(res.ok ? "Income saved." : "Failed to save income.");
}

function addExpenseRow() {
  const container = document.getElementById("expenseRows");
  const row = document.createElement("div");
  row.innerHTML = `
    <input type="text" class="expCategory" placeholder="Category">
    <input type="number" class="expAmount" placeholder="Amount">
  `;
  container.appendChild(row);
}

async function submitExpenses() {
  const categories = document.querySelectorAll(".expCategory");
  const amounts = document.querySelectorAll(".expAmount");
  const userId = getUserId();
  const month = getMonth();
  const requests = [];

  for (let i = 0; i < categories.length; i++) {
    const category = categories[i].value.trim();
    const amount = parseFloat(amounts[i].value);
    if (!category || !amount) continue;
    requests.push(fetch("/api/expenses", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId, category, amount, month })
    }));
  }

  if (requests.length === 0) return alert("Add at least one expense.");
  await Promise.all(requests);
  alert("Expenses saved.");
}

async function generateBudgetPlan() {
  const userId = getUserId();
  const month = getMonth();
  const goals = document.getElementById("goals").value;

  const res = await fetch("/api/generate-budget", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, month, goals })
  });

  const data = await res.json();
  if (!res.ok) { alert(data.error || "Failed to generate budget plan."); return; }
  renderResults(data);
}

function renderResults(data) {
  document.getElementById("results").style.display = "block";
  document.getElementById("summary").innerText = data.financial_health_summary;
  document.getElementById("savings").innerText = `Projected Monthly Savings: ₹${data.projected_monthly_savings}`;

  const suggestionsList = document.getElementById("suggestions");
  suggestionsList.innerHTML = "";
  (data.saving_suggestions || []).forEach(s => {
    const li = document.createElement("li");
    li.textContent = s;
    suggestionsList.appendChild(li);
  });

  document.getElementById("overspent").innerText = (data.overspent_categories || []).join(", ") || "None";

  const budgetList = document.getElementById("recommendedBudget");
  budgetList.innerHTML = "";
  Object.entries(data.recommended_budget || {}).forEach(([category, amount]) => {
    const li = document.createElement("li");
    li.textContent = `${category}: ₹${amount}`;
    budgetList.appendChild(li);
  });
}
</script>

</body>
</html>
"""


# ============================================================
# ROUTES
# ============================================================

@app.route("/")
def index():
    return render_template_string(INDEX_HTML)


@app.route("/api/users", methods=["POST"])
def create_user():
    data = request.get_json()
    user = User(name=data["name"], email=data["email"])
    db.session.add(user)
    db.session.commit()
    return jsonify({"id": user.id, "name": user.name, "email": user.email}), 201


@app.route("/api/income", methods=["POST"])
def add_income():
    data = request.get_json()
    income = Income(
        user_id=data["user_id"],
        amount=data["amount"],
        source=data.get("source", "Salary"),
        month=data["month"],
    )
    db.session.add(income)
    db.session.commit()
    return jsonify({"id": income.id, "amount": income.amount, "month": income.month}), 201


@app.route("/api/expenses", methods=["POST"])
def add_expense():
    data = request.get_json()
    expense = Expense(
        user_id=data["user_id"],
        category=data["category"],
        amount=data["amount"],
        note=data.get("note", ""),
        month=data["month"],
    )
    db.session.add(expense)
    db.session.commit()
    return jsonify({"id": expense.id, "category": expense.category, "amount": expense.amount}), 201


@app.route("/api/expenses/<int:user_id>/<string:month>", methods=["GET"])
def get_expenses(user_id, month):
    expenses = Expense.query.filter_by(user_id=user_id, month=month).all()
    return jsonify([e.to_dict() for e in expenses])


@app.route("/api/generate-budget", methods=["POST"])
def generate_budget():
    data = request.get_json()
    user_id = data["user_id"]
    month = data["month"]
    goals = data.get("goals", "")

    total_income = sum(
        i.amount for i in Income.query.filter_by(user_id=user_id, month=month).all()
    )
    expenses = [
        e.to_dict() for e in Expense.query.filter_by(user_id=user_id, month=month).all()
    ]

    if total_income == 0 or not expenses:
        return jsonify({"error": "Missing income or expense data for this month"}), 400

    try:
        result = generate_budget_plan(total_income, expenses, goals)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 500

    report = BudgetReport(
        user_id=user_id,
        month=month,
        overspent_categories=json.dumps(result.get("overspent_categories", [])),
        recommended_budget=json.dumps(result.get("recommended_budget", {})),
        saving_suggestions=json.dumps(result.get("saving_suggestions", [])),
        projected_monthly_savings=result.get("projected_monthly_savings", 0),
        financial_health_summary=result.get("financial_health_summary", ""),
    )
    db.session.add(report)
    db.session.commit()

    return jsonify(result)


@app.route("/api/reports/<int:user_id>", methods=["GET"])
def get_reports(user_id):
    reports = (
        BudgetReport.query.filter_by(user_id=user_id)
        .order_by(BudgetReport.created_at.desc())
        .all()
    )
    return jsonify([
        {
            "month": r.month,
            "overspent_categories": json.loads(r.overspent_categories),
            "recommended_budget": json.loads(r.recommended_budget),
            "saving_suggestions": json.loads(r.saving_suggestions),
            "projected_monthly_savings": r.projected_monthly_savings,
            "financial_health_summary": r.financial_health_summary,
            "created_at": r.created_at.isoformat(),
        }
        for r in reports
    ])


if __name__ == "__main__":
    app.run(debug=True)
