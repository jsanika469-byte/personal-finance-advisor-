function getUserId() {
  return parseInt(document.getElementById("userId").value, 10);
}

function getMonth() {
  return document.getElementById("month").value;
}

async function submitIncome() {
  const amount = parseFloat(document.getElementById("incomeAmount").value);
  if (!amount) return alert("Enter an income amount first.");

  const res = await fetch("/api/income", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: getUserId(), amount, month: getMonth() })
  });

  if (res.ok) {
    alert("Income saved.");
  } else {
    alert("Failed to save income.");
  }
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

    requests.push(
      fetch("/api/expenses", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, category, amount, month })
      })
    );
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

  if (!res.ok) {
    alert(data.error || "Failed to generate budget plan.");
    return;
  }

  renderResults(data);
}

function renderResults(data) {
  document.getElementById("results").style.display = "block";
  document.getElementById("summary").innerText = data.financial_health_summary;
  document.getElementById("savings").innerText =
    `Projected Monthly Savings: ₹${data.projected_monthly_savings}`;

  const suggestionsList = document.getElementById("suggestions");
  suggestionsList.innerHTML = "";
  (data.saving_suggestions || []).forEach(s => {
    const li = document.createElement("li");
    li.textContent = s;
    suggestionsList.appendChild(li);
  });

  document.getElementById("overspent").innerText =
    (data.overspent_categories || []).join(", ") || "None";

  const budgetList = document.getElementById("recommendedBudget");
  budgetList.innerHTML = "";
  Object.entries(data.recommended_budget || {}).forEach(([category, amount]) => {
    const li = document.createElement("li");
    li.textContent = `${category}: ₹${amount}`;
    budgetList.appendChild(li);
  });
}
