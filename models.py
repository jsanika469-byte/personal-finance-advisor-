from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


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
    month = db.Column(db.String(7), nullable=False)  # format: "2026-09"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Expense(db.Model):
    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    category = db.Column(db.String(80), nullable=False)  # e.g. Rent, Food, Transport
    amount = db.Column(db.Float, nullable=False)
    note = db.Column(db.String(255))
    month = db.Column(db.String(7), nullable=False)  # format: "2026-09"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {"category": self.category, "amount": self.amount}


class BudgetReport(db.Model):
    __tablename__ = "budget_reports"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    month = db.Column(db.String(7), nullable=False)
    overspent_categories = db.Column(db.Text)      # JSON string
    recommended_budget = db.Column(db.Text)         # JSON string
    saving_suggestions = db.Column(db.Text)          # JSON string
    projected_monthly_savings = db.Column(db.Float)
    financial_health_summary = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
