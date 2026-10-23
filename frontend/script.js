// ============================================================
// FINANCEFLOW
// AI PERSONAL FINANCE MANAGEMENT SYSTEM
// ============================================================

const API_URL = "http://127.0.0.1:5000";


// ============================================================
// GLOBAL STATE
// ============================================================

let monthlyChart = null;
let categoryChart = null;

let analyticsMonthlyData = [];

let selectedAnalyticsMonth = "";

let trendMode = "monthly";

let currentUser = null;

let allTransactions = [];

let showingAllTransactions = false;
let editingTransactionId = null;


// ============================================================
// DOM HELPER
// ============================================================

function getElement(id) {
    return document.getElementById(id);
}


// ============================================================
// API
// ============================================================

async function apiRequest(endpoint, options = {}) {

    const config = {
        credentials: "include",
        ...options,

        headers: {
            ...(options.body instanceof FormData
                ? {}
                : {
                    "Content-Type": "application/json"
                }),

            ...(options.headers || {})
        }
    };

    let response;
    try {
        response = await fetch(API_URL + endpoint, config);
    } catch (error) {
        throw new Error(
            `Cannot connect to FinanceFlow backend at ${API_URL}. Start the backend with python backend\\app.py and open the frontend at http://127.0.0.1:8000.`
        );
    }

    let data = {};

    try {
        data = await response.json();
    } catch {
        data = {};
    }

    if (!response.ok) {

        throw new Error(
            data.error ||
            data.message ||
            `Request failed: ${response.status}`
        );
    }

    return data;
}


// ============================================================
// FORMATTERS
// ============================================================

function formatCurrency(value) {

    const number = Number(value || 0);

    return "₹" +
        number.toLocaleString(
            "en-IN",
            {
                minimumFractionDigits: 0,
                maximumFractionDigits: 2
            }
        );
}


function formatMonthLabel(value) {

    if (!value) {
        return "";
    }

    const parts = value.split("-");

    if (parts.length !== 2) {
        return value;
    }

    const date =
        new Date(
            Number(parts[0]),
            Number(parts[1]) - 1,
            1
        );

    if (isNaN(date.getTime())) {
        return value;
    }

    return date.toLocaleDateString(
        "en-IN",
        {
            month: "short",
            year: "numeric"
        }
    );
}


function formatDayLabel(value) {

    if (!value) {
        return "";
    }

    const date =
        new Date(
            value + "T00:00:00"
        );

    if (isNaN(date.getTime())) {
        return value;
    }

    return date.toLocaleDateString(
        "en-IN",
        {
            day: "numeric",
            month: "short"
        }
    );
}


// ============================================================
// AUTH UI
// ============================================================

function showLogin() {

    getElement("auth-section")
        ?.classList.remove("hidden");

    getElement("dashboard-section")
        ?.classList.add("hidden");
}


function showDashboard() {

    getElement("auth-section")
        ?.classList.add("hidden");

    getElement("dashboard-section")
        ?.classList.remove("hidden");
}


function showRegisterForm() {

    getElement("login-form")
        ?.classList.add("hidden");

    getElement("register-form")
        ?.classList.remove("hidden");
}


function showLoginForm() {

    getElement("register-form")
        ?.classList.add("hidden");

    getElement("login-form")
        ?.classList.remove("hidden");
}


// ============================================================
// LOGIN
// ============================================================

async function handleLogin(event) {

    event.preventDefault();

    const identifier =
        getElement("login-email").value.trim();

    const password =
        getElement("login-password").value;

    if (!identifier || !password) {

        alert(
            "Please enter your username or email and password."
        );

        return;
    }

    try {

        const data =
            await apiRequest(
                "/login",
                {
                    method: "POST",

                    body: JSON.stringify({
                        identifier,
                        password
                    })
                }
            );

        currentUser =
            data.user;

        showDashboard();

        await loadDashboard();

    } catch (error) {

        alert(error.message);
    }
}


// ============================================================
// REGISTER
// ============================================================

async function handleRegister(event) {

    event.preventDefault();

    const name =
        getElement("register-name")
            .value
            .trim();

    const email =
        getElement("register-email")
            .value
            .trim();

    const password =
        getElement("register-password")
            .value;

    if (!name || !email || !password) {

        alert(
            "Please fill all fields."
        );

        return;
    }

    try {

        await apiRequest(
            "/register",
            {
                method: "POST",

                body: JSON.stringify({
                    name,
                    email,
                    password
                })
            }
        );

        alert(
            "Registration successful. Please login."
        );

        getElement(
            "login-email"
        ).value = email;

        showLoginForm();

    } catch (error) {

        alert(error.message);
    }
}


// ============================================================
// LOGOUT
// ============================================================

async function handleLogout() {

    try {

        await apiRequest(
            "/logout",
            {
                method: "POST"
            }
        );

        currentUser = null;

        if (monthlyChart) {

            monthlyChart.destroy();

            monthlyChart = null;
        }

        if (categoryChart) {

            categoryChart.destroy();

            categoryChart = null;
        }

        showLogin();

    } catch (error) {

        console.error(
            "Logout error:",
            error
        );
    }
}


// ============================================================
// PROFILE
// ============================================================

async function loadProfile() {

    try {

        const data =
            await apiRequest("/me");

        currentUser =
            data.user;

        const name =
            currentUser.name || "User";

        const email =
            currentUser.email || "";

        getElement("user-name").textContent =
            name;

        getElement("header-user-name").textContent =
            name;

        getElement("user-email").textContent =
            email;

        getElement("user-initial").textContent =
            name.charAt(0).toUpperCase();

    } catch (error) {

        console.error(
            "Profile error:",
            error
        );
    }
}


// ============================================================
// DASHBOARD
// ============================================================

async function loadDashboard() {

    await loadProfile();

    await Promise.allSettled([
        loadSummary(),
        loadTransactions(),
        loadAnalytics(),
        loadAnomalies(),
        loadPrediction(),
        loadAvoidableSpending(),
        loadMonthlyComparison(),
        loadBudgets(),
        loadSavingsGoals()
    ]);
}


// ============================================================
// SUMMARY
// ============================================================

async function loadSummary() {

    try {

        const data =
            await apiRequest("/summary");

        getElement("balance").textContent =
            formatCurrency(
                data.balance
            );

        getElement("total-income").textContent =
            formatCurrency(
                data.total_income
            );

        getElement("total-expense").textContent =
            formatCurrency(
                data.total_expense
            );

        getElement("transaction-count").textContent =
            Number(
                data.transaction_count || 0
            ).toLocaleString("en-IN");

    } catch (error) {

        console.error(
            "Summary error:",
            error
        );
    }
}


// ============================================================
// TRANSACTION MODAL
// ============================================================

function openTransactionModal() {

    editingTransactionId = null;
    getElement("transaction-form")?.reset();
    getElement("transaction-modal-title").textContent = "Add Transaction";
    getElement("transaction-modal-eyebrow").textContent = "NEW TRANSACTION";
    getElement("save-transaction-button").textContent = "Add Transaction";

    const modal =
        getElement(
            "transaction-modal"
        );

    if (!modal) {
        return;
    }

    modal.classList.remove(
        "hidden"
    );

    const dateInput =
        getElement(
            "transaction-date"
        );

    if (
        dateInput &&
        !dateInput.value
    ) {

        dateInput.value =
            new Date()
                .toISOString()
                .split("T")[0];
    }
}


function closeTransactionModal() {

    const modal =
        getElement(
            "transaction-modal"
        );

    if (!modal) {
        return;
    }

    modal.classList.add(
        "hidden"
    );
}


async function handleAddTransaction(event) {

    event.preventDefault();

    const date =
        getElement(
            "transaction-date"
        ).value;

    const type =
        getElement(
            "transaction-type"
        ).value;

    const amount =
        getElement(
            "transaction-amount"
        ).value;

    const category =
        getElement(
            "transaction-category"
        ).value;

    const description =
        getElement(
            "transaction-description"
        ).value;

    if (
        !date ||
        !type ||
        !amount ||
        !category
    ) {

        alert(
            "Please fill all required fields."
        );

        return;
    }

    try {

        const payload = {
            date,
            amount: Number(amount),
            category,
            description,
            type
        };
        const isEditing = editingTransactionId !== null;
        await apiRequest(
            isEditing
                ? `/transactions/${editingTransactionId}`
                : "/transactions",
            {
                method: isEditing ? "PUT" : "POST",
                body: JSON.stringify(payload)
            }
        );

        alert(
            isEditing
                ? "Transaction updated successfully."
                : "Transaction added successfully."
        );

        getElement(
            "transaction-form"
        ).reset();
        editingTransactionId = null;

        closeTransactionModal();

        await loadDashboard();

    } catch (error) {

        alert(error.message);
    }
}



// ============================================================
// EDIT AND DELETE TRANSACTIONS
// ============================================================

function openEditTransaction(transactionId) {
    const transaction = allTransactions.find(
        item => Number(item.id) === Number(transactionId)
    );
    if (!transaction) {
        alert("This transaction could not be found. Refresh and try again.");
        return;
    }

    editingTransactionId = Number(transaction.id);
    getElement("transaction-date").value = String(transaction.Date || "").slice(0, 10);
    getElement("transaction-type").value = transaction.Type || "Expense";
    getElement("transaction-amount").value = Number(transaction.Amount || 0);
    const categorySelect = getElement("transaction-category");
    const transactionCategory = transaction.Category || "";
    if (transactionCategory && !Array.from(categorySelect.options).some(option => option.value === transactionCategory || option.textContent.trim() === transactionCategory)) {
        const categoryOption = document.createElement("option");
        categoryOption.value = transactionCategory;
        categoryOption.textContent = transactionCategory;
        categorySelect.appendChild(categoryOption);
    }
    categorySelect.value = transactionCategory;
    getElement("transaction-description").value = transaction.Description || "";
    getElement("transaction-modal-title").textContent = "Edit Transaction";
    getElement("transaction-modal-eyebrow").textContent = "UPDATE TRANSACTION";
    getElement("save-transaction-button").textContent = "Save Changes";
    getElement("transaction-modal").classList.remove("hidden");
}

async function deleteTransaction(transactionId) {
    const transaction = allTransactions.find(
        item => Number(item.id) === Number(transactionId)
    );
    if (!transaction) {
        alert("This transaction could not be found. Refresh and try again.");
        return;
    }

    const description = transaction.Description || transaction.Category || "this transaction";
    if (!confirm(`Delete "${description}" (${formatCurrency(Number(transaction.Amount || 0))})? This cannot be undone.`)) {
        return;
    }

    try {
        await apiRequest(`/transactions/${Number(transactionId)}`, {
            method: "DELETE"
        });
        alert("Transaction deleted successfully.");
        await loadDashboard();
    } catch (error) {
        alert(error.message || "Unable to delete transaction.");
    }
}

function setupReportDateDefaults() {
    const today = new Date();
    const toLocalISO = value => {
        const y = value.getFullYear();
        const m = String(value.getMonth() + 1).padStart(2, "0");
        const d = String(value.getDate()).padStart(2, "0");
        return `${y}-${m}-${d}`;
    };
    const end = toLocalISO(today);
    const startDate = new Date(today);
    startDate.setDate(startDate.getDate() - 29);
    getElement("report-start-date").value = toLocalISO(startDate);
    getElement("report-end-date").value = end;
}

function setReportRange(range) {
    const today = new Date();
    const toLocalISO = value => {
        const y = value.getFullYear();
        const m = String(value.getMonth() + 1).padStart(2, "0");
        const d = String(value.getDate()).padStart(2, "0");
        return `${y}-${m}-${d}`;
    };
    let start = new Date(today);
    let end = new Date(today);

    if (range === "7" || range === "30") {
        start.setDate(start.getDate() - (Number(range) - 1));
    } else if (range === "month") {
        start = new Date(today.getFullYear(), today.getMonth(), 1);
    }
    getElement("report-start-date").value = toLocalISO(start);
    getElement("report-end-date").value = toLocalISO(end);
}

async function downloadFinancialReport() {
    const start = getElement("report-start-date").value;
    const end = getElement("report-end-date").value;
    if (!start || !end) {
        alert("Please select both report dates.");
        return;
    }
    if (start > end) {
        alert("Start date must be on or before end date.");
        return;
    }

    const button = getElement("download-report-button");
    const originalLabel = button.textContent;
    button.disabled = true;
    button.textContent = "Preparing PDF...";
    try {
        const response = await fetch(
            `${API_URL}/reports/financial.pdf?start_date=${encodeURIComponent(start)}&end_date=${encodeURIComponent(end)}`,
            { method: "GET", credentials: "include" }
        );
        if (!response.ok) {
            let message = "Unable to generate PDF report.";
            try {
                const data = await response.json();
                message = data.error || message;
            } catch (_) {}
            throw new Error(message);
        }
        const blob = await response.blob();
        const objectUrl = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = objectUrl;
        link.download = `FinanceFlow_Report_${start}_to_${end}.pdf`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(objectUrl);
    } catch (error) {
        alert(error.message || "Unable to download the report. Check that the backend is running.");
    } finally {
        button.disabled = false;
        button.textContent = originalLabel;
    }
}


// ============================================================
// CSV IMPORT
// ============================================================

async function handleCSVImport(event) {

    event.preventDefault();

    const fileInput =
        getElement("csv-file");

    if (
        !fileInput ||
        !fileInput.files.length
    ) {

        alert(
            "Please select a CSV file."
        );

        return;
    }

    const formData =
        new FormData();

    formData.append(
        "file",
        fileInput.files[0]
    );

    try {

        const response =
            await fetch(
                API_URL +
                "/transactions/import-csv",
                {
                    method: "POST",
                    credentials: "include",
                    body: formData
                }
            );

        const data =
            await response.json();

        if (!response.ok) {

            throw new Error(
                data.error ||
                "CSV import failed."
            );
        }

        alert(
            "CSV imported successfully.\n\n" +
            "Inserted: " +
            data.inserted_count +
            "\nSkipped: " +
            data.skipped_rows
        );

        fileInput.value = "";

        await loadDashboard();

    } catch (error) {

        alert(error.message);
    }
}


// ============================================================
// TRANSACTIONS
// ============================================================

async function loadTransactions() {

    try {

        const data =
            await apiRequest(
                "/transactions"
            );

        allTransactions =
            data.transactions || [];

        showingAllTransactions = false;
        populateTransactionCategoryFilter();
        renderTransactions();

    } catch (error) {

        console.error(
            "Transactions error:",
            error
        );
    }
}


function getFilteredTransactions() {
    const query = (getElement("transaction-search-input")?.value || "").trim().toLowerCase();
    const type = getElement("transaction-type-filter")?.value || "";
    const category = getElement("transaction-category-filter")?.value || "";
    const startDate = getElement("transaction-start-filter")?.value || "";
    const endDate = getElement("transaction-end-filter")?.value || "";

    return allTransactions.filter(transaction => {
        const date = String(transaction.Date || "").slice(0, 10);
        const transactionCategory = String(transaction.Category || "");
        const description = String(transaction.Description || "");
        const amount = String(Number(transaction.Amount || 0));
        const transactionType = String(transaction.Type || "");
        const searchable = `${description} ${transactionCategory} ${amount} ${transactionType} ${date}`.toLowerCase();

        if (query && !searchable.includes(query)) return false;
        if (type && transactionType.toLowerCase() !== type.toLowerCase()) return false;
        if (category && transactionCategory !== category) return false;
        if (startDate && date < startDate) return false;
        if (endDate && date > endDate) return false;
        return true;
    });
}

function populateTransactionCategoryFilter() {
    const select = getElement("transaction-category-filter");
    if (!select) return;

    const selected = select.value;
    const categories = [...new Set(
        allTransactions
            .map(transaction => String(transaction.Category || "").trim())
            .filter(Boolean)
    )].sort((a, b) => a.localeCompare(b));

    select.innerHTML = '<option value="">All categories</option>';
    categories.forEach(category => {
        const option = document.createElement("option");
        option.value = category;
        option.textContent = category;
        select.appendChild(option);
    });
    if (categories.includes(selected)) select.value = selected;
}

function resetTransactionFilters() {
    ["transaction-search-input", "transaction-type-filter", "transaction-category-filter", "transaction-start-filter", "transaction-end-filter"]
        .forEach(id => {
            const element = getElement(id);
            if (element) element.value = "";
        });
    showingAllTransactions = false;
    renderTransactions();
}

function renderTransactions() {
    const tbody = getElement("transactions-body");
    const toggleButton = getElement("toggle-transactions-button");
    if (!tbody) return;

    tbody.innerHTML = "";
    const filteredTransactions = getFilteredTransactions();
    const countLabel = getElement("transaction-search-count");
    const totalsLabel = getElement("transaction-search-totals");

    const incomeTotal = filteredTransactions
        .filter(item => String(item.Type || "").toLowerCase() === "income")
        .reduce((sum, item) => sum + Number(item.Amount || 0), 0);
    const expenseTotal = filteredTransactions
        .filter(item => String(item.Type || "").toLowerCase() === "expense")
        .reduce((sum, item) => sum + Number(item.Amount || 0), 0);

    if (countLabel) {
        countLabel.textContent = `${filteredTransactions.length} matching transaction${filteredTransactions.length === 1 ? "" : "s"}`;
    }
    if (totalsLabel) {
        totalsLabel.textContent = `Income: ${formatCurrency(incomeTotal)}  ·  Expenses: ${formatCurrency(expenseTotal)}`;
    }

    if (!filteredTransactions.length) {
        const hasFilters = Boolean(
            (getElement("transaction-search-input")?.value || "").trim() ||
            getElement("transaction-type-filter")?.value ||
            getElement("transaction-category-filter")?.value ||
            getElement("transaction-start-filter")?.value ||
            getElement("transaction-end-filter")?.value
        );
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="table-empty">
                    ${hasFilters ? "No transactions match your search or filters." : "No transactions found."}
                </td>
            </tr>
        `;
        if (toggleButton) toggleButton.classList.add("hidden");
        return;
    }

    const visibleTransactions = showingAllTransactions || filteredTransactions.length <= 5
        ? filteredTransactions
        : filteredTransactions.slice(0, 5);

    visibleTransactions.forEach(transaction => {
        const row = document.createElement("tr");
        const date = transaction.Date || "";
        const amount = Number(transaction.Amount || 0);
        const category = transaction.Category || "";
        const description = transaction.Description || "";
        const type = transaction.Type || "";

        row.innerHTML = `
            <td>${escapeHTML(date)}</td>
            <td>${escapeHTML(category)}</td>
            <td>${escapeHTML(description)}</td>
            <td>${formatCurrency(amount)}</td>
            <td>${escapeHTML(type)}</td>
            <td>${Number(transaction.id) || ""}</td>
            <td class="transaction-actions">
                <button type="button" class="row-action-button edit-transaction-button" data-transaction-id="${Number(transaction.id)}">Edit</button>
                <button type="button" class="row-action-button delete-transaction-button" data-transaction-id="${Number(transaction.id)}">Delete</button>
            </td>
        `;
        tbody.appendChild(row);
    });

    if (toggleButton) {
        toggleButton.classList.toggle("hidden", filteredTransactions.length <= 5);
        toggleButton.textContent = showingAllTransactions ? "View Less" : "View All";
    }
}

function toggleTransactions() {

    showingAllTransactions =
        !showingAllTransactions;

    renderTransactions();

    if (showingAllTransactions) {

        getElement(
            "transactions-wrapper"
        )?.scrollIntoView({
            behavior: "smooth",
            block: "nearest"
        });
    }
}


function escapeHTML(value) {

    return String(value ?? "")
        .replaceAll(
            "&",
            "&amp;"
        )
        .replaceAll(
            "<",
            "&lt;"
        )
        .replaceAll(
            ">",
            "&gt;"
        )
        .replaceAll(
            '"',
            "&quot;"
        )
        .replaceAll(
            "'",
            "&#039;"
        );
}


// ============================================================
// ANALYTICS
// ============================================================

async function loadAnalytics() {

    try {

        const data =
            await apiRequest(
                "/analytics/monthly"
            );

        analyticsMonthlyData =
            data.monthly_data || [];

        populateMonthSelector();

        if (!analyticsMonthlyData.length) {

            renderMonthlyChart([]);

            renderCategoryChart([]);

            return;
        }

        if (!selectedAnalyticsMonth) {

            selectedAnalyticsMonth =
                analyticsMonthlyData[
                    analyticsMonthlyData.length - 1
                ].month;
        }

        if (
            trendMode === "daily"
        ) {

            await loadDailyAnalytics(
                selectedAnalyticsMonth
            );

        } else if (
            trendMode === "yearly"
        ) {

            await loadYearlyAnalytics();

        } else {

            renderMonthlyChart(
                analyticsMonthlyData
            );
        }

        // Default category view = Overall
        await loadCategoryAnalytics(
            "overall"
        );

    } catch (error) {

        console.error(
            "Analytics error:",
            error
        );
    }
}


// ============================================================
// MONTH SELECTOR
// ============================================================

function populateMonthSelector() {

    const selector =
        getElement(
            "analytics-month-selector"
        );

    if (!selector) {
        return;
    }

    selector.innerHTML = "";

    const overallOption =
        document.createElement("option");

    overallOption.value =
        "overall";

    overallOption.textContent =
        "Overall";

    selector.appendChild(
        overallOption
    );


    analyticsMonthlyData
        .slice()
        .reverse()
        .forEach(item => {

            const option =
                document.createElement(
                    "option"
                );

            option.value =
                item.month;

            option.textContent =
                formatMonthLabel(
                    item.month
                );

            selector.appendChild(
                option
            );
        });

    selector.value =
        "overall";
}


function updateMonthSelector(
    value = "overall"
) {

    const selector =
        getElement(
            "analytics-month-selector"
        );

    if (selector) {

        selector.value =
            value;
    }
}


// ============================================================
// CATEGORY / MONTH CHANGE
// ============================================================

async function handleMonthChange(event) {

    const value =
        event.target.value;

    if (value === "overall") {

        await loadCategoryAnalytics(
            "overall"
        );

        return;
    }

    selectedAnalyticsMonth =
        value;

    await loadCategoryAnalytics(
        selectedAnalyticsMonth
    );

    if (
        trendMode === "daily"
    ) {

        await loadDailyAnalytics(
            selectedAnalyticsMonth
        );
    }
}


// ============================================================
// MONTHLY CHART
// ============================================================

function renderMonthlyChart(
    data
) {

    const canvas =
        getElement(
            "monthly-chart"
        );

    if (
        !canvas ||
        typeof Chart === "undefined"
    ) {
        return;
    }

    hideChartMessage(
        "trend-empty-message"
    );

    if (monthlyChart) {

        monthlyChart.destroy();

        monthlyChart = null;
    }

    if (!data.length) {

        showChartMessage(
            "trend-empty-message",
            "No monthly transaction data available."
        );

        return;
    }

    const labels =
        data.map(
            item =>
                formatMonthLabel(
                    item.month
                )
        );

    const expenses =
        data.map(
            item =>
                Number(
                    item.expense || 0
                )
        );

    const incomes =
        data.map(
            item =>
                Number(
                    item.income || 0
                )
        );

    monthlyChart =
        new Chart(
            canvas,
            {
                type: "line",

                data: {

                    labels,

                    datasets: [

                        {
                            label: "Expense",

                            data: expenses,

                            borderWidth: 2,

                            tension: 0.35,

                            pointRadius: 2,

                            pointHoverRadius: 5,

                            fill: false
                        },

                        {
                            label: "Income",

                            data: incomes,

                            borderWidth: 2,

                            tension: 0.35,

                            pointRadius: 2,

                            pointHoverRadius: 5,

                            fill: false
                        }

                    ]
                },

                options:
                    getLineChartOptions()
            }
        );

    getElement(
        "trend-chart-subtitle"
    ).textContent =
        "Monthly income vs expense";
}


// ============================================================
// DAILY CHART
// ============================================================

async function loadDailyAnalytics(
    month
) {

    if (!month) {
        return;
    }

    try {

        const data =
            await apiRequest(
                "/analytics/daily?month=" +
                encodeURIComponent(month)
            );

        renderDailyChart(
            data.daily_data || [],
            month
        );

    } catch (error) {

        console.error(
            "Daily analytics error:",
            error
        );

        renderDailyChart(
            [],
            month
        );
    }
}


function renderDailyChart(
    data,
    month
) {

    const canvas =
        getElement(
            "monthly-chart"
        );

    if (
        !canvas ||
        typeof Chart === "undefined"
    ) {
        return;
    }

    hideChartMessage(
        "trend-empty-message"
    );

    if (monthlyChart) {

        monthlyChart.destroy();

        monthlyChart = null;
    }

    if (!data.length) {

        showChartMessage(
            "trend-empty-message",
            "No transactions for " +
            formatMonthLabel(month)
        );

        getElement(
            "trend-chart-subtitle"
        ).textContent =
            "Daily spending · " +
            formatMonthLabel(month);

        return;
    }

    const labels =
        data.map(
            item =>
                formatDayLabel(
                    item.day
                )
        );

    const expenses =
        data.map(
            item =>
                Number(
                    item.expense || 0
                )
        );

    const incomes =
        data.map(
            item =>
                Number(
                    item.income || 0
                )
        );

    monthlyChart =
        new Chart(
            canvas,
            {
                type: "line",

                data: {

                    labels,

                    datasets: [

                        {
                            label: "Expense",

                            data: expenses,

                            borderWidth: 2,

                            tension: 0.35,

                            pointRadius: 2,

                            pointHoverRadius: 5,

                            fill: false
                        },

                        {
                            label: "Income",

                            data: incomes,

                            borderWidth: 2,

                            tension: 0.35,

                            pointRadius: 2,

                            pointHoverRadius: 5,

                            fill: false
                        }

                    ]
                },

                options:
                    getLineChartOptions()
            }
        );

    getElement(
        "trend-chart-subtitle"
    ).textContent =
        "Daily income vs expense · " +
        formatMonthLabel(month);
}


// ============================================================
// YEARLY CHART
// ============================================================

async function loadYearlyAnalytics() {

    try {

        const data =
            await apiRequest(
                "/analytics/yearly"
            );

        renderYearlyChart(
            data.yearly_data || []
        );

    } catch (error) {

        console.error(
            "Yearly analytics error:",
            error
        );

        renderYearlyChart([]);
    }
}


function renderYearlyChart(
    data
) {

    const canvas =
        getElement(
            "monthly-chart"
        );

    if (
        !canvas ||
        typeof Chart === "undefined"
    ) {
        return;
    }

    hideChartMessage(
        "trend-empty-message"
    );

    if (monthlyChart) {

        monthlyChart.destroy();

        monthlyChart = null;
    }

    if (!data.length) {

        showChartMessage(
            "trend-empty-message",
            "No yearly transaction data available."
        );

        getElement(
            "trend-chart-subtitle"
        ).textContent =
            "Yearly income vs expense";

        return;
    }

    const labels =
        data.map(
            item =>
                String(item.year)
        );

    const expenses =
        data.map(
            item =>
                Number(
                    item.expense || 0
                )
        );

    const incomes =
        data.map(
            item =>
                Number(
                    item.income || 0
                )
        );

    monthlyChart =
        new Chart(
            canvas,
            {
                type: "line",

                data: {

                    labels,

                    datasets: [

                        {
                            label: "Expense",

                            data: expenses,

                            borderWidth: 2,

                            tension: 0.35,

                            pointRadius: 3,

                            pointHoverRadius: 6,

                            fill: false
                        },

                        {
                            label: "Income",

                            data: incomes,

                            borderWidth: 2,

                            tension: 0.35,

                            pointRadius: 3,

                            pointHoverRadius: 6,

                            fill: false
                        }

                    ]
                },

                options:
                    getLineChartOptions()
            }
        );

    getElement(
        "trend-chart-subtitle"
    ).textContent =
        "Yearly income vs expense";
}


// ============================================================
// LINE CHART OPTIONS
// ============================================================

function getLineChartOptions() {

    return {

        responsive: true,

        maintainAspectRatio: false,

        interaction: {
            mode: "index",
            intersect: false
        },

        plugins: {

            legend: {

                display: true,

                position: "top",

                labels: {

                    usePointStyle: true,

                    boxWidth: 8,

                    padding: 16,

                    color: "#999999"
                }
            },

            tooltip: {

                callbacks: {

                    label: function(context) {

                        return (
                            context.dataset.label +
                            ": " +
                            formatCurrency(
                                context.parsed.y
                            )
                        );
                    }
                }
            }
        },

        scales: {

            x: {

                grid: {
                    display: false
                },

                ticks: {

                    color: "#777777",

                    maxRotation: 0,

                    autoSkip: true,

                    maxTicksLimit: 12
                }
            },

            y: {

                beginAtZero: true,

                grid: {

                    color:
                        "rgba(255,255,255,0.06)"
                },

                ticks: {

                    color: "#777777",

                    callback:
                        function(value) {

                            return formatCurrency(
                                value
                            );
                        }
                }
            }
        }
    };
}


// ============================================================
// CATEGORY CHART
// ============================================================

async function loadCategoryAnalytics(
    month
) {

    try {

        let endpoint =
            "/analytics/category";

        if (
            month &&
            month !== "overall"
        ) {

            endpoint +=
                "?month=" +
                encodeURIComponent(month);
        }

        const data =
            await apiRequest(
                endpoint
            );

        renderCategoryChart(
            data.category_data || [],
            month
        );

    } catch (error) {

        console.error(
            "Category analytics error:",
            error
        );

        renderCategoryChart(
            [],
            month
        );
    }
}



function renderCategoryChart(data, month) {
    const canvas = getElement("category-chart");

    if (!canvas || typeof Chart === "undefined") {
        return;
    }

    hideChartMessage("category-empty-message");

    if (categoryChart) {
        categoryChart.destroy();
        categoryChart = null;
    }

    if (!data.length) {
        showChartMessage(
            "category-empty-message",
            month === "overall"
                ? "No spending data available."
                : "No spending data for " + formatMonthLabel(month)
        );
        return;
    }

    const labels = data.map(item => item.category);

    const values = data.map(
        item => Number(item.total_expense || 0)
    );

    // Consistent colors for the spending categories
    const colorPalette = [
        "#6366F1", // Indigo
        "#06B6D4", // Cyan
        "#10B981", // Green
        "#F59E0B", // Amber
        "#EF4444", // Red
        "#8B5CF6", // Purple
        "#EC4899", // Pink
        "#14B8A6", // Teal
        "#F97316", // Orange
        "#64748B"  // Slate
    ];

    const backgroundColors = labels.map(
        (_, index) => colorPalette[index % colorPalette.length]
    );

    categoryChart = new Chart(canvas, {
        type: "doughnut",

        data: {
            labels: labels,

            datasets: [{
                data: values,
                backgroundColor: backgroundColors,
                hoverBackgroundColor: backgroundColors,
                borderColor: "#111111",
                borderWidth: 2,
                hoverOffset: 6
            }]
        },

        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: "68%",

            plugins: {
                legend: {
                    position: "bottom",

                    labels: {
                        usePointStyle: true,
                        boxWidth: 8,
                        padding: 12,
                        color: "#999999"
                    }
                },

                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return (
                                context.label + ": " +
                                formatCurrency(context.parsed)
                            );
                        }
                    }
                }
            }
        }
    });

    const subtitle = getElement("category-chart-subtitle");

    if (subtitle) {
        subtitle.textContent =
            month === "overall"
                ? "Overall spending"
                : "Spending · " + formatMonthLabel(month);
    }
}


// ============================================================
// CHART EMPTY HELPERS
// ============================================================

function showChartMessage(
    id,
    message
) {

    const element =
        getElement(id);

    if (!element) {
        return;
    }

    element.textContent =
        message;

    element.classList.remove(
        "hidden"
    );
}


function hideChartMessage(id) {

    const element =
        getElement(id);

    if (!element) {
        return;
    }

    element.classList.add(
        "hidden"
    );
}


// ============================================================
// TREND MODE
// ============================================================

async function setTrendMode(
    mode
) {

    trendMode =
        mode;

    const dailyButton =
        getElement(
            "daily-view-toggle"
        );

    const monthlyButton =
        getElement(
            "monthly-view-toggle"
        );

    const yearlyButton =
        getElement(
            "yearly-view-toggle"
        );

    dailyButton?.classList.toggle(
        "active",
        mode === "daily"
    );

    monthlyButton?.classList.toggle(
        "active",
        mode === "monthly"
    );

    yearlyButton?.classList.toggle(
        "active",
        mode === "yearly"
    );


    if (
        mode === "daily"
    ) {

        if (!selectedAnalyticsMonth) {

            selectedAnalyticsMonth =
                analyticsMonthlyData[
                    analyticsMonthlyData.length - 1
                ]?.month;
        }

        updateMonthSelector(
            selectedAnalyticsMonth
        );

        await loadDailyAnalytics(
            selectedAnalyticsMonth
        );

        return;
    }


    if (
        mode === "monthly"
    ) {

        updateMonthSelector(
            "overall"
        );

        renderMonthlyChart(
            analyticsMonthlyData
        );

        return;
    }


    if (
        mode === "yearly"
    ) {

        updateMonthSelector(
            "overall"
        );

        await loadYearlyAnalytics();
    }
}


// ============================================================
// ANOMALIES
// ============================================================

async function loadAnomalies() {

    try {

        const data =
            await apiRequest(
                "/analytics/anomalies"
            );

        renderAnomalies(
            data.anomalies || []
        );

    } catch (error) {

        console.error(
            "Anomaly error:",
            error
        );
    }
}


function renderAnomalies(
    anomalies
) {

    const container =
        getElement(
            "anomalies-container"
        );

    if (!container) {
        return;
    }

    container.innerHTML = "";

    if (!anomalies.length) {

        container.innerHTML = `
            <div class="empty-state">
                No unusual expenses detected.
            </div>
        `;

        return;
    }

    anomalies.forEach(
        anomaly => {

            const item =
                document.createElement(
                    "div"
                );

            item.className =
                "anomaly-item";

            item.innerHTML = `

                <div>

                    <strong>
                        ${escapeHTML(
                            anomaly.category ||
                            "Expense"
                        )}
                    </strong>

                    <p>
                        ${escapeHTML(
                            anomaly.description ||
                            "Unusual expense"
                        )}
                    </p>

                    ${Array.isArray(anomaly.reasons) && anomaly.reasons.length
                        ? `<small>${escapeHTML(anomaly.reasons.join(" · "))}</small>`
                        : ""}

                    <small>
                        ${escapeHTML(
                            anomaly.date || ""
                        )}
                    </small>

                </div>

                <strong>
                    ${formatCurrency(
                        anomaly.amount
                    )}
                </strong>
            `;

            container.appendChild(
                item
            );
        }
    );
}


// ============================================================
// AI PREDICTION
// ============================================================

async function loadPrediction() {

    try {

        const data =
            await apiRequest(
                "/predict",
                {
                    method: "POST",

                    body: JSON.stringify({

                        Year:
                            new Date()
                                .getFullYear(),

                        Month:
                            new Date()
                                .getMonth() + 1
                    })
                }
            );

        getElement(
            "predicted-expense"
        ).textContent =
            formatCurrency(
                data.predicted_expense
            );

        const predictionNote = getElement("prediction-method");
        if (predictionNote) {
            predictionNote.textContent = data.prediction_method || "Based on your transaction history";
        }

    } catch (error) {

        console.error(
            "Prediction error:",
            error
        );

        getElement(
            "predicted-expense"
        ).textContent =
            "Unavailable";
    }
}


// ============================================================
// AVOIDABLE SPENDING INSIGHTS
// ============================================================

async function loadAvoidableSpending() {
    const container = getElement("avoidable-spending-container");
    if (!container) return;

    try {
        const data = await apiRequest("/analytics/avoidable-spending");
        renderAvoidableSpending(data.suggestions || []);
    } catch (error) {
        console.error("Avoidable spending error:", error);
        container.innerHTML = '<div class="empty-state">Spending suggestions are temporarily unavailable.</div>';
    }
}

function renderAvoidableSpending(suggestions) {
    const container = getElement("avoidable-spending-container");
    if (!container) return;

    container.innerHTML = "";
    if (!suggestions.length) {
        container.innerHTML = '<div class="empty-state">No clear avoidable-spending pattern yet. Add more transactions or check back next month.</div>';
        return;
    }

    suggestions.forEach(suggestion => {
        const item = document.createElement("div");
        item.className = "anomaly-item";
        const details = document.createElement("div");
        const title = document.createElement("strong");
        title.textContent = suggestion.category || "Other";
        const message = document.createElement("p");
        message.textContent = suggestion.message || "Spending is above your recent average.";
        const saving = document.createElement("small");
        saving.textContent = "Possible monthly saving: " + formatCurrency(suggestion.potential_saving);
        details.append(title, message, saving);
        const amount = document.createElement("strong");
        amount.textContent = formatCurrency(suggestion.recent_month_spend);
        item.append(details, amount);
        container.appendChild(item);
    });
}


// ============================================================
// MONTH-OVER-MONTH SPENDING COMPARISON
// ============================================================

function comparisonMonthLabel(value) {
    return formatMonthLabel(value) || value || "Selected month";
}

function formatComparisonPercent(value) {
    if (value === null || value === undefined) return "New spending (no previous-month baseline)";
    if (Number(value) === 0) return "No change (0%)";
    return `${Number(value) > 0 ? "+" : ""}${Number(value).toLocaleString("en-IN", { maximumFractionDigits: 1 })}% vs previous month`;
}

async function loadMonthlyComparison() {
    const body = getElement("monthly-comparison-body");
    if (!body) return;
    const monthInput = getElement("monthly-comparison-month");
    if (monthInput && !monthInput.value) monthInput.value = currentMonthValue();
    const month = monthInput?.value || currentMonthValue();
    body.innerHTML = '<tr><td colspan="5" class="empty-state">Loading spending comparison...</td></tr>';

    try {
        const data = await apiRequest(`/analytics/monthly-comparison?month=${encodeURIComponent(month)}`);
        getElement("comparison-current-total").textContent = formatCurrency(data.current_total);
        getElement("comparison-previous-total").textContent = formatCurrency(data.previous_total);
        getElement("comparison-change-total").textContent = `${Number(data.change_amount) > 0 ? "+" : Number(data.change_amount) < 0 ? "−" : ""}${formatCurrency(Math.abs(Number(data.change_amount || 0)))}`;
        getElement("comparison-change-percent").textContent = formatComparisonPercent(data.percentage_change);
        getElement("comparison-current-label").textContent = comparisonMonthLabel(data.month);
        getElement("comparison-previous-label").textContent = comparisonMonthLabel(data.previous_month);

        const increase = data.biggest_increase;
        const decrease = data.biggest_decrease;
        getElement("comparison-biggest-increase").textContent = increase ? `${increase.category}: +${formatCurrency(increase.change_amount)}` : "No category increased";
        getElement("comparison-biggest-decrease").textContent = decrease ? `${decrease.category}: −${formatCurrency(Math.abs(decrease.change_amount))}` : "No category decreased";
        getElement("monthly-comparison-note").textContent = `Comparing ${comparisonMonthLabel(data.month)} with ${comparisonMonthLabel(data.previous_month)}. Only recorded expenses for your account are included.`;

        if (!data.categories?.length) {
            body.innerHTML = '<tr><td colspan="5" class="empty-state">No expense transactions found for these months yet.</td></tr>';
            return;
        }
        body.innerHTML = data.categories.map(item => {
            const change = Number(item.change_amount || 0);
            const sign = change > 0 ? "+" : change < 0 ? "−" : "";
            const changeClass = change > 0 ? "comparison-increase" : change < 0 ? "comparison-decrease" : "comparison-same";
            const percentage = item.percentage_change === null ? "New" : `${Number(item.percentage_change) > 0 ? "+" : ""}${Number(item.percentage_change).toLocaleString("en-IN", { maximumFractionDigits: 1 })}%`;
            return `<tr><td>${escapeHTML(item.category)}</td><td>${formatCurrency(item.previous_expense)}</td><td>${formatCurrency(item.current_expense)}</td><td class="${changeClass}">${sign}${formatCurrency(Math.abs(change))}</td><td class="${changeClass}">${percentage}</td></tr>`;
        }).join("");
    } catch (error) {
        body.innerHTML = `<tr><td colspan="5" class="empty-state">${escapeHTML(error.message)}</td></tr>`;
    }
}


// ============================================================
// MONTHLY BUDGET PLANNER
// ============================================================

function currentMonthValue() {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, character => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[character]));
}

async function loadBudgets() {
    const container = getElement("budgets-container");
    if (!container) return;
    const monthInput = getElement("budget-month");
    if (monthInput && !monthInput.value) monthInput.value = currentMonthValue();
    const month = monthInput?.value || currentMonthValue();
    try {
        const data = await apiRequest(`/planning/budgets?month=${encodeURIComponent(month)}`);
        renderBudgets(data.budgets || []);
    } catch (error) {
        container.innerHTML = `<div class="empty-state planning-empty">Could not load budgets: ${escapeHTML(error.message)}</div>`;
    }
}

function renderBudgets(budgets) {
    const container = getElement("budgets-container");
    if (!container) return;
    if (!budgets.length) {
        container.innerHTML = '<div class="empty-state planning-empty">No budgets for this month yet. Add a category and monthly limit above to get started.</div>';
        return;
    }
    container.innerHTML = budgets.map(budget => {
        const limit = Number(budget.amount || 0);
        const spent = Number(budget.spent || 0);
        const remaining = limit - spent;
        const percent = limit > 0 ? Math.min(100, Math.round(spent / limit * 100)) : 0;
        const over = spent > limit;
        return `<article class="planning-item">
            <div class="planning-item-header"><div><h3>${escapeHTML(budget.category)}</h3><p>${escapeHTML(budget.month)} budget</p></div><button type="button" class="planning-delete-button" data-budget-delete="${Number(budget.id)}">Remove</button></div>
            <div class="planning-meta"><span>Spent ${formatCurrency(spent)}</span><span>Limit ${formatCurrency(limit)}</span></div>
            <div class="planning-progress"><div class="planning-progress-bar ${over ? 'over-budget' : ''}" style="width:${percent}%"></div></div>
            <div class="planning-meta"><span>${over ? `Over budget by ${formatCurrency(Math.abs(remaining))}` : `${formatCurrency(remaining)} remaining`}</span><span>${Math.round(limit > 0 ? spent / limit * 100 : 0)}% used</span></div>
        </article>`;
    }).join("");
}

async function handleSaveBudget(event) {
    event.preventDefault();
    const month = getElement("budget-month")?.value || currentMonthValue();
    const category = getElement("budget-category")?.value.trim();
    const amount = Number(getElement("budget-amount")?.value);
    if (!category || !Number.isFinite(amount) || amount <= 0) return alert("Enter a category and a positive budget amount.");
    try {
        await apiRequest("/planning/budgets", { method: "POST", body: JSON.stringify({ month, category, amount }) });
        getElement("budget-category").value = "";
        getElement("budget-amount").value = "";
        await loadBudgets();
        alert("Monthly budget saved.");
    } catch (error) { alert(error.message || "Could not save the budget."); }
}

async function deleteBudget(id) {
    if (!confirm("Remove this budget? Your transactions will not be deleted.")) return;
    try {
        await apiRequest(`/planning/budgets/${id}`, { method: "DELETE" });
        await loadBudgets();
    } catch (error) { alert(error.message || "Could not remove the budget."); }
}

// ============================================================
// SAVINGS GOALS
// ============================================================

async function loadSavingsGoals() {
    const container = getElement("savings-goals-container");
    if (!container) return;
    try {
        const data = await apiRequest("/planning/goals");
        renderSavingsGoals(data.goals || []);
    } catch (error) {
        container.innerHTML = `<div class="empty-state planning-empty">Could not load savings goals: ${escapeHTML(error.message)}</div>`;
    }
}

function renderSavingsGoals(goals) {
    const container = getElement("savings-goals-container");
    if (!container) return;
    if (!goals.length) {
        container.innerHTML = '<div class="empty-state planning-empty">No savings goals yet. Create your first goal above.</div>';
        return;
    }
    container.innerHTML = goals.map(goal => {
        const target = Number(goal.target_amount || 0);
        const saved = Number(goal.current_amount || 0);
        const remaining = Math.max(0, target - saved);
        const percent = target > 0 ? Math.min(100, Math.round(saved / target * 100)) : 0;
        const complete = saved >= target;
        const targetDate = goal.target_date ? `Target date: ${escapeHTML(goal.target_date)}` : "No target date set";
        return `<article class="planning-item">
            <div class="planning-item-header"><div><h3>${escapeHTML(goal.name)}</h3><p>${targetDate}</p></div><span class="planning-status ${complete ? 'complete' : ''}">${complete ? 'Goal reached' : `${percent}% complete`}</span></div>
            <div class="planning-number">${formatCurrency(saved)} <span style="font-size:12px;color:#858585;font-weight:500">of ${formatCurrency(target)}</span></div>
            <div class="planning-progress"><div class="planning-progress-bar ${complete ? '' : ''}" style="width:${percent}%"></div></div>
            <div class="planning-meta"><span>${complete ? 'Target achieved 🎉' : `${formatCurrency(remaining)} left to save`}</span><span>${percent}%</span></div>
            ${complete ? '' : `<form class="planning-inline-form" data-contribution-form="${Number(goal.id)}"><input type="number" name="contribution" min="0.01" step="0.01" placeholder="Add savings (₹)" required aria-label="Amount to add to ${escapeHTML(goal.name)}"><button type="submit">Add savings</button></form>`}
            <div style="display:flex;justify-content:flex-end;margin-top:10px"><button type="button" class="planning-delete-button" data-goal-delete="${Number(goal.id)}">Delete goal</button></div>
        </article>`;
    }).join("");
}

async function handleCreateSavingsGoal(event) {
    event.preventDefault();
    const name = getElement("goal-name")?.value.trim();
    const target_amount = Number(getElement("goal-target")?.value);
    const target_date = getElement("goal-date")?.value || null;
    if (!name || !Number.isFinite(target_amount) || target_amount <= 0) return alert("Enter a goal name and a positive target amount.");
    try {
        await apiRequest("/planning/goals", { method: "POST", body: JSON.stringify({ name, target_amount, target_date }) });
        getElement("savings-goal-form").reset();
        await loadSavingsGoals();
        alert("Savings goal created.");
    } catch (error) { alert(error.message || "Could not create the goal."); }
}

async function addGoalContribution(id, amount) {
    if (!Number.isFinite(amount) || amount <= 0) return alert("Enter a positive savings amount.");
    try {
        await apiRequest(`/planning/goals/${id}/contributions`, { method: "POST", body: JSON.stringify({ amount }) });
        await loadSavingsGoals();
    } catch (error) { alert(error.message || "Could not update savings."); }
}

async function deleteSavingsGoal(id) {
    if (!confirm("Delete this savings goal? This will not affect your transactions.")) return;
    try {
        await apiRequest(`/planning/goals/${id}`, { method: "DELETE" });
        await loadSavingsGoals();
    } catch (error) { alert(error.message || "Could not delete the goal."); }
}

function setupPlanningFeatureEvents() {
    getElement("budget-form")?.addEventListener("submit", handleSaveBudget);
    getElement("budget-month")?.addEventListener("change", loadBudgets);
    getElement("savings-goal-form")?.addEventListener("submit", handleCreateSavingsGoal);
    getElement("budgets-container")?.addEventListener("click", event => {
        const button = event.target.closest("[data-budget-delete]");
        if (button) deleteBudget(Number(button.dataset.budgetDelete));
    });
    getElement("savings-goals-container")?.addEventListener("click", event => {
        const button = event.target.closest("[data-goal-delete]");
        if (button) deleteSavingsGoal(Number(button.dataset.goalDelete));
    });
    getElement("savings-goals-container")?.addEventListener("submit", event => {
        const form = event.target.closest("[data-contribution-form]");
        if (!form) return;
        event.preventDefault();
        const amount = Number(new FormData(form).get("contribution"));
        addGoalContribution(Number(form.dataset.contributionForm), amount);
    });
}

// ============================================================
// NAVIGATION
// ============================================================

function setupNavigation() {

    document
        .querySelectorAll(".nav-item")
        .forEach(item => {

            item.addEventListener(
                "click",
                function() {

                    document
                        .querySelectorAll(
                            ".nav-item"
                        )
                        .forEach(
                            nav =>
                                nav.classList.remove(
                                    "active"
                                )
                        );

                    this.classList.add(
                        "active"
                    );
                }
            );
        });
}


// ============================================================
// INITIALIZATION
// ============================================================

async function checkLogin() {

    try {

        const data =
            await apiRequest("/me");

        currentUser =
            data.user;

        showDashboard();

        await loadDashboard();

    } catch {

        showLogin();
    }
}


// ============================================================
// DOM READY
// ============================================================

document.addEventListener(
    "DOMContentLoaded",
    function() {

        // Login
        getElement(
            "login-form"
        )?.addEventListener(
            "submit",
            handleLogin
        );


        // Register
        getElement(
            "register-form"
        )?.addEventListener(
            "submit",
            handleRegister
        );


        // Auth switching
        getElement(
            "show-register"
        )?.addEventListener(
            "click",
            showRegisterForm
        );


        getElement(
            "show-login"
        )?.addEventListener(
            "click",
            showLoginForm
        );


        // Add transaction modal
        getElement(
            "open-transaction-modal"
        )?.addEventListener(
            "click",
            openTransactionModal
        );


        getElement(
            "close-transaction-modal"
        )?.addEventListener(
            "click",
            closeTransactionModal
        );


        getElement(
            "cancel-transaction"
        )?.addEventListener(
            "click",
            closeTransactionModal
        );


        getElement(
            "transaction-form"
        )?.addEventListener(
            "submit",
            handleAddTransaction
        );


        // Close modal by clicking outside
        getElement(
            "transaction-modal"
        )?.addEventListener(
            "click",
            function(event) {

                if (
                    event.target === this
                ) {

                    closeTransactionModal();
                }
            }
        );


        // CSV
        getElement(
            "csv-form"
        )?.addEventListener(
            "submit",
            handleCSVImport
        );


        // Logout
        getElement(
            "logout-button"
        )?.addEventListener(
            "click",
            handleLogout
        );


        // Trend buttons
        getElement(
            "daily-view-toggle"
        )?.addEventListener(
            "click",
            function() {

                setTrendMode(
                    "daily"
                );
            }
        );


        getElement(
            "monthly-view-toggle"
        )?.addEventListener(
            "click",
            function() {

                setTrendMode(
                    "monthly"
                );
            }
        );


        getElement(
            "yearly-view-toggle"
        )?.addEventListener(
            "click",
            function() {

                setTrendMode(
                    "yearly"
                );
            }
        );


        // Category/month selector
        getElement(
            "analytics-month-selector"
        )?.addEventListener(
            "change",
            handleMonthChange
        );


        // Transactions
        getElement(
            "toggle-transactions-button"
        )?.addEventListener(
            "click",
            toggleTransactions
        );

        // Search and filter transactions instantly
        [
            "transaction-search-input",
            "transaction-type-filter",
            "transaction-category-filter",
            "transaction-start-filter",
            "transaction-end-filter"
        ].forEach(id => {
            const element = getElement(id);
            if (!element) return;
            element.addEventListener(id === "transaction-search-input" ? "input" : "change", () => {
                showingAllTransactions = false;
                renderTransactions();
            });
        });
        getElement("reset-transaction-filters")?.addEventListener("click", resetTransactionFilters);

        getElement("transactions-body")?.addEventListener("click", function(event) {
            const button = event.target.closest("button[data-transaction-id]");
            if (!button) return;
            const id = Number(button.dataset.transactionId);
            if (button.classList.contains("edit-transaction-button")) {
                openEditTransaction(id);
            } else if (button.classList.contains("delete-transaction-button")) {
                deleteTransaction(id);
            }
        });

        // PDF financial report
        setupReportDateDefaults();
        getElement("report-last-7")?.addEventListener("click", () => setReportRange("7"));
        getElement("report-last-30")?.addEventListener("click", () => setReportRange("30"));
        getElement("report-this-month")?.addEventListener("click", () => setReportRange("month"));
        getElement("download-report-button")?.addEventListener("click", downloadFinancialReport);

        // Month-over-month comparison and monthly budgets
        if (getElement("monthly-comparison-month")) getElement("monthly-comparison-month").value = currentMonthValue();
        getElement("monthly-comparison-month")?.addEventListener("change", loadMonthlyComparison);
        if (getElement("budget-month")) getElement("budget-month").value = currentMonthValue();
        setupPlanningFeatureEvents();

        // Navigation
        setupNavigation();


        // Start
        checkLogin();
    }
);