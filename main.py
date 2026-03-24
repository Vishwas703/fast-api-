from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime
import logging

# ── Logging Setup ──────────────────────────────────────────
logging.basicConfig(
    filename="transactions.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ── App Init ───────────────────────────────────────────────
app = FastAPI(
    title="💰 Financial Data Validation Service",
    description="FastAPI service with real-time validation, fraud detection & live dashboard.",
    version="2.0.0"
)

# ── In-Memory Transaction Store ────────────────────────────
transaction_history = []

# ── Valid Options ──────────────────────────────────────────
VALID_CURRENCIES = ["USD", "INR", "EUR", "GBP", "JPY"]
VALID_TRANSACTION_TYPES = ["credit", "debit", "transfer"]
BLACKLISTED_ACCOUNTS = ["ACC000", "FRAUD123", "BLOCK999"]

# ── Data Model ─────────────────────────────────────────────
class Transaction(BaseModel):
    transaction_id: str
    account_number: str
    amount: float
    currency: str
    transaction_type: str
    description: Optional[str] = "No description"

    @validator("amount")
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v

    @validator("currency")
    def currency_must_be_valid(cls, v):
        if v.upper() not in VALID_CURRENCIES:
            raise ValueError(f"Invalid currency. Allowed: {VALID_CURRENCIES}")
        return v.upper()

    @validator("transaction_type")
    def type_must_be_valid(cls, v):
        if v.lower() not in VALID_TRANSACTION_TYPES:
            raise ValueError(f"Invalid type. Allowed: {VALID_TRANSACTION_TYPES}")
        return v.lower()

    @validator("account_number")
    def account_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError("Account number cannot be empty")
        return v

# ── Fraud Detection Logic ──────────────────────────────────
def detect_fraud(transaction: Transaction):
    flags = []

    # Rule 1: Blacklisted account
    if transaction.account_number in BLACKLISTED_ACCOUNTS:
        flags.append("Account is blacklisted")

    # Rule 2: Extremely high amount
    if transaction.amount > 500000:
        flags.append("Suspiciously high transaction amount (> 5,00,000)")

    # Rule 3: Rapid repeated transactions
    recent = [t for t in transaction_history[-10:]
              if t["account_number"] == transaction.account_number]
    if len(recent) >= 3:
        flags.append("Rapid repeated transactions from same account")

    # Rule 4: Round number fraud pattern
    if transaction.amount % 100000 == 0 and transaction.amount >= 100000:
        flags.append("Suspicious round-number transaction pattern")

    return flags

# ── Routes ─────────────────────────────────────────────────

@app.get("/")
def home():
    return {
        "service": "Financial Data Validation API v2.0",
        "status": "Running ✅",
        "features": ["Real-time Validation", "Fraud Detection", "Live Dashboard"]
    }

@app.post("/validate-transaction")
def validate_transaction(transaction: Transaction):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    logger.info(f"Received: {transaction.transaction_id} | "
                f"{transaction.amount} {transaction.currency}")

    # High value check
    if transaction.amount > 1_000_000:
        logger.warning(f"High-value flagged: {transaction.transaction_id}")
        raise HTTPException(status_code=400,
            detail="Amount exceeds limit. Manual review required.")

    # Fraud Detection
    fraud_flags = detect_fraud(transaction)
    is_fraud = len(fraud_flags) > 0
    status = "🚨 Fraud Suspected" if is_fraud else "✅ Approved"

    if is_fraud:
        logger.warning(f"FRAUD DETECTED: {transaction.transaction_id} | Flags: {fraud_flags}")
    else:
        logger.info(f"APPROVED: {transaction.transaction_id}")

    # Save to history
    transaction_history.append({
        "transaction_id": transaction.transaction_id,
        "account_number": transaction.account_number,
        "amount": transaction.amount,
        "currency": transaction.currency,
        "transaction_type": transaction.transaction_type,
        "description": transaction.description,
        "timestamp": timestamp,
        "status": status,
        "fraud_flags": fraud_flags,
        "fraud_detected": is_fraud,
        "compliance": not is_fraud
    })

    return {
        "status": status,
        "transaction_id": transaction.transaction_id,
        "timestamp": timestamp,
        "compliance": not is_fraud,
        "fraud_detected": is_fraud,
        "fraud_flags": fraud_flags,
        "message": "Fraud risk identified!" if is_fraud else "Transaction is valid and compliant."
    }

@app.get("/health")
def health_check():
    return {
        "status": "Healthy ✅",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_transactions": len(transaction_history)
    }

@app.get("/logs")
def get_logs():
    try:
        with open("transactions.log", "r") as f:
            logs = f.readlines()
        return {"total_logs": len(logs), "logs": logs[-10:]}
    except FileNotFoundError:
        return {"message": "No logs yet."}

@app.get("/transactions")
def get_all_transactions():
    return {
        "total": len(transaction_history),
        "transactions": transaction_history
    }

# ── Live Dashboard ─────────────────────────────────────────
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    rows = ""
    for t in reversed(transaction_history):
        is_fraud = t.get("fraud_detected", False)
        color = "#ffebee" if is_fraud else "#e8f5e9"
        badge = "🚨 FRAUD" if is_fraud else "✅ OK"
        flags = ", ".join(t["fraud_flags"]) if t["fraud_flags"] else "None"
        rows += f"""
        <tr style="background:{color}">
            <td>{t['timestamp']}</td>
            <td>{t['transaction_id']}</td>
            <td>{t['account_number']}</td>
            <td><strong>{t['amount']} {t['currency']}</strong></td>
            <td>{t['transaction_type'].upper()}</td>
            <td><span style="font-weight:bold">{badge}</span></td>
            <td style="color:#c62828;font-size:12px">{flags}</td>
        </tr>"""

    total = len(transaction_history)
    fraud_count = sum(1 for t in transaction_history if t.get("fraud_detected"))
    approved = total - fraud_count

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>💰 Financial Validation Dashboard</title>
        <meta http-equiv="refresh" content="5">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: 'Segoe UI', sans-serif; background: #0d1b4b; color: white; padding: 20px; }}
            h1 {{ text-align: center; font-size: 28px; margin-bottom: 5px; color: #4FC3F7; }}
            p.sub {{ text-align: center; color: #8FA3C8; margin-bottom: 20px; font-size: 13px; }}
            .cards {{ display: flex; gap: 20px; justify-content: center; margin-bottom: 25px; flex-wrap: wrap; }}
            .card {{ background: #1E2761; border-radius: 12px; padding: 20px 35px; text-align: center; border: 1px solid #253380; }}
            .card h2 {{ font-size: 36px; color: #FFD740; }}
            .card p {{ font-size: 13px; color: #8FA3C8; margin-top: 5px; }}
            .fraud-card h2 {{ color: #FF5252; }}
            .ok-card h2 {{ color: #00C853; }}
            table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 12px; overflow: hidden; }}
            th {{ background: #1E2761; color: white; padding: 12px 15px; text-align: left; font-size: 13px; }}
            td {{ padding: 10px 15px; font-size: 13px; color: #333; border-bottom: 1px solid #eee; }}
            .empty {{ text-align: center; padding: 40px; color: #8FA3C8; font-size: 16px; background: white; border-radius: 12px; }}
        </style>
    </head>
    <body>
        <h1>💰 Financial Validation Dashboard</h1>
        <p class="sub">Auto-refreshes every 5 seconds • Real-time transaction monitoring</p>
        <div class="cards">
            <div class="card"><h2>{total}</h2><p>Total Transactions</p></div>
            <div class="card ok-card"><h2>{approved}</h2><p>✅ Approved</p></div>
            <div class="card fraud-card"><h2>{fraud_count}</h2><p>🚨 Fraud Detected</p></div>
        </div>
        {'<table><thead><tr><th>Timestamp</th><th>Transaction ID</th><th>Account</th><th>Amount</th><th>Type</th><th>Status</th><th>Fraud Flags</th></tr></thead><tbody>' + rows + '</tbody></table>' if total > 0 else '<div class="empty">No transactions yet. Send some requests to /validate-transaction first!</div>'}
    </body>
    </html>
    """
    return HTMLResponse(content=html)