# FinanceFlow feature update

This update adds:
- Edit and delete controls on each transaction row. Deletion requires confirmation.
- A downloadable PDF report for a chosen date range.
- Day-wise expense totals (including dates with no recorded expenses), average daily expense, days with no recorded expenses, monthly income/expense summary and chart, category totals, and transaction details.
- Backend update/delete/report queries are restricted to the authenticated user's `user_id`.
- No database schema changes are required.

## Apply safely
1. Stop the Flask backend.
2. Make a backup copy of your current project folder.
3. Extract the update ZIP into the existing project folder and allow it to replace only the files in the ZIP. Do not delete or overwrite your existing `.env` file.
4. Open a terminal in the project folder and activate your existing virtual environment.
5. Install the new dependency:
   `pip install -r requirements.txt`
6. Start the backend with your existing command, then refresh the frontend page.

## Report dates
The report section defaults to the last 30 days. Use the date fields or the Last 7 days, Last 30 days, and This month shortcuts, then choose Download PDF Report.

A “day with no recorded expenses” means FinanceFlow contains no expense transaction for that date. It cannot establish whether spending occurred but was not recorded.

## Validation
Python and JavaScript syntax checks passed. A sample PDF chart was generated successfully. A live database/API integration test was not run in this environment, so test Edit, Delete, and PDF download with your local backend/database after applying the update.
