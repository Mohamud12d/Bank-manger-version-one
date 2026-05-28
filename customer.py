import random
from account import Account


class Customer:
    """
    Represents a bank customer.
    - Added: password field for login authentication
    - Added: role field ("admin" or "customer") for access control
    - Added: is_admin() helper method
    - Added: update_password() with validation
    - Added: create_account() so account numbers are generated automatically
    - Added: from_dict() paired with to_dict() for clean serialisation
    """

    def __init__(self, owner, customer_id, password, role="customer"):
        # Validate that inputs are sensible before storing them
        if not owner or not isinstance(owner, str):
            raise ValueError("Owner name must be a non-empty string.")
        if not isinstance(customer_id, int):
            raise ValueError("Customer ID must be an integer.")

        self.owner = owner
        self.customer_id = customer_id
        self.password = password
        # role controls what menu options are shown and what actions are allowed
        self.role = role
        self.accounts = []

    # ------------------------------------------------------------------
    # Role helpers
    # ------------------------------------------------------------------

    def is_admin(self):
        """Return True if this customer has admin privileges."""
        return self.role == "admin"

    # ------------------------------------------------------------------
    # Password management
    # ------------------------------------------------------------------

    def update_password(self, old_password, new_password):
        """
        Change the customer's password.
        - Verifies the old password first (you must prove you know it)
        - Enforces a minimum length on the new password
        """
        if self.password != old_password:
            raise ValueError("Current password is incorrect.")
        if len(new_password) < 6:
            raise ValueError("New password must be at least 6 characters long.")
        self.password = new_password

    # ------------------------------------------------------------------
    # Account management
    # ------------------------------------------------------------------

    def create_account(self, account_type):
        """
        Generate a new account with a random unique account number and add it.
        Keeping account creation here means callers never pick their own numbers.
        """
        # Generate a random 5-digit number; check it's not already in use
        existing_numbers = {acc.account_number for acc in self.accounts}
        while True:
            number = random.randint(10000, 99999) # generate  five of number 
            if number not in existing_numbers:
                break
        new_account = Account(number, account_type)
        self.accounts.append(new_account)
        return new_account

    def add_account(self, account):
        """Add an existing Account object (used when loading from JSON)."""
        self.accounts.append(account)

    def get_account(self, account_number):
        """Find and return an account by number. Raises ValueError if not found."""
        for acc in self.accounts:
            if acc.account_number == account_number:
                return acc
        raise ValueError(f"Account #{account_number} not found.")

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self):
        """Convert to dictionary for JSON saving."""
        return {
            "owner": self.owner,
            "customer_id": self.customer_id,
            "password": self.password,
            "role": self.role,
            "accounts": [acc.to_dict() for acc in self.accounts]
        }

    @classmethod
    def from_dict(cls, data):
        """
        Rebuild a Customer object from a dictionary loaded from JSON.
        Uses .get() with defaults so old JSON files without role/password
        still load without crashing.
        """
        customer = cls(
            data["owner"],
            data["customer_id"],
            data.get("password", "password123"),  # default for old data
            data.get("role", "customer")           # default for old data
        )
        for acc_data in data.get("accounts", []):
            customer.add_account(Account.from_dict(acc_data))
        return customer

    def __str__(self):
        return f"Customer({self.customer_id}, {self.owner}, role={self.role})"
