# Personal Finance Management System

A full-stack finance tracking web application built with Flask and SQLite that helps users manage income, expenses, budgets, and spending habits through interactive analytics and reporting.

## Features

### Authentication & Security
- User registration and login
- Password hashing using Werkzeug
- Session-based authentication
- Profile management
- Password update functionality

### Expense & Income Tracking
- Add income and expense records
- Categorize transactions
- Edit and delete transactions
- Add notes to financial records
- Date-based transaction logging

### Budget Management
- Set category-specific budgets
- Monitor spending against budget limits
- Monthly budget tracking

### Analytics Dashboard
- Income vs Expense analysis
- Category-wise spending breakdown
- Monthly spending comparison
- Financial summaries and insights

### Search & Filtering
- Search transactions by name or note
- Filter by:
  - Transaction type
  - Category
  - Month
  - Year
- Sort transactions by:
  - Date
  - Type
  - Category

### Recurring Transactions
- Automatic generation of recurring expenses/income
- Monthly recurring transaction support

### Reporting
- Export financial records as CSV
- Download transaction history

---

## Tech Stack

### Backend
- Flask
- Python
- SQLite

### Frontend
- HTML
- CSS
- Bootstrap
- Jinja2

### Security
- Werkzeug Password Hashing
- Flask Sessions

---

## Database Design

### PARTICIPANTS

Stores user information.

| Field | Type |
|---------|---------|
| id | Integer |
| username | Text |
| email | Text |
| password | Text |

### TASKS

Stores income and expense records.

| Field | Type |
|---------|---------|
| expense_name | Text |
| amount | Integer |
| note | Text |
| date_of | Text |
| type | Income / Expense |
| category | Text |
| recurring | Text |

### BUDGETS

Stores user-defined budgets.

| Field | Type |
|---------|---------|
| user_id | Integer |
| category | Text |
| amount | Integer |

---

## Screenshots

### Dashboard
(Add Screenshot Here)

### Analytics Page
(Add Screenshot Here)

### Budget Management
(Add Screenshot Here)

---

## Installation

Clone the repository:

```bash
git clone https://github.com/yourusername/FinanceTracker.git
```

Navigate to the project folder:

```bash
cd FinanceTracker
```

Install dependencies:

```bash
pip install flask python-dateutil werkzeug
```

Run the application:

```bash
python app.py
```

Open:

```text
http://127.0.0.1:5001
```

---

## Future Improvements

- Email reminders for recurring expenses
- Financial goal tracking
- Investment portfolio management
- Data visualizations with Plotly
- Budget recommendations
- Dark mode
- REST API support
- Multi-currency support
- Cloud database integration

---

## Key Learning Outcomes

This project helped me gain experience with:

- Flask web development
- Authentication systems
- Session management
- Relational database design
- SQL queries and filtering
- Data analytics
- CSV report generation
- Financial application development
- Full-stack application deployment

---

## Live Demo

🌐 https://personal-finance-manager-system.onrender.com/

## Author

Built as part of my software development and problem-solving journey.

---
*"Track your money. Understand your habits. Improve your future."*