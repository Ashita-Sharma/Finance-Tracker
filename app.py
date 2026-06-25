from flask import Flask, redirect, url_for, render_template, request, flash, send_file
from flask import session
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date
import csv
import io



app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

@app.route('/')
def reroute():
    if 'user_id' not in session:
        return redirect(url_for('sign_up'))
    return redirect(url_for('dashboard'))


def init_db():
    with sqlite3.connect("database.db") as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS PARTICIPANTS (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            email TEXT,
            password TEXT
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS TASKS (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            expense_name TEXT,
            amount INTEGER,
            note TEXT,
            date_of TEXT,
            type TEXT,
            category TEXT,
            recurring TEXT DEFAULT NULL,
            FOREIGN KEY (user_id) REFERENCES PARTICIPANTS(id)
        )
        """)
        conn.execute("""
                CREATE TABLE IF NOT EXISTS BUDGETS (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    budget_name TEXT,
                    amount INTEGER,
                    date_of TEXT,
                    category TEXT DEFAULT 'medium',
                    UNIQUE(user_id, category),
                    FOREIGN KEY (user_id) REFERENCES PARTICIPANTS(id)
                )
                """
                     )
init_db()
def generate_recurring(user_id):
    current_month = date.today().strftime('%Y-%m')  # e.g. "2026-06"
    today = date.today().isoformat()                # e.g. "2026-06-15"

    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT expense_name, amount, note, type, category, recurring FROM TASKS WHERE user_id = ? AND recurring IS NOT NULL GROUP BY expense_name, type, category",
            (user_id,))
        recurring_tasks = cursor.fetchall()

        for task in recurring_tasks:
            expense_name, amount, note, task_type, category, recurring = task

            cursor.execute(
                "SELECT 1 FROM TASKS WHERE user_id = ? AND expense_name = ? AND type = ? AND category = ? AND date_of LIKE ?",
                (user_id, expense_name, task_type, category, f"{current_month}%"))
            exists = cursor.fetchone()

            if not exists:
                cursor.execute(
                    "INSERT INTO TASKS (user_id, expense_name, amount, note, date_of, type, category, recurring) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (user_id, expense_name, amount, note, today, task_type, category, recurring))

        conn.commit()

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    generate_recurring(session['user_id'])
    if request.method == 'POST':
        expense_name = request.form['ExpenseName']
        amount = request.form['Amount'].replace(',', '')
        note = request.form['Note']
        date_of = request.form['Date']
        transaction_type = request.form['Type']
        category = request.form['Category']
        recurring = request.form['Recurring'] or None  # converts "" to None

        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO TASKS (user_id, expense_name, amount, note, date_of, type, category, recurring) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (session['user_id'], expense_name, amount, note, date_of, transaction_type, category, recurring))
            conn.commit()

        flash("Added!", "success")
        return redirect(url_for('dashboard'))

    sort_by = request.args.get('sort', 'date_of')
    search_query = request.args.get('search', '')

    query = "SELECT * FROM TASKS WHERE user_id = ?"
    params = [session['user_id']]
    total_balance = 0

    if search_query:
        query += " AND (expense_name LIKE ? OR note LIKE ?)"
        params.append(f"%{search_query}%")
        params.append(f"%{search_query}%")

    filter_type = request.args.get('filter_type', 'all')
    filter_category = request.args.get('filter_category', 'all')

    selected_month = request.args.get('month', 'all')
    selected_year = request.args.get('year', 'all')

    date_filter = ""
    params_base = [session['user_id']]

    if selected_year != 'all' and selected_month != 'all':
        query += " AND date_of LIKE ?"
        params.append(f"{selected_year}-{selected_month}%")
    elif selected_year != 'all':
        query += " AND date_of LIKE ?"
        params.append(f"{selected_year}%")
    elif selected_month != 'all':
        query += " AND strftime('%m', date_of) = ?"
        params.append(selected_month)

    if filter_type != 'all':
        query += " AND type = ?"
        params.append(filter_type)

    if filter_category != 'all':
        query += " AND category = ?"
        params.append(filter_category)


    if sort_by == 'date_of':
        query += " ORDER BY date_of ASC"
    elif sort_by == 'type':
        query += " ORDER BY CASE type WHEN 'expense' THEN 1 WHEN 'income' THEN 2 END"
    elif sort_by == 'category':
        query += " ORDER BY CASE category WHEN 'home' THEN 1 WHEN 'work' THEN 2 WHEN 'personal' THEN 3 END"

    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        tasks = cursor.fetchall()

    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM TASKS WHERE user_id = ?", (session['user_id'],))
        total = cursor.fetchone()[0]

    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT COALESCE(SUM(amount),0) FROM BUDGETS WHERE category = ? AND user_id = ?",
            ('work', session['user_id']))
        work = cursor.fetchone()[0]
        cursor.execute(
            f"SELECT COALESCE(SUM(amount),0) FROM TASKS WHERE category = ? AND user_id = ?",
            ('home', session['user_id']))
        home = cursor.fetchone()[0]
        cursor.execute(
            f"SELECT COALESCE(SUM(amount),0) FROM TASKS WHERE category = ? AND user_id = ?",
            ('personal', session['user_id']))
        personal = cursor.fetchone()[0]


    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT COALESCE(SUM(amount),0) FROM TASKS WHERE type = ? AND user_id = ?{date_filter}",
            ('income', session['user_id'], *params_base[1:]))
        incomee = cursor.fetchone()[0]
        cursor.execute(
            f"SELECT COALESCE(SUM(amount),0) FROM TASKS WHERE type = ? AND user_id = ?{date_filter}",
            ('expense', session['user_id'], *params_base[1:]))
        expenses = cursor.fetchone()[0]
        total_balance = incomee - expenses


    return render_template('dashboard.html', tasks=tasks, filter_type=filter_type,  filter_category=filter_category,
                           sort_by=sort_by, search_query=search_query, total=total, total_balance=total_balance, total_income=incomee, total_expense = expenses,
                           selected_month=selected_month,
                           selected_year=selected_year)
@app.route('/analyze')
def analyze():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    selected_month = request.args.get('month', 'all')
    selected_year = request.args.get('year', 'all')

    date_filter = ""
    date_params = []

    if selected_year != 'all' and selected_month != 'all':
        date_filter = " AND date_of LIKE ?"
        date_params.append(f"{selected_year}-{selected_month}%")
    elif selected_year != 'all':
        date_filter = " AND date_of LIKE ?"
        date_params.append(f"{selected_year}%")
    elif selected_month != 'all':
        date_filter = " AND strftime('%m', date_of) = ?"
        date_params.append(selected_month)

    categories = ['Salary', 'Food', 'Rent', 'Transport', 'Entertainment', 'Shopping', 'Utilities', 'Other']

    expense_data = []
    income_data = []

    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        for cat in categories:
            cursor.execute(
                f"SELECT COALESCE(SUM(amount),0) FROM TASKS WHERE type = 'expense' AND category = ? AND user_id = ?{date_filter}",
                (cat, session['user_id'], *date_params))
            expense_data.append(cursor.fetchone()[0])

            cursor.execute(
                f"SELECT COALESCE(SUM(amount),0) FROM TASKS WHERE type = 'income' AND category = ? AND user_id = ?{date_filter}",
                (cat, session['user_id'], *date_params))
            income_data.append(cursor.fetchone()[0])

    return render_template('analyze.html',
                           categories=categories,
                           expense_data=expense_data,
                           income_data=income_data,
                           selected_month=selected_month,
                           selected_year=selected_year)

@app.route('/budget', methods=['GET', 'POST'])
def budget():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    categories = ['Salary', 'Food', 'Rent', 'Transport', 'Entertainment', 'Shopping', 'Utilities', 'Other']

    if request.method == 'POST':
        for cat in categories:
            amount = request.form.get(cat, 0)
            if amount:
                with sqlite3.connect("database.db") as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT OR REPLACE INTO BUDGETS (user_id, category, amount) VALUES (?, ?, ?)",
                        (session['user_id'], cat, amount))
                    conn.commit()

        flash("Budgets updated!", "success")
        return redirect(url_for('budget'))

    # Fetch existing budgets
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT category, amount FROM BUDGETS WHERE user_id = ?", (session['user_id'],))
        budget_data = {row[0]: row[1] for row in cursor.fetchall()}

    # Fetch actual spending per category for current month
    current_month = date.today().strftime('%Y-%m')
    spending = {}
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        for cat in categories:
            cursor.execute(
                "SELECT COALESCE(SUM(amount),0) FROM TASKS WHERE type = 'expense' AND category = ? AND user_id = ? AND date_of LIKE ?",
                (cat, session['user_id'], f"{current_month}%"))
            spending[cat] = cursor.fetchone()[0]

    return render_template('budget.html',
                           categories=categories,
                           budget_data=budget_data,
                           spending=spending)

@app.route('/export')
def export():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM TASKS WHERE user_id = ?", (session['user_id'],))
        headers = [description[0] for description in cursor.description]
        tasks = cursor.fetchall()

    csv_data = io.StringIO()
    writer = csv.writer(csv_data)
    writer.writerow(headers)
    writer.writerows(tasks)

    mem_file = io.BytesIO(csv_data.getvalue().encode('utf-8'))

    return send_file(
        mem_file,
        mimetype='text/csv',
        as_attachment=True,
        download_name='finance_report.csv'
    )

@app.route('/new-log', methods=['GET', 'POST'])
def new_log():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('new_log.html')

@app.route('/sign_up', methods=['GET', 'POST'])
def sign_up():
    if 'user_id' in session:
        flash('Already logged in!', 'warning')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form['userEmail']
        username = request.form['userId']
        password = request.form['userPassword']
        confirm_password = request.form['ConfirmUserPassword']
        if not email:
            flash('Email is required!', 'danger')
            return redirect(url_for('sign_up'))
        if not username:
            flash('Username is required!', 'warning')
            return redirect(url_for('sign_up'))
        if not password:
            flash('Password field is required!', 'danger')
            return redirect(url_for('sign_up'))
        if len(password) < 8:
            flash("Password must be at least 8 characters!", "warning")
            return redirect(url_for('sign_up'))
        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM PARTICIPANTS WHERE email = ?", (email,))
            user = cursor.fetchone()
            if user:
                flash("E-Mail already in use!", "danger")
                return redirect(url_for('sign_up'))

        if password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for('sign_up'))

        hashed_password = generate_password_hash(password)
        with sqlite3.connect("database.db") as users:
            cursor = users.cursor()
            cursor.execute("INSERT INTO PARTICIPANTS \
            (username,email,password) VALUES (?,?,?)",
                           (username, email, hashed_password))
            users.commit()
        flash("Account created! Please log in.", "success")
        return redirect(url_for('login'))

    return render_template('sign_up.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        flash('Already logged in!', 'warning')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form['enteredEmail']
        password = request.form['enteredPassword']

        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, password FROM PARTICIPANTS WHERE email = ?", (email,))
            user = cursor.fetchone()

        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password", "danger")

    return render_template("login.html")

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        flash("Please log in!", 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_new_password']

        # Update email and username
        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE PARTICIPANTS SET email = ?, username = ? WHERE id = ?",
                (email, username, session['user_id']))
            conn.commit()

        session['username'] = username

        # If user wants to change password
        if password and new_password:
            # Verify current password first
            with sqlite3.connect("database.db") as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT password FROM PARTICIPANTS WHERE id = ?", (session['user_id'],))
                user = cursor.fetchone()

            if not check_password_hash(user[0], password):
                flash("Current password is incorrect!", "danger")
                return redirect(url_for('profile'))

            if new_password != confirm_password:
                flash("New passwords do not match!", "danger")
                return redirect(url_for('profile'))

            hashed_password = generate_password_hash(new_password)
            with sqlite3.connect("database.db") as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE PARTICIPANTS SET password = ? WHERE id = ?",
                    (hashed_password, session['user_id']))
                conn.commit()

            flash("Password updated!", "success")
        else:
            flash("Profile updated!", "success")

        return redirect(url_for('dashboard'))

    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT email, username FROM PARTICIPANTS WHERE id = ?", (session['user_id'],))
        user = cursor.fetchone()

    return render_template('profile.html', user=user)

@app.route('/delete-task/<int:task_id>')
def delete_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM TASKS WHERE id = ? AND user_id = ?", (task_id, session['user_id']))
        conn.commit()

    flash("Task deleted", "info")
    return redirect(url_for('dashboard'))

@app.route('/edit-log/<int:task_id>', methods=['GET', 'POST'])
def edit_log(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        expense_name = request.form['ExpenseName']
        amount = request.form['Amount']
        note = request.form['Note']
        date_of = request.form['Date']
        type = request.form['Type']
        category = request.form['Category']

        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE TASKS SET expense_name = ?, amount=?, note = ?, date_of = ?, type = ?, category = ? WHERE id = ? AND user_id = ?",
                (expense_name, amount, note, date_of, type, category, task_id, session['user_id'])
            )
            conn.commit()

        flash("Expense updated!", "success")
        return redirect(url_for('dashboard'))

    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM TASKS WHERE id = ? AND user_id = ?", (task_id, session['user_id']))
        task = cursor.fetchone()

    return render_template('edit_log.html', task=task)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True, port=5001)