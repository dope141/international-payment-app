import streamlit as st
import pdfplumber
import re
import pandas as pd

st.title("International Transaction & Deposit Amount Extractor")

st.write("""
Upload your bank statement PDF.  
This app detects **international payments** using keywords for payment methods, service providers, currencies,  
and e‑commerce/freelancing platforms like Amazon, Upwork, Fiverr, etc.  

It shows:
- Date of transaction  
- Deposit (credited) amount **not closing balance** ✅  
- The keyword/method that triggered detection  
- Monthly totals
""")

# --- Sidebar: Editable keyword filter ---
default_keywords = ",".join([
    # Service Providers
    "SKYDO", "WISE", "PAYONEER", "PAYPAL", "TRANSFERWISE", "WESTERN UNION",
    "MONEYGRAM", "XOOM", "WORLDREMIT", "AZIMO", "REMITLY", "RIA", "OFX", "XE", "TRANSFERGO", "TORFX",
    # E‑commerce / Freelancing
    "AMAZON", "UPWORK", "FIVERR", "ETSY", "SHOPIFY", "EBAY", "FREELANCER", "GURU", "TOPTAL",
    "PEOPLEPERHOUR", "99DESIGNS", "ENVATO", "ZAZZLE",
    # Other markers
    "SMARTPAYNI", "CMS TRANSACTION", "PURPOSE CODE",
    # Currencies
    "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "CNY", "SGD", "MXN",
    "NZD", "ZAR", "HKD", "NOK", "SEK", "DKK", "RUB", "TRY", "BRL",
    # International Payment Methods
    "SWIFT", "ACH", "FPS", "CHAPS", "BACS", "SEPA", "GIRO", "INTERAC", "EFT", "IBAN", "SORT CODE", "ABA", "MT103",
    "CROSS BORDER", "WIRE", "REMITTANCE", "TRUSTLY", "CLEARING", "DEUTSCHE", "NOSTRO"
])
keywords_input = st.sidebar.text_area(
    "Enter international payment keywords/websites/methods/currencies (comma-separated):",
    value=default_keywords
)
keywords = [kw.strip().upper() for kw in keywords_input.split(",") if kw.strip()]

# --- Helpers ---
def clean_amount(amount_str):
    """Remove commas from amount and return as float."""
    cleaned = amount_str.replace(',', '')
    try:
        return float(cleaned)
    except:
        return 0.0

def extract_date(line):
    """Find first date pattern in line."""
    match = re.search(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', line)
    return match.group(0) if match else ""

def extract_deposit_amount(line):
    """
    Deposit fix: picks the number before 'CR' or 'CREDIT'
    so we don't pick closing balance.
    """
    cr_match = re.search(r'([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.\d{2})?)\s*(?=CR|CREDIT)', line.upper())
    if cr_match:
        return cr_match.group(1)
    # fallback: second-to-last number in line
    all_nums = re.findall(r'([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.\d{2})?)', line)
    if len(all_nums) >= 2:
        return all_nums[-2]
    elif all_nums:
        return all_nums[-1]
    return ""

def find_matched_keyword(line, keywords):
    """Return first matching keyword or Purpose Code if present."""
    if "PURPOSE CODE" in line.upper():
        return "PURPOSE CODE"
    for kw in keywords:
        if kw in line.upper():
            return kw
    return None

# --- Main ---
uploaded_file = st.file_uploader("Upload your bank statement PDF", type=["pdf"])
if uploaded_file:
    try:
        # Read PDF text
        with pdfplumber.open(uploaded_file) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)

        lines = text.split("\n")
        transactions = []

        for line in lines:
            matched_kw = find_matched_keyword(line, keywords)
            if matched_kw:
                # Skip pure debits
                if "DR" in line.upper() and not "CR" in line.upper():
                    continue
                date = extract_date(line)
                raw_amount = extract_deposit_amount(line)
                deposit_value = clean_amount(raw_amount)
                if date and deposit_value > 0:
                    transactions.append((date, raw_amount, deposit_value, matched_kw, line))

        if not transactions:
            st.warning("No international deposits found. Try adjusting keywords in the sidebar.")
        else:
            # Convert to DataFrame
            df = pd.DataFrame(transactions, columns=[
                "Date", "Deposit Amount", "Amount Value", "Matched Keyword", "Raw Line Preview"
            ])
            df["ParsedDate"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
            df = df.dropna(subset=["ParsedDate"])
            df["YearMonth"] = df["ParsedDate"].dt.to_period('M')

            # Show detailed transactions
            st.subheader("Detected International Deposits")
            st.dataframe(df[["Date", "Deposit Amount", "Amount Value", "Matched Keyword", "Raw Line Preview"]])

            # Monthly summary
            monthly_summary = df.groupby("YearMonth").agg(
                Number_of_Transactions=("Date", "count"),
                Total_Amount=("Amount Value", "sum")
            ).reset_index()
            monthly_summary["Month"] = monthly_summary["YearMonth"].dt.strftime("%b %Y")
            st.subheader("Monthly Summary")
            st.dataframe(monthly_summary[["Month", "Number_of_Transactions", "Total_Amount"]])

    except Exception as e:
        st.error(f"Error processing PDF: {e}")
else:
    st.info("Please upload your PDF to begin.")
