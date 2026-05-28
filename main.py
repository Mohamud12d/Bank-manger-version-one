"""
main.py — Entry point for the Bank System CLI

How the program is structured:
  - Each menu option calls one small function
  - Each function handles: input → action → save → feedback
  - try/except wraps every banking operation so errors never crash the program
  - current_user tracks who is logged in (None = nobody)

Run with:  python main.py
"""

import getpass
import os
from bank import Bank
from customer import Customer
from account import Account

# -----------------------------------------------------------------------
# Session — tracks who is logged in
# -----------------------------------------------------------------------

# This is the "session variable". When nobody is logged in it's None.
# After a successful login it holds the Customer object.
current_user = None


# ---------------------------------------------------------------
# ---------------------------------------------------------------------
# Helper utilities
# ----------
def clear_screen():
    """Clear the terminal so each menu looks fresh."""
    os.system("cls" if os.name == "nt" else "clear")


def print_header(title):
    """Print a consistent section header."""
    print(f"\n{'=' * 50}")
    print(f"  {title}")
    print(f"{'=' * 50}")


def get_int_input(prompt):
    """
    Keep asking until the user enters a valid integer.
    This prevents the program crashing when someone types letters.
    """
    while True:
        try:
            return int(input(prompt))
        except ValueError:
            print("  Please enter a whole number.")


def get_float_input(prompt):
    """Keep asking until the user enters a valid decimal number."""
    while True:
        try:
            value = float(input(prompt))
            return value
        except ValueError:
            print("  Please enter a valid amount (e.g. 100 or 50.50).")


def pick_account(customer):
    """
    Show the customer's accounts and let them pick one by number.
    Returns the selected Account object, or None if they cancel.
    """
    if not customer.accounts:
        print("  You have no accounts.")
        return None

    print("\n  Your accounts:")
    for i, acc in enumerate(customer.accounts, 1):
        print(f"    {i}. {acc.account_type.capitalize():10} "
              f"#{acc.account_number}   "
              f"Balance: ${acc.get_balance():.2f}")
    print(f"    0. Cancel")

    choice = get_int_input("  Select account: ")
    if choice == 0:
        return None
    if 1 <= choice <= len(customer.accounts):
        return customer.accounts[choice - 1]

    print("  Invalid selection.")
    return None


# -----------------------------------------------------------------------
# Authentication
# -----------------------------------------------------------------------

def login(bank):
    """
    Authenticate a customer.
    Sets the global current_user on success.
    """
    global current_user
    print_header("Login")
    try:
        cid = get_int_input("  Customer ID: ")
        # getpass hides the password while typing — it won't show on screen
        pwd = getpass.getpass("  Password: ")
        customer = bank.get_customer(cid)
        if customer.password == pwd:
            current_user = customer
            print(f"\n  Welcome back, {current_user.owner}!")
        else:
            print("  Incorrect password.")
    except ValueError as e:
        print(f"  Login failed: {e}")


def logout():
    """Clear the session — set current_user back to None."""
    global current_user
    name = current_user.owner
    current_user = None
    print(f"\n  Goodbye, {name}. Logged out.")


# -----------------------------------------------------------------------
# Customer features
# -----------------------------------------------------------------------

def show_dashboard():
    """
    Display a formatted balance summary for the logged-in customer.
    Demonstrates f-string alignment: :.2f for 2 decimal places,
    :>10 to right-align in a 10-character wide column.
    """
    print_header(f"Dashboard — {current_user.owner}")
    if not current_user.accounts:
        print("  No accounts found.")
        return

    total = 0
    print(f"\n  {'Type':<12} {'Account #':<12} {'Balance':>12}")
    print(f"  {'-'*12} {'-'*12} {'-'*12}")
    for acc in current_user.accounts:
        bal = acc.get_balance()
        total += bal
        print(f"  {acc.account_type.capitalize():<12} "
              f"#{acc.account_number:<11} "
              f"${bal:>11.2f}")
    print(f"  {'-'*12} {'-'*12} {'-'*12}")
    print(f"  {'TOTAL':<25} ${total:>11.2f}\n")


def do_deposit(bank):
    """Handle a deposit: pick account → enter amount → save."""
    print_header("Deposit")
    account = pick_account(current_user)
    if account is None:
        return
    amount = get_float_input("  Amount to deposit: $")
    try:
        account.deposit(amount)
        bank.save_to_file()
        print(f"  Deposited ${amount:.2f}. New balance: ${account.get_balance():.2f}")
    except ValueError as e:
        print(f"  Error: {e}")


def do_withdraw(bank):
    """Handle a withdrawal: pick account → enter amount → save."""
    print_header("Withdraw")
    account = pick_account(current_user)
    if account is None:
        return
    amount = get_float_input("  Amount to withdraw: $")
    try:
        account.withdraw(amount)
        bank.save_to_file()
        print(f"  Withdrew ${amount:.2f}. New balance: ${account.get_balance():.2f}")
    except ValueError as e:
        print(f"  Error: {e}")


def do_transfer(bank):
    """
    Transfer money between accounts.
    The Bank now handles the lookup — we just pass IDs and the amount.
    """
    print_header("Transfer")
    print("  -- Source account --")
    from_account = pick_account(current_user)
    if from_account is None:
        return

    print("\n  -- Destination --")
    to_cid = get_int_input("  Destination customer ID: ")
    to_acc_num = get_int_input("  Destination account number: ")
    amount = get_float_input("  Amount to transfer: $")

    try:
        bank.transfer(
            current_user.customer_id,
            from_account.account_number,
            to_cid,
            to_acc_num,
            amount
        )
        bank.save_to_file()
        print(f"  Transferred ${amount:.2f} successfully.")
    except ValueError as e:
        print(f"  Error: {e}")


def view_transaction_history():
    """
    Show filtered transaction history for a chosen account.
    Introduces list comprehensions through Account's filter methods.
    """
    print_header("Transaction History")
    account = pick_account(current_user)
    if account is None:
        return

    print("\n  Filter:  1. All   2. Deposits only   3. Withdrawals only")
    choice = input("  Your choice (default All): ").strip()
    filter_map = {"1": "all", "2": "deposits", "3": "withdrawals"}
    filter_type = filter_map.get(choice, "all")

    transactions = account.get_transaction_history(filter_type)

    print(f"\n  Account #{account.account_number} — "
          f"{filter_type.capitalize()} transactions:\n")
    if not transactions:
        print("  No transactions found.")
    else:
        print(f"  {'Date':<12} {'Type':<10} {'Amount':>10}")
        print(f"  {'-'*12} {'-'*10} {'-'*10}")
        for t in transactions:
            symbol = "+" if t["type"] == "deposit" else "-"
            print(f"  {t['date']:<12} {t['type'].capitalize():<10} "
                  f"{symbol}${t['amount']:>9.2f}")
    print()


def do_generate_statement():
    """Generate a .txt account statement file for a chosen account."""
    print_header("Generate Statement")
    account = pick_account(current_user)
    if account is None:
        return
    filename = account.generate_statement(current_user.owner)
    print(f"  Statement saved to: {filename}")


def do_change_password(bank):
    """Let the customer change their own password with validation."""
    print_header("Change Password")
    try:
        old = getpass.getpass("  Current password: ")
        new = getpass.getpass("  New password (min 6 chars): ")
        confirm = getpass.getpass("  Confirm new password: ")
        if new != confirm:
            print("  Passwords do not match. No changes made.")
            return
        current_user.update_password(old, new)
        bank.save_to_file()
        print("  Password updated successfully.")
    except ValueError as e:
        print(f"  Error: {e}")


def do_open_account(bank):
    """Let the customer open a new account (saving or current)."""
    print_header("Open New Account")
    print("  Account types:  1. Saving   2. Current")
    choice = input("  Choose type: ").strip()
    type_map = {"1": "saving", "2": "current"}
    account_type = type_map.get(choice)
    if not account_type:
        print("  Invalid choice.")
        return
    new_acc = current_user.create_account(account_type)
    bank.save_to_file()
    print(f"  New {account_type} account created. Account number: #{new_acc.account_number}")



# -----------------------------------------------------------------------
# Admin features
# -----------------------------------------------------------------------

def admin_view_all_accounts(bank):
    """Admin: print every customer and their accounts."""
    bank.view_all_accounts()


def admin_view_all_transactions(bank):
    """Admin: show every transaction across the entire bank."""
    print_header("All Transactions — Audit Log")
    transactions = bank.get_all_transactions()
    if not transactions:
        print("  No transactions recorded yet.\n")
        return
    print(f"\n  {'Customer':<12} {'Acct #':<8} {'Date':<12} {'Type':<10} {'Amount':>10}")
    print(f"  {'-'*12} {'-'*8} {'-'*12} {'-'*10} {'-'*10}")
    for t in transactions:
        symbol = "+" if t["type"] == "deposit" else "-"
        print(f"  {t['customer']:<12} #{t['account_number']:<7} "
              f"{t['date']:<12} {t['type'].capitalize():<10} "
              f"{symbol}${t['amount']:>9.2f}")
    print()


def admin_add_customer(bank):
    """Admin: register a new customer with a generated or chosen ID."""
    print_header("Add New Customer")
    name = input("  Customer name: ").strip()
    if not name:
        print("  Name cannot be empty.")
        return

    # Keep asking until the admin provides an unused ID
    while True:
        cid = get_int_input("  Customer ID (must be unique): ")
        if bank.customer_id_exists(cid):
            print(f"  ID {cid} is already taken. Try another.")
        else:
            break

    pwd = getpass.getpass("  Temporary password (min 6 chars): ")
    if len(pwd) < 6:
        print("  Password too short. Customer not created.")
        return

    role_input = input("  Role — 1. Customer   2. Admin (default: Customer): ").strip()
    role = "admin" if role_input == "2" else "customer"

    try:
        new_customer = Customer(name, cid, pwd, role)
        bank.add_customer(new_customer)
        bank.save_to_file()
        print(f"  Customer '{name}' (ID: {cid}, role: {role}) added successfully.")
    except ValueError as e:
        print(f"  Error: {e}")


def admin_remove_customer(bank):
    """Admin: delete a customer from the bank by ID."""
    print_header("Remove Customer")
    bank.view_all_accounts()   # show the list first so admin can pick an ID
    cid = get_int_input("  Enter customer ID to remove: ")
    if cid == current_user.customer_id:
        print("  You cannot remove your own account while logged in.")
        return
    confirm = input(f"  Are you sure? Type YES to confirm: ").strip()
    if confirm != "YES":
        print("  Cancelled.")
        return
    try:
        removed_name = bank.remove_customer(cid)
        bank.save_to_file()
        print(f"  Customer '{removed_name}' removed successfully.")
    except ValueError as e:
        print(f"  Error: {e}")


# -----------------------------------------------------------------------
# Menus
# -----------------------------------------------------------------------

def customer_menu(bank):
    """
    The menu loop for a regular customer.
    Shows options, reads the choice, calls the matching function.
    Loops until the user chooses to log out.
    """
    while True:
        print_header(f"Customer Menu — {current_user.owner}")
        print("  1. View dashboard (balances)")
        print("  2. Deposit")
        print("  3. Withdraw")
        print("  4. Transfer")
        print("  5. Transaction history")
        print("  6. Generate account statement")
        print("  7. Open new account")
        print("  8. Change password")
        print("  0. Logout")
        print()

        choice = input("  Choose an option: ").strip()
        print()

        if choice == "1":
            show_dashboard()
        elif choice == "2":
            do_deposit(bank)
        elif choice == "3":
            do_withdraw(bank)
        elif choice == "4":
            do_transfer(bank)
        elif choice == "5":
            view_transaction_history()
        elif choice == "6":
            do_generate_statement()
        elif choice == "7":
            do_open_account(bank)
        elif choice == "8":
            do_change_password(bank)
        elif choice == "0":
            logout()
            break
        else:
            print("  Invalid option. Please try again.")

        input("\n  Press Enter to continue...")


def admin_menu(bank):
    """
    The menu loop for an admin user.
    Admins see both their own banking options and admin-only actions.
    """
    while True:
        print_header(f"Admin Menu — {current_user.owner}")
        print()
        print("  --- Admin only ---")
        print("  1.  View all customer accounts")
        print("  2. View all transactions (audit log)")
        print("  3. Add new customer")
        print("  4. Remove customer")
        print()
        print("  0. Logout")
        print()

        choice = input("  Choose an option: ").strip()
        print()

        if choice == "1":
            admin_view_all_accounts(bank)
        elif choice == "2":
            admin_view_all_transactions(bank)
        elif choice == "3":
            admin_add_customer(bank)
        elif choice == "4":
            admin_remove_customer(bank)
        elif choice == "0":
            logout()
            break
        else:
            print("  Invalid option. Please try again.")

        input("\n  Press Enter to continue...")


def main_menu(bank):
    """
    The outermost menu — shown before anyone is logged in.
    Only offers Login or Exit.
    """
    while True:
        print_header(f"Welcome to {bank.name}")
        print("  1. Login")
        print("  0. Exit")
        print()
        choice = input("  Choose an option: ").strip()
        print()

        if choice == "1":
            login(bank)
            if current_user is not None:
                # Route to the right menu based on role
                if current_user.is_admin():
                    admin_menu(bank)
                else:
                    customer_menu(bank)
        elif choice == "0":
            print("  Thank you for banking with us. Goodbye!\n")
            break
        else:
            print("  Invalid option.")


# -----------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------

if __name__ == "__main__":
    # Load existing data or create a fresh bank on first run
    bank = Bank.load_from_file("bank.json")
    main_menu(bank)
