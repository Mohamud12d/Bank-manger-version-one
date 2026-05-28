from datetime import date
import random
# The maximum a customer can withdraw in a single day across all transactions
DAILY_WITHDRAWAL_LIMIT = 10000.0


class Account:
    """
    Represents a single bank account.

    Changes from the original:
    - Transactions are now stored as dictionaries instead of plain strings.
      This lets us record the date, type, and amount separately, which is
      needed for the daily withdrawal limit and filtering features.
    - Added: daily withdrawal limit
    - Added: get_deposits(), get_withdrawals(), get_transaction_history()
    - Added: generate_statement() to write a .txt report file
    - Added: from_dict() so loading from JSON lives here, not in bank.py
    """

    def __init__(self, account_number, account_type, balance=0):
        self.account_number = account_number
        self.account_type = account_type
        self.__balance = balance
        # Each transaction is a dict: {"type": "deposit"/"withdraw", "amount": float, "date": "YYYY-MM-DD"}
        self.transactions = []

    # ------------------------------------------------------------------
    # Core banking operations
    # ------------------------------------------------------------------
    @staticmethod
    def generate_txn_id():
        return f"TXN-{random.randint(10000,99999)}"
    
    def get_transactions(self ,txn_id):
        for tr in self.transactions:
            if tr["txn_id"]== txn_id:
                return tr
        raise ValueError("Transaction not found")

    def deposit(self, amount ):
        """Add money to the account."""
        if amount <= 0:
            raise ValueError("Deposit amount must be greater than 0.")
        self.__balance += amount
        self.transactions.append({
            "txn_id":self.generate_txn_id(),
            "type": "deposit",
            "amount": amount,
            "date": str(date.today())
        })

    def withdraw(self, amount):
        """
        Remove money from the account.
        Raises ValueError if the amount is invalid, balance is too low,
        or the daily withdrawal limit would be exceeded.
        """
        if amount <= 0:
            raise ValueError("Withdrawal amount must be greater than 0.")
        if amount > self.__balance:
            raise ValueError("Insufficient balance.")

        # --- Daily limit check ---
        # Sum all withdrawals made today across this account
        today = str(date.today())
        withdrawn_today = sum(
            t["amount"] for t in self.transactions
            if t["type"] == "withdraw" and t["date"] == today
        )
        remaining_limit = DAILY_WITHDRAWAL_LIMIT - withdrawn_today
        if amount > remaining_limit:
            raise ValueError(
                f"Daily withdrawal limit reached. "
                f"You can withdraw at most ${remaining_limit:.2f} more today "
                f"(daily limit: ${DAILY_WITHDRAWAL_LIMIT:.2f})."
            )

        self.__balance -= amount
        self.transactions.append({
            "txn_id":self.generate_txn_id(),
            "type": "withdraw",
            "amount": amount,
            "date": today
        })

    def get_balance(self):
        """Return the current balance. Balance is private so it can only
        be changed through deposit() and withdraw()."""
        return self.__balance

    # ------------------------------------------------------------------
    # Transaction filtering
    # ------------------------------------------------------------------

    def get_deposits(self):
        """Return only deposit transactions."""
        # List comprehension: builds a new list by filtering the existing one
        return [t for t in self.transactions if t["type"] == "deposit"]

    def get_withdrawals(self):
        """Return only withdrawal transactions."""
        return [t for t in self.transactions if t["type"] == "withdraw"]

    def get_transaction_history(self, filter_type="all"):
        """
        Return transactions filtered by type.
        filter_type can be: "all", "deposits", or "withdrawals"
        """
        if filter_type == "deposits":
            return self.get_deposits()
        elif filter_type == "withdrawals":
            return self.get_withdrawals()
        return self.transactions

    # ------------------------------------------------------------------
    # Statement generator
    # ------------------------------------------------------------------

    def generate_statement(self, owner_name):
        """
        Write a formatted account statement to a .txt file.
        This teaches file writing — the 'w' mode creates or overwrites a file.
        """
        filename = f"statement_{self.account_number}.txt"
        with open(filename, "w") as f:
            f.write("=" * 45 + "\n")
            f.write("           ACCOUNT STATEMENT\n")
            f.write("=" * 45 + "\n")
            f.write(f"  Customer : {owner_name}\n")
            f.write(f"  Account  : #{self.account_number}\n")
            f.write(f"  Type     : {self.account_type.capitalize()}\n")
            f.write(f"  Balance  : ${self.__balance:.2f}\n")
            f.write("=" * 45 + "\n")
            f.write("  TRANSACTIONS\n")
            f.write("-" * 45 + "\n")
            if not self.transactions:
                f.write("  No transactions yet.\n")
            else:
                for t in self.transactions:
                    symbol = "+" if t["type"] == "deposit" else "-"
                    label = "Deposit  " if t["type"] == "deposit" else "Withdraw "
                    f.write(f"  {t['date']}  {label}  {symbol}${t['amount']:.2f}\n")
            f.write("=" * 45 + "\n")
        return filename

    # ------------------------------------------------------------------
    # Serialization (saving and loading)
    # ------------------------------------------------------------------

    def to_dict(self):
        """Convert this account to a dictionary so it can be saved as JSON."""
        return {
            "account_number": self.account_number,
            "account_type": self.account_type,
            "balance": self.__balance,
            "transactions": self.transactions
        }

    @classmethod
    def from_dict(cls, data):
        """
        Create an Account object from a dictionary (loaded from JSON).
        Keeping this here means bank.py doesn't need to know Account's internals.

        @classmethod means this method belongs to the class itself, not an instance.
        'cls' is the class (Account), so cls(...) is the same as Account(...).
        """
        acc = cls(
            data["account_number"],
            data["account_type"],
            data["balance"]
        )
        acc.transactions = data.get("transactions", [])
        return acc

    def __str__(self):
        return (
                f"Account(#{self.account_number},"
                f"{self.account_type.capitalize()},"
                f"Balance=${self.__balance:.2f})"
               )
    

