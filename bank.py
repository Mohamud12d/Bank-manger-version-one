import json
import os
from account import Account
from customer import Customer


class Bank:
    """
    Represents the bank — the top-level container for all customers.

    Changes from the original:
    - transfer() now looks up accounts by customer/account ID instead of
      requiring the caller to pass account objects directly
    - Added: remove_customer()
    - Added: view_all_accounts() for admin overview
    - Added: get_all_transactions() for admin transaction log
    - load_from_file() now delegates to Customer.from_dict() and Account.from_dict()
      instead of reconstructing objects manually
    """

    def __init__(self, name):
        self.name = name
        self.customers = []

    # ------------------------------------------------------------------
    # Customer management
    # ------------------------------------------------------------------

    def add_customer(self, customer):
        """Add a Customer object to the bank's list."""
        self.customers.append(customer)

    def remove_customer(self, customer_id):
        """
        Find a customer by ID and remove them from the bank.
        Loops through the list, finds the match, removes it, then returns.
        """
        for customer in self.customers:
            if customer.customer_id == customer_id:
                self.customers.remove(customer)
                return customer.owner   # return the name so the caller can confirm
        raise ValueError(f"Customer with ID {customer_id} not found.")

    def get_customer(self, customer_id):
        """Return a Customer by their ID. Raises ValueError if not found."""
        for c in self.customers:
            if c.customer_id == customer_id:
                return c
        raise ValueError("Customer not found.")

    def customer_id_exists(self, customer_id):
        """Check if a customer ID is already taken (used when adding new customers)."""
        return any(c.customer_id == customer_id for c in self.customers)

    # ------------------------------------------------------------------
    # Banking operations
    # ------------------------------------------------------------------

    def transfer(self, from_customer_id, from_account_number,
                 to_customer_id, to_account_number, amount):
        """
        Transfer money between two accounts.

        The bank now looks up both accounts itself using IDs — this is safer
        than the original which required passing account objects directly,
        because it prevents transferring between accounts at different banks.
        """
        if amount <= 0:
            raise ValueError("Transfer amount must be greater than 0.")

        from_customer = self.get_customer(from_customer_id)
        to_customer = self.get_customer(to_customer_id)
        from_account = from_customer.get_account(from_account_number)
        to_account = to_customer.get_account(to_account_number)

        # withdraw first — if it fails (insufficient funds, daily limit), deposit never runs
        from_account.withdraw(amount)
        to_account.deposit(amount)

    # ------------------------------------------------------------------
    # Admin views
    # ------------------------------------------------------------------

    def view_all_accounts(self):
        """
        Print a formatted overview of every customer and their accounts.
        Uses a nested loop: one loop for customers, one inside it for accounts.
        """
        print(f"\n{'=' * 50}")
        print(f"  {self.name}  —  All Customer Accounts")
        print(f"{'=' * 50}")
        for customer in self.customers:
            role_label = "[ADMIN]" if customer.is_admin() else "[customer]"
            print(f"\n  {role_label} {customer.owner}  (ID: {customer.customer_id})")
            if not customer.accounts:
                print("    No accounts.")
            for acc in customer.accounts:
                print(f"    • {acc.account_type.capitalize():10} "
                      f"#{acc.account_number}   "
                      f"Balance: ${acc.get_balance():>10.2f}")
        print(f"\n{'=' * 50}\n")

    def get_all_transactions(self):
        """
        Return a flat list of all transactions across every account,
        each tagged with the customer and account number for context.
        Useful for an admin audit log.
        """
        all_transactions = []
        for customer in self.customers:
            for acc in customer.accounts:
                for t in acc.transactions:
                    # Attach extra context since the transaction dict doesn't know who owns it
                    all_transactions.append({
                        "customer": customer.owner,
                        "account_number": acc.account_number,
                        **t   # unpack the existing transaction dict fields into this one
                    })
        return all_transactions

    # ------------------------------------------------------------------
    # Persistence (saving and loading)
    # ------------------------------------------------------------------

    def to_dict(self):
        return {
            "name": self.name,
            "customers": [c.to_dict() for c in self.customers]
        }

    def save_to_file(self, file_name="bank.json"):
        """Save the entire bank state to a JSON file."""
        with open(file_name, "w") as f:
            json.dump(self.to_dict(), f, indent=4)

    @staticmethod
    def load_from_file(file_name="bank.json"):
        """
        Load the bank state from a JSON file.
        Now uses Customer.from_dict() instead of rebuilding objects manually here —
        so if Customer changes, only customer.py needs updating.
        """
        if not os.path.exists(file_name):
            # First run: create a default admin account so someone can log in
            print("No bank.json found — creating a fresh bank with a default admin.")
            bank = Bank("MyBank")
            admin = Customer("Admin", 0, "admin123", role="admin")
            bank.add_customer(admin)
            bank.save_to_file(file_name)
            return bank

        with open(file_name, "r") as f:
            data = json.load(f)

        bank = Bank(data["name"])
        for c_data in data["customers"]:
            bank.add_customer(Customer.from_dict(c_data))

        return bank
