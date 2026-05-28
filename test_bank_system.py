"""
test_bank_system.py — Pytest suite for the Bank System

Coverage:
  - Account: deposit, withdraw, balance, daily limit, transaction filters,
             statement generation, serialisation
  - Customer: creation, validation, password management, account management,
              role helpers, serialisation
  - Bank: customer management, transfer, admin views, persistence (save/load)

Run with:
    pytest test_bank_system.py -v
"""

import json
import os
import pytest
from unittest.mock import patch
from datetime import date

# ---------------------------------------------------------------------------
# Make sure the source files are importable when running from the output dir.
# Adjust the path below if your project layout differs.
# ---------------------------------------------------------------------------
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from account import Account, DAILY_WITHDRAWAL_LIMIT
from customer import Customer
from bank import Bank


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def basic_account():
    """A savings account pre-loaded with $1 000."""
    acc = Account(11111, "saving", balance=1000.0)
    return acc


@pytest.fixture
def empty_account():
    """A current account with zero balance."""
    return Account(22222, "current", balance=0.0)


@pytest.fixture
def customer_with_account():
    """A customer who already owns one savings account with $500."""
    c = Customer("Alice", 1, "pass123")
    acc = Account(55555, "saving", balance=500.0)
    c.add_account(acc)
    return c, acc


@pytest.fixture
def two_customer_bank():
    """
    A bank with two customers:
      - Alice  (ID 1): one savings account #55555 with $1 000
      - Bob    (ID 2): one current account #66666 with $200
    """
    bank = Bank("TestBank")

    alice = Customer("Alice", 1, "alicepw")
    alice.add_account(Account(55555, "saving", balance=1000.0))
    bank.add_customer(alice)

    bob = Customer("Bob", 2, "bobpw")
    bob.add_account(Account(66666, "current", balance=200.0))
    bank.add_customer(bob)

    return bank, alice, bob


# ===========================================================================
# Account tests
# ===========================================================================

class TestAccountDeposit:
    def test_deposit_increases_balance(self, basic_account):
        basic_account.deposit(500)
        assert basic_account.get_balance() == 1500.0

    def test_deposit_records_transaction(self, basic_account):
        basic_account.deposit(200)
        deposits = basic_account.get_deposits()
        assert len(deposits) == 1
        assert deposits[0]["type"] == "deposit"
        assert deposits[0]["amount"] == 200

    def test_deposit_zero_raises(self, basic_account):
        with pytest.raises(ValueError, match="greater than 0"):
            basic_account.deposit(0)

    def test_deposit_negative_raises(self, basic_account):
        with pytest.raises(ValueError, match="greater than 0"):
            basic_account.deposit(-50)

    def test_deposit_records_todays_date(self, basic_account):
        basic_account.deposit(100)
        txn = basic_account.get_deposits()[0]
        assert txn["date"] == str(date.today())

    def test_deposit_transaction_has_txn_id(self, basic_account):
        basic_account.deposit(100)
        txn = basic_account.get_deposits()[0]
        assert txn["txn_id"].startswith("TXN-")


class TestAccountWithdraw:
    def test_withdraw_decreases_balance(self, basic_account):
        basic_account.withdraw(300)
        assert basic_account.get_balance() == 700.0

    def test_withdraw_records_transaction(self, basic_account):
        basic_account.withdraw(100)
        withdrawals = basic_account.get_withdrawals()
        assert len(withdrawals) == 1
        assert withdrawals[0]["type"] == "withdraw"
        assert withdrawals[0]["amount"] == 100

    def test_withdraw_zero_raises(self, basic_account):
        with pytest.raises(ValueError, match="greater than 0"):
            basic_account.withdraw(0)

    def test_withdraw_negative_raises(self, basic_account):
        with pytest.raises(ValueError, match="greater than 0"):
            basic_account.withdraw(-10)

    def test_withdraw_insufficient_funds_raises(self, basic_account):
        with pytest.raises(ValueError, match="Insufficient balance"):
            basic_account.withdraw(9999)

    def test_withdraw_exact_balance_succeeds(self, basic_account):
        basic_account.withdraw(1000.0)
        assert basic_account.get_balance() == 0.0

    def test_withdraw_from_empty_account_raises(self, empty_account):
        with pytest.raises(ValueError, match="Insufficient balance"):
            empty_account.withdraw(1)


class TestDailyWithdrawalLimit:
    def test_single_withdrawal_within_limit(self, basic_account):
        """A withdrawal below the daily limit should succeed."""
        basic_account.deposit(DAILY_WITHDRAWAL_LIMIT)   # ensure enough funds
        basic_account.withdraw(DAILY_WITHDRAWAL_LIMIT - 1)
        assert basic_account.get_balance() >= 0

    def test_cumulative_withdrawals_hit_limit(self):
        """Two withdrawals that together exceed the daily limit should fail on the second."""
        acc = Account(99999, "saving", balance=DAILY_WITHDRAWAL_LIMIT + 5000)
        acc.withdraw(DAILY_WITHDRAWAL_LIMIT - 100)
        with pytest.raises(ValueError, match="Daily withdrawal limit"):
            acc.withdraw(200)   # would exceed the daily total

    def test_full_daily_limit_in_one_go(self):
        """Withdrawing exactly the daily limit in one transaction should work."""
        acc = Account(77777, "saving", balance=DAILY_WITHDRAWAL_LIMIT)
        acc.withdraw(DAILY_WITHDRAWAL_LIMIT)
        assert acc.get_balance() == 0.0

    def test_withdrawals_on_different_days_are_independent(self):
        """Simulate yesterday's withdrawal not counting toward today's limit."""
        acc = Account(88888, "saving", balance=DAILY_WITHDRAWAL_LIMIT * 2 + 100)

        # Inject a withdrawal dated yesterday
        yesterday = "2000-01-01"
        acc.transactions.append({
            "txn_id": "TXN-00000",
            "type": "withdraw",
            "amount": DAILY_WITHDRAWAL_LIMIT,
            "date": yesterday,
        })
        # Force internal balance down to reflect that historical withdrawal
        acc._Account__balance -= DAILY_WITHDRAWAL_LIMIT

        # Today's withdrawal should not be blocked by yesterday's
        acc.withdraw(100)
        assert acc.get_balance() == DAILY_WITHDRAWAL_LIMIT


class TestTransactionFilters:
    @pytest.fixture(autouse=True)
    def _setup(self, basic_account):
        self.acc = basic_account
        self.acc.deposit(100)
        self.acc.deposit(200)
        self.acc.withdraw(50)
        self.acc.withdraw(75)

    def test_get_deposits_returns_only_deposits(self):
        deposits = self.acc.get_deposits()
        assert all(t["type"] == "deposit" for t in deposits)
        assert len(deposits) == 2

    def test_get_withdrawals_returns_only_withdrawals(self):
        withdrawals = self.acc.get_withdrawals()
        assert all(t["type"] == "withdraw" for t in withdrawals)
        assert len(withdrawals) == 2

    def test_get_transaction_history_all(self):
        assert len(self.acc.get_transaction_history("all")) == 4

    def test_get_transaction_history_deposits(self):
        result = self.acc.get_transaction_history("deposits")
        assert len(result) == 2

    def test_get_transaction_history_withdrawals(self):
        result = self.acc.get_transaction_history("withdrawals")
        assert len(result) == 2

    def test_get_transaction_history_default_is_all(self):
        assert len(self.acc.get_transaction_history()) == 4


class TestTransactionLookup:
    def test_get_transactions_returns_correct_txn(self, basic_account):
        basic_account.deposit(999)
        txn = basic_account.get_deposits()[0]
        result = basic_account.get_transactions(txn["txn_id"])
        assert result["amount"] == 999

    def test_get_transactions_raises_for_missing_id(self, basic_account):
        with pytest.raises(ValueError, match="Transaction not found"):
            basic_account.get_transactions("TXN-00000")


class TestAccountStatement:
    def test_statement_creates_file(self, basic_account, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        filename = basic_account.generate_statement("Test Owner")
        assert os.path.exists(filename)

    def test_statement_contains_owner_name(self, basic_account, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        filename = basic_account.generate_statement("Test Owner")
        content = open(filename).read()
        assert "Test Owner" in content

    def test_statement_contains_balance(self, basic_account, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        filename = basic_account.generate_statement("Test Owner")
        content = open(filename).read()
        assert "1000.00" in content

    def test_statement_lists_transactions(self, basic_account, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        basic_account.deposit(250)
        filename = basic_account.generate_statement("Test Owner")
        content = open(filename).read()
        assert "250.00" in content

    def test_statement_no_transactions_message(self, empty_account, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        filename = empty_account.generate_statement("Empty User")
        content = open(filename).read()
        assert "No transactions yet" in content


class TestAccountSerialisation:
    def test_to_dict_round_trip(self, basic_account):
        basic_account.deposit(100)
        basic_account.withdraw(50)
        d = basic_account.to_dict()
        restored = Account.from_dict(d)
        assert restored.account_number == basic_account.account_number
        assert restored.account_type == basic_account.account_type
        assert restored.get_balance() == basic_account.get_balance()
        assert len(restored.transactions) == 2

    def test_from_dict_missing_transactions_defaults_to_empty(self):
        d = {"account_number": 12345, "account_type": "saving", "balance": 0}
        acc = Account.from_dict(d)
        assert acc.transactions == []

    def test_str_representation(self, basic_account):
        s = str(basic_account)
        assert "11111" in s
        assert "Saving" in s
        assert "1000.00" in s


# ===========================================================================
# Customer tests
# ===========================================================================

class TestCustomerCreation:
    def test_valid_customer_is_created(self):
        c = Customer("Bob", 42, "secret")
        assert c.owner == "Bob"
        assert c.customer_id == 42
        assert c.role == "customer"

    def test_default_role_is_customer(self):
        c = Customer("Eve", 7, "pw1234")
        assert not c.is_admin()

    def test_admin_role_is_recognised(self):
        c = Customer("Admin", 0, "adminpw", role="admin")
        assert c.is_admin()

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="non-empty string"):
            Customer("", 1, "pw1234")

    def test_non_string_name_raises(self):
        with pytest.raises(ValueError):
            Customer(None, 1, "pw1234")

    def test_non_integer_id_raises(self):
        with pytest.raises(ValueError, match="integer"):
            Customer("Bob", "abc", "pw1234")

    def test_str_representation(self):
        c = Customer("Carol", 5, "pw1234", role="admin")
        s = str(c)
        assert "Carol" in s
        assert "admin" in s


class TestPasswordManagement:
    def test_correct_password_allows_update(self):
        c = Customer("Dave", 3, "oldpass")
        c.update_password("oldpass", "newpass")
        assert c.password == "newpass"

    def test_wrong_old_password_raises(self):
        c = Customer("Dave", 3, "oldpass")
        with pytest.raises(ValueError, match="incorrect"):
            c.update_password("wrongpass", "newpass")

    def test_short_new_password_raises(self):
        c = Customer("Dave", 3, "oldpass")
        with pytest.raises(ValueError, match="6 characters"):
            c.update_password("oldpass", "abc")

    def test_minimum_length_password_is_accepted(self):
        c = Customer("Dave", 3, "oldpass")
        c.update_password("oldpass", "abc123")
        assert c.password == "abc123"


class TestCustomerAccounts:
    def test_create_account_adds_to_list(self):
        c = Customer("Eve", 4, "pw1234")
        acc = c.create_account("saving")
        assert len(c.accounts) == 1
        assert acc.account_type == "saving"

    def test_create_account_number_is_unique(self):
        c = Customer("Eve", 4, "pw1234")
        numbers = {c.create_account("saving").account_number for _ in range(10)}
        assert len(numbers) == 10

    def test_get_account_returns_correct_account(self, customer_with_account):
        c, acc = customer_with_account
        found = c.get_account(acc.account_number)
        assert found is acc

    def test_get_account_raises_for_unknown_number(self, customer_with_account):
        c, _ = customer_with_account
        with pytest.raises(ValueError, match="not found"):
            c.get_account(99999)

    def test_add_account_appends_existing_account(self):
        c = Customer("Frank", 6, "pw1234")
        acc = Account(10001, "current", 0)
        c.add_account(acc)
        assert acc in c.accounts


class TestCustomerSerialisation:
    def test_round_trip_preserves_data(self):
        c = Customer("Gina", 9, "mypassword", role="admin")
        c.create_account("saving")
        d = c.to_dict()
        restored = Customer.from_dict(d)
        assert restored.owner == "Gina"
        assert restored.customer_id == 9
        assert restored.role == "admin"
        assert len(restored.accounts) == 1

    def test_from_dict_uses_defaults_for_missing_fields(self):
        d = {"owner": "Harry", "customer_id": 10, "accounts": []}
        c = Customer.from_dict(d)
        assert c.role == "customer"
        assert c.password == "password123"


# ===========================================================================
# Bank tests
# ===========================================================================

class TestBankCustomerManagement:
    def test_add_customer_increases_count(self):
        bank = Bank("TestBank")
        bank.add_customer(Customer("Iris", 1, "pw1234"))
        assert len(bank.customers) == 1

    def test_get_customer_returns_correct_customer(self, two_customer_bank):
        bank, alice, _ = two_customer_bank
        result = bank.get_customer(alice.customer_id)
        assert result is alice

    def test_get_customer_raises_for_unknown_id(self, two_customer_bank):
        bank, _, _ = two_customer_bank
        with pytest.raises(ValueError, match="not found"):
            bank.get_customer(9999)

    def test_remove_customer_deletes_them(self, two_customer_bank):
        bank, _, bob = two_customer_bank
        bank.remove_customer(bob.customer_id)
        assert len(bank.customers) == 1

    def test_remove_customer_returns_name(self, two_customer_bank):
        bank, _, bob = two_customer_bank
        name = bank.remove_customer(bob.customer_id)
        assert name == "Bob"

    def test_remove_nonexistent_customer_raises(self, two_customer_bank):
        bank, _, _ = two_customer_bank
        with pytest.raises(ValueError):
            bank.remove_customer(9999)

    def test_customer_id_exists_true(self, two_customer_bank):
        bank, alice, _ = two_customer_bank
        assert bank.customer_id_exists(alice.customer_id)

    def test_customer_id_exists_false(self, two_customer_bank):
        bank, _, _ = two_customer_bank
        assert not bank.customer_id_exists(9999)


class TestBankTransfer:
    def test_transfer_moves_funds_correctly(self, two_customer_bank):
        bank, alice, bob = two_customer_bank
        alice_acc = alice.accounts[0]
        bob_acc = bob.accounts[0]

        bank.transfer(alice.customer_id, alice_acc.account_number,
                      bob.customer_id, bob_acc.account_number, 300)

        assert alice_acc.get_balance() == 700.0
        assert bob_acc.get_balance() == 500.0

    def test_transfer_zero_raises(self, two_customer_bank):
        bank, alice, bob = two_customer_bank
        with pytest.raises(ValueError, match="greater than 0"):
            bank.transfer(alice.customer_id, alice.accounts[0].account_number,
                          bob.customer_id, bob.accounts[0].account_number, 0)

    def test_transfer_insufficient_funds_raises(self, two_customer_bank):
        bank, alice, bob = two_customer_bank
        with pytest.raises(ValueError, match="Insufficient balance"):
            bank.transfer(alice.customer_id, alice.accounts[0].account_number,
                          bob.customer_id, bob.accounts[0].account_number, 99999)

    def test_transfer_insufficient_funds_does_not_change_balances(self, two_customer_bank):
        """If the withdraw fails the deposit must never run (atomicity)."""
        bank, alice, bob = two_customer_bank
        alice_before = alice.accounts[0].get_balance()
        bob_before = bob.accounts[0].get_balance()
        try:
            bank.transfer(alice.customer_id, alice.accounts[0].account_number,
                          bob.customer_id, bob.accounts[0].account_number, 99999)
        except ValueError:
            pass
        assert alice.accounts[0].get_balance() == alice_before
        assert bob.accounts[0].get_balance() == bob_before

    def test_transfer_to_unknown_customer_raises(self, two_customer_bank):
        bank, alice, _ = two_customer_bank
        with pytest.raises(ValueError):
            bank.transfer(alice.customer_id, alice.accounts[0].account_number,
                          9999, 12345, 100)


class TestBankAdminViews:
    def test_get_all_transactions_returns_flat_list(self, two_customer_bank):
        bank, alice, bob = two_customer_bank
        alice.accounts[0].deposit(100)
        alice.accounts[0].withdraw(50)
        bob.accounts[0].deposit(200)

        txns = bank.get_all_transactions()
        assert len(txns) == 3

    def test_get_all_transactions_includes_customer_name(self, two_customer_bank):
        bank, alice, _ = two_customer_bank
        alice.accounts[0].deposit(50)
        txns = bank.get_all_transactions()
        names = [t["customer"] for t in txns]
        assert "Alice" in names

    def test_get_all_transactions_empty_bank(self):
        bank = Bank("EmptyBank")
        assert bank.get_all_transactions() == []


class TestBankPersistence:
    def test_save_and_load_preserves_customers(self, two_customer_bank, tmp_path):
        bank, alice, bob = two_customer_bank
        file_path = str(tmp_path / "bank.json")
        bank.save_to_file(file_path)

        loaded = Bank.load_from_file(file_path)
        assert len(loaded.customers) == 2
        owner_names = {c.owner for c in loaded.customers}
        assert owner_names == {"Alice", "Bob"}

    def test_save_and_load_preserves_balances(self, two_customer_bank, tmp_path):
        bank, alice, bob = two_customer_bank
        alice.accounts[0].deposit(123.45)
        file_path = str(tmp_path / "bank.json")
        bank.save_to_file(file_path)

        loaded = Bank.load_from_file(file_path)
        loaded_alice = loaded.get_customer(alice.customer_id)
        assert loaded_alice.accounts[0].get_balance() == pytest.approx(1123.45)

    def test_save_and_load_preserves_transactions(self, two_customer_bank, tmp_path):
        bank, alice, _ = two_customer_bank
        alice.accounts[0].deposit(50)
        alice.accounts[0].withdraw(20)
        file_path = str(tmp_path / "bank.json")
        bank.save_to_file(file_path)

        loaded = Bank.load_from_file(file_path)
        loaded_alice = loaded.get_customer(alice.customer_id)
        assert len(loaded_alice.accounts[0].transactions) == 2

    def test_load_missing_file_creates_default_admin(self, tmp_path):
        file_path = str(tmp_path / "nonexistent.json")
        bank = Bank.load_from_file(file_path)
        assert len(bank.customers) == 1
        assert bank.customers[0].is_admin()

    def test_save_creates_valid_json(self, two_customer_bank, tmp_path):
        bank, _, _ = two_customer_bank
        file_path = str(tmp_path / "bank.json")
        bank.save_to_file(file_path)
        with open(file_path) as f:
            data = json.load(f)
        assert data["name"] == "TestBank"
        assert len(data["customers"]) == 2
