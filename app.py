import os
from bson import ObjectId
from flask import Flask,render_template, request, redirect, url_for, flash, session, current_app
from decimal import Decimal, InvalidOperation
from collections import defaultdict
from mongoengine import connect
from models import Transaction, User, Account
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)              
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-prod")
try:
    connect(
        db='Expense_Tracker',
        host='localhost',
        port=27017
    )
except Exception as e:
    print("Database connection failed:", e)

@app.route('/')
def home():
    return redirect(url_for('login'))

#------------------- CONTEXT PROCESSOR ---------------
@app.context_processor
def inject_user():
    if 'user_id' in session:
        user = User.objects(id=session['user_id']).first()
        return dict(user=user)
    return dict(user=None)

@app.context_processor
def inject_user_balance():
    if 'user_id' not in session:
        return dict(global_balance=0)

    user = User.objects(id=session['user_id']).first()
    if not user:
        return dict(global_balance=0)

    # ✅ Much faster — uses aggregated account balances
    accounts = Account.objects(user=user)
    balance = sum(a.amount for a in accounts)

    return dict(global_balance=round(balance, 2))

#----------------- Dashboard -------------------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.objects(id=session['user_id']).first()
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('logout'))

    # Fetch all transactions once
    transactions = Transaction.objects(user=user)

    total_income = 0.0
    total_expenses = 0.0
    income_categories = defaultdict(float)
    expense_categories = defaultdict(float)

    # ✅ Single-pass clean logic
    for t in transactions:
        ttype = t.transaction_type.lower()
        amount = float(t.amount)  # ensure numeric

        if ttype == "income":
            total_income += amount
            income_categories[t.category] += amount

        elif ttype == "expense":
            total_expenses += amount
            expense_categories[t.category] += amount

    total_transactions = len(transactions)
    balance = total_income - total_expenses

    # ✅ Unified color list
    color_list = [
        "#007bff", "#dc3545", "#ffc107", "#28a745",
        "#6610f2", "#20c997", "#fd7e14", "#6c757d"
    ]

    # ✅ Prepare legend + chart for expenses only (pie chart)
    chart_labels = []
    chart_values = []
    chart_colors = []

    expense_total = sum(expense_categories.values())
    expense_legend = []

    for i, (cat, amt) in enumerate(expense_categories.items()):
        color = color_list[i % len(color_list)]
        percent = (amt / expense_total * 100) if expense_total else 0

        chart_labels.append(cat)
        chart_values.append(round(amt, 2))
        chart_colors.append(color)

        expense_legend.append({
            "name": cat,
            "amount": round(amt, 2),
            "percent": round(percent, 2),
            "color": color
        })

    # ✅ Income legend (no chart)
    income_legend = []
    income_total = sum(income_categories.values())

    for i, (cat, amt) in enumerate(income_categories.items()):
        color = color_list[i % len(color_list)]
        percent = (amt / income_total * 100) if income_total else 0

        income_legend.append({
            "name": cat,
            "amount": round(amt, 2),
            "percent": round(percent, 2),
            "color": color
        })

    return render_template(
        'dashboard.html',
        username=user.name,
        user=user,
        total_income=round(total_income, 2),
        total_expenses=round(total_expenses, 2),
        total_transactions=total_transactions,
        balance=round(balance, 2),

        # Chart data
        income_labels=list(income_categories.keys()),
        income_values=list(income_categories.values()),
        income_colors=[color_list[i % len(color_list)] for i in range(len(income_categories))],

        expense_labels=list(expense_categories.keys()),
        expense_values=list(expense_categories.values()),
        expense_colors=[color_list[i % len(color_list)] for i in range(len(expense_categories))],

        # Legend
        chart_labels=chart_labels,
        chart_values=chart_values,
        chart_colors=chart_colors,
        income_legend=income_legend,
        expense_legend=expense_legend)


#---------------- LOGIN ------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''

        # Basic validation
        if not email or not password:
            flash('Please enter both email and password.', 'danger')
            return render_template('login.html')

        # Fetch user
        user = User.objects(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            flash('Invalid email or password.', 'danger')
            return render_template('login.html')

        # Login success
        session['user_id'] = str(user.id)
        session['user_name'] = user.name  # for navbar
        flash('Login successful!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('login.html')

#---------------- Signup -------------------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''

        # Basic validations
        if not name:
            flash('Name is required.', 'danger')
            return render_template('signup.html')

        if not email:
            flash('Email is required.', 'danger')
            return render_template('signup.html')

        if '@' not in email:
            flash('Please enter a valid email.', 'danger')
            return render_template('signup.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('signup.html')

        # Check duplicate email
        if User.objects(email=email).first():
            flash('Email already registered. Please log in.', 'warning')
            return redirect(url_for('login'))

        # Create user
        password_hash = generate_password_hash(password)
        User(name=name, email=email, password_hash=password_hash).save()

        flash('Signup successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')

#--------------- ADD NEW ACCOUNT -------------------------
@app.route('/add_accounts', methods=['GET','POST'])
def add_accounts():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.objects(id=session['user_id']).first()

    if request.method == 'POST':
        account_name = request.form['account_name']
        raw_amount = request.form.get('amount', '').strip()
        try:
            amount = float(raw_amount) if raw_amount else 0.0
        except ValueError:
            flash('Invalid amount entered. Please enter a number.', 'danger')
            return render_template('add_account.html', user=user)

        Account(user=user,account_name=account_name,amount=amount).save()
        flash('Account added successfully!', 'success')
        return redirect(url_for('accounts'))

    return render_template('add_account.html',user=user)


#---------------- ADD NEW TRANSACTION ----------------
@app.route('/add_transaction', methods=['GET', 'POST'])
def add_transaction():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.objects(id=session['user_id']).first()
    if not user:
        session.clear()
        return redirect(url_for('login'))

    if request.method == 'POST':
        ttype = (request.form.get('transaction_type') or '').strip().lower()
        amount_raw = (request.form.get('amount') or '').strip()
        category = (request.form.get('category') or '').strip()
        description = (request.form.get('description') or '').strip()
        date_str = (request.form.get('date') or '').strip()
        account_id = (request.form.get('account_id') or '').strip()

        # Validate type
        if ttype not in ('income', 'expense'):
            flash('Invalid transaction type.', 'danger')
            return redirect(url_for('add_transaction'))

        # Validate numeric amount
        try:
            amt = float(amount_raw)
            if amt <= 0:
                raise ValueError
        except ValueError:
            flash('Enter a valid positive amount.', 'danger')
            return redirect(url_for('add_transaction'))

        # Validate category
        if not category:
            flash('Category cannot be empty.', 'danger')
            return redirect(url_for('add_transaction'))

        # Validate account
        if not ObjectId.is_valid(account_id):
            flash('Invalid account.', 'danger')
            return redirect(url_for('add_transaction'))

        account = Account.objects(id=account_id, user=user).first()
        if not account:
            flash('Account not found.', 'danger')
            return redirect(url_for('add_transaction'))

        # Parse date
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d') if date_str else datetime.utcnow()
        except ValueError:
            flash('Invalid date format.', 'danger')
            return redirect(url_for('add_transaction'))

        # Determine amount sign for storage
        # We store EXPENSE as negative amount, INCOME as positive
        stored_amount = -amt if ttype == 'expense' else amt

        # Delta to balance is same as stored_amount
        delta = stored_amount

        # Create transaction
        tx = Transaction(
            user=user,
            transaction_type=ttype,
            account=account,
            amount=stored_amount,
            category=category,
            description=description,
            date=date
        ).save()

        # Update account balance atomically
        Account.objects(id=account.id).update_one(inc__amount=delta)

        flash('Transaction added successfully!', 'success')
        return redirect(url_for('view_account', account_id=str(account.id)))

    # GET → form display
    accounts = Account.objects(user=user)
    return render_template('add_transaction.html', user=user, accounts=accounts)
 
#---------------- ACCOUNTS -----------------------------
@app.route('/accounts')
def accounts():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.objects(id=session['user_id']).first()
    if not user:
        return redirect(url_for('login'))
    
    accounts = Account.objects(user=user)
    return render_template('accounts.html', accounts=accounts, user=user)

#--------------------- View Account ------------------------------
@app.route('/accounts/<account_id>', methods=['GET'])
def view_account(account_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.objects(id=session['user_id']).first()
    if not user:
        session.pop('user_id', None)
        return redirect(url_for('login'))

    account = Account.objects(id=account_id, user=user).first()
    if not account:
        flash('Account not found or access denied.', 'warning')
        return redirect(url_for('accounts'))

    transactions_qs = Transaction.objects(account=account).order_by('-date')
    total_tx = transactions_qs.count()

    return render_template(
        'view_account.html',
        account=account,
        transactions=transactions_qs,
        total_tx=total_tx,
        user=user
    )

# ------------------- Delete Account --------------------------
@app.route('/accounts/<string:account_id>/delete', methods=['POST'])
def delete_account(account_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.objects(id=session['user_id']).first()
    if not user:
        return redirect(url_for('login'))

    account = Account.objects(id=account_id, user=user).first()
    if not account:
        flash('Account not found or access denied.', 'warning')
        return redirect(url_for('accounts'))

    # Cascade delete: delete all transactions first
    Transaction.objects(account=account).delete()
    account.delete()

    flash('Account deleted successfully (all transactions removed).', 'success')
    return redirect(url_for('accounts'))

#------------------------ Edit account --------------------------
@app.route('/account/<string:account_id>/edit', methods=['GET', 'POST'])
def edit_account(account_id):
    # Require login
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.objects(id=session['user_id']).first()
    if not user:
        session.clear()
        return redirect(url_for('login'))

    # Validate valid object ID
    if not ObjectId.is_valid(account_id):
        flash("Invalid account ID.", "danger")
        return redirect(url_for('accounts'))

    # Fetch account
    account = Account.objects(id=account_id, user=user).first()
    if not account:
        flash("Account not found or access denied.", "danger")
        return redirect(url_for('accounts'))

    # GET → show form
    if request.method == 'GET':
        return render_template('edit_account.html', account=account, user=user)

    # POST → update name only
    new_name = (request.form.get('account_name') or "").strip()

    if not new_name:
        flash("Account name cannot be empty.", "danger")
        return redirect(url_for('edit_account', account_id=account.id))

    if len(new_name) > 100:
        flash("Account name too long (max 100 characters).", "danger")
        return redirect(url_for('edit_account', account_id=account.id))

    # Update name
    account.update(set__account_name=new_name)

    flash("Account name updated successfully!", "success")
    return redirect(url_for('accounts'))


#----------------------- Edit Transaction -------------------------
@app.route('/account/<string:account_id>/transactions/<string:tx_id>/edit', methods=['GET', 'POST'])
def edit_transaction(account_id, tx_id):
    # 1) auth
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.objects(id=session['user_id']).first()
    
    if not user:
        session.pop('user_id', None)
        return redirect(url_for('login'))

    # 2) validate ids
    if not ObjectId.is_valid(account_id) or not ObjectId.is_valid(tx_id):
        flash('Invalid ID provided.', 'danger')
        return redirect(url_for('accounts'))

    # 3) ownership checks
    account = Account.objects(id=account_id, user=user).first()
    if not account:
        flash('Account not found or access denied.', 'danger')
        return redirect(url_for('accounts'))

    tx = Transaction.objects(id=tx_id, account=account).first()
    if not tx:
        flash('Transaction not found.', 'warning')
        return redirect(url_for('view_account', account_id=account.id))

    if request.method == 'GET':
        # Pre-fill the form
        return render_template('edit_transaction.html', account=account, tx=tx,user=user)

    # POST: validate inputs
    ttype = (request.form.get('transaction_type') or '').strip().lower()
    amount_raw = (request.form.get('amount') or '').strip()
    category = (request.form.get('category') or '').strip()
    date_str = (request.form.get('date') or '').strip()

    if ttype not in ('expense', 'income'):
        flash('Invalid transaction type.', 'danger')
        return redirect(url_for('edit_transaction', account_id=account.id, tx_id=tx.id))

    try:
        new_amount_dec = Decimal(amount_raw)
        if new_amount_dec <= 0:
            raise ValueError('Amount must be positive.')
    except (InvalidOperation, ValueError):
        flash('Enter a valid positive amount.', 'danger')
        return redirect(url_for('edit_transaction', account_id=account.id, tx_id=tx.id))

    try:
        new_date = datetime.strptime(date_str, '%Y-%m-%d') if date_str else tx.date
    except ValueError:
        flash('Invalid date format. Use YYYY-MM-DD.', 'danger')
        return redirect(url_for('edit_transaction', account_id=account.id, tx_id=tx.id))

    # 4) compute balance difference: (new_effect - old_effect)
    # old_effect from existing tx
    old_amt = abs(float(tx.amount))          # tx.amount should already be positive in your app
    old_type = (getattr(tx, 'transaction_type', '') or '').lower()
    old_effect = -old_amt if old_type == 'expense' else +old_amt

    # new_effect from form
    new_amt = float(new_amount_dec)
    new_effect = -new_amt if ttype == 'expense' else +new_amt

    diff = new_effect - old_effect  # what to apply to Account.amount

    try:
        # 5) update account balance atomically
        if diff != 0:
            Account.objects(id=account.id).update_one(inc__amount=diff)

        # 6) save tx fields
        tx.update(
            set__amount=new_amt,                # keep amount positive
            set__transaction_type=ttype,        # 'expense' or 'income'
            set__category=category or None,
            set__date=new_date
        )

        flash('Transaction updated.', 'success')
    except Exception as e:
        current_app.logger.exception('Edit transaction failed: %s', e)
        flash('Could not update transaction. Try again.', 'danger')

    return redirect(url_for('view_account', account_id=account.id))

#------------------ Delete Transaction ------------------
@app.route('/account/<string:account_id>/transactions/<string:tx_id>/delete', methods=['POST'])
def delete_transaction(account_id, tx_id):
    # Require login
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.objects(id=session['user_id']).first()
    if not user:
        session.clear()
        return redirect(url_for('login'))

    # Validate IDs
    if not ObjectId.is_valid(account_id) or not ObjectId.is_valid(tx_id):
        flash("Invalid ID.", "danger")
        return redirect(url_for('accounts'))

    # Account ownership check
    account = Account.objects(id=account_id, user=user).first()
    if not account:
        flash("Account not found or access denied.", "danger")
        return redirect(url_for('accounts'))

    # Transaction must belong to this account
    tx = Transaction.objects(id=tx_id, account=account).first()
    if not tx:
        flash("Transaction not found.", "warning")
        return redirect(url_for('view_account', account_id=account.id))

    try:
        # Reverse the transaction effect
        reverse_delta = -float(tx.amount)    # Because amounts are stored signed

        # Update account
        Account.objects(id=account.id).update_one(inc__amount=reverse_delta)

        # Delete the transaction
        tx.delete()

        flash("Transaction deleted successfully.", "success")

    except Exception as e:
        current_app.logger.exception("Delete tx failed: %s", e)
        flash("Error deleting transaction.", "danger")

    return redirect(url_for('view_account', account_id=account.id))

# ----------------- HISTORY ---------------------------
@app.route('/history', methods=['GET'])
def get_history():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.objects(id=session['user_id']).first()
    if not user:
        return {"error": "User not found."}, 404

    account_id = request.args.get("account_id")
    category = request.args.get("category")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    query = Transaction.objects(user=user)

    if account_id:
        query = query.filter(account=account_id)
    if category:
        query = query.filter(category=category)
    if start_date and end_date:
        try:
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)
            query = query.filter(date__gte=start, date__lte=end)
        except ValueError:
            return {"error": "Invalid date format. Use YYYY-MM-DD"}, 400

    transactions = query.order_by("-date")

    return {
        "transactions": [
            {
                "id": str(t.id),
                "account": str(t.account.account_name) if t.account else None,
                "transaction_type": t.transaction_type,
                "amount": t.amount,
                "category": t.category,
                "description": t.description or "",
                "date": t.date.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for t in transactions
        ]
    }
#-------------- HISTORY PAGE API -----------------
@app.route('/history_page')
def history_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.objects(id=session['user_id']).first()

    return render_template("history.html", username=session['user_name'],user=user)

#--------------------- Edit Profile -----------------
@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.objects(id=session['user_id']).first()
    if not user:
        session.clear()
        return redirect(url_for('login'))

    if request.method == 'GET':
        # Render profile form with current name
        return render_template('edit_profile.html', user=user)

    # POST: update name
    new_name = (request.form.get('name') or '').strip()

    if not new_name:
        flash('Name cannot be empty.', 'danger')
        return redirect(url_for('profile'))
    if len(new_name) > 100:
        flash('Name is too long (max 100 characters).', 'danger')
        return redirect(url_for('edit_profile'))

    # Persist + sync session display name
    user.update(set__name=new_name)
    session['user_name'] = new_name

    flash('Profile updated successfully.', 'success')
    return redirect(url_for('edit_profile'))

#--------------- LOGOUT ---------------------------------
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True,port=5000)




