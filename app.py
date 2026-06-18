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
            type TEXT DEFAULT 'medium',
            category TEXT DEFAULT 'medium',
            FOREIGN KEY (user_id) REFERENCES PARTICIPANTS(id)
        )
        """)
init_db()

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
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
                "INSERT INTO TASKS (user_id, expense_name, amount, note, date_of, type, category) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (session['user_id'], expense_name, amount, note, date_of, type, category)
            )
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


    if filter_type == 'expense':
        query += " AND type = 'expense'"
    elif filter_type == 'income':
        query += " AND type = 'income'"

    if filter_category == 'work':
        query += " AND category = 'work'"
    elif filter_category == 'home':
        query += " AND category = 'home'"
    elif filter_category == 'personal':
        query += " AND category = 'personal'"


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
    params_base = [session['user_id']]

    if selected_year != 'all' and selected_month != 'all':
        date_filter = " AND date_of LIKE ?"
        params_base.append(f"{selected_year}-{selected_month}%")
    elif selected_year != 'all':
        date_filter = " AND date_of LIKE ?"
        params_base.append(f"{selected_year}%")
    elif selected_month != 'all':
        date_filter = " AND strftime('%m', date_of) = ?"
        params_base.append(selected_month)

    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()

        cursor.execute(
            f"SELECT category, SUM(amount) FROM TASKS WHERE type = 'expense' AND user_id = ?{date_filter} GROUP BY category",
            params_base)
        expense_totals = {row[0]: row[1] for row in cursor.fetchall()}

        cursor.execute(
            f"SELECT category, SUM(amount) FROM TASKS WHERE type = 'income' AND user_id = ?{date_filter} GROUP BY category",
            params_base)
        income_totals = {row[0]: row[1] for row in cursor.fetchall()}

    return render_template('analyze.html',
                           home_expense=expense_totals.get('home', 0),
                           work_expense=expense_totals.get('work', 0),
                           personal_expense=expense_totals.get('personal', 0),
                           home_income=income_totals.get('home', 0),
                           work_income=income_totals.get('work', 0),
                           personal_income=income_totals.get('personal', 0),
                           selected_month=selected_month,
                           selected_year=selected_year)

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