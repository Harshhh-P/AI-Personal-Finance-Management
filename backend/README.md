\# Flask Backend



This folder contains the Flask REST API for the AI-Based Personal Finance Management System.



\## Technologies



\- Python

\- Flask

\- Flask-CORS

\- PyMySQL

\- Pandas

\- Joblib

\- Scikit-learn

\- MySQL



\## Backend Responsibilities



The Flask backend connects the application with:



1\. MySQL database

2\. Machine Learning model

3\. Frontend application



\## APIs



\### GET `/`



Checks whether the backend is running.



\### GET `/model-info`



Returns information about the trained Random Forest model.



\### POST `/predict`



Predicts the expected monthly expense using the trained ML model.



\### GET `/transactions`



Returns transactions stored in MySQL.



\### POST `/transactions`



Adds a new transaction to MySQL.



\### GET `/summary`



Returns:



\- Total income

\- Total expense

\- Balance

\- Number of transactions



\## Database



Database name:



`ai\_personal\_finance`



Main table:



`transactions`



\## Running the Backend



From the project root:



```bash

python backend/app.py

