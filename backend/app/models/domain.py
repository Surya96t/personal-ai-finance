from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class Transaction(BaseModel):
    date: str = Field(
        description="The date of the transaction in YYYY-MM-DD format.")
    description: str = Field(
        description="The full, original description of the transaction.")
    amount: float = Field(
        description="The transaction amount. Use a negative number for debits/expenses.")

class TransactionList(BaseModel):
    transactions: List[Transaction]

class EnrichedTransaction(BaseModel):
    cleaned_description: str = Field(
        description="The cleaned, human-readable merchant name.")
    category: Literal[
        "Food & Drink", "Shopping", "Housing", "Transportation", "Utilities",
        "Entertainment", "Income", "Travel", "Health & Wellness", "Groceries",
        "Personal Care", "Gifts & Donations", "Other"
    ] = Field(description="The financial category of the transaction.")
