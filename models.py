# models.py
from mongoengine import (
    Document, StringField, FloatField, DateTimeField,
    ReferenceField, EmailField
)
from datetime import datetime

class User(Document):
    """Optional: Only use if you want user login/authentication."""
    name = StringField(required=True)
    email = EmailField(required=True, unique=True)
    password_hash = StringField(required=True)

    def __str__(self):
        return f"{self.name} ({self.email})"

class Account(Document):
    account_name = StringField(required=True)
    amount = FloatField(required=False, null=True)
    user = ReferenceField(User, required=True)

    def __str__(self):
        return f" {self.name} {self.amount}"
        
class Transaction(Document):
    user = ReferenceField(User, required=True)
    """Stores individual income or expense entries."""
    account = ReferenceField(Account ,required=True)
    transaction_type = StringField(required=True, choices=["income", "expense"])
    amount = FloatField(required=True, min_value=0)
    category = StringField(required=True)  # e.g., Food, Rent, Bills, Shopping
    description = StringField()
    date = DateTimeField(default=datetime.utcnow)

    def __str__(self):
        return f"{self.type.capitalize()} - {self.category} - ₹{self.amount}"





