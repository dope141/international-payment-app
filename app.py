import streamlit as st
import pdfplumber
import re
import pandas as pd

st.title("International Transaction & Deposit Amount Extractor")

st.write("""
Upload your bank statement PDF. The app detects international payments by scanning for service providers, payment methods, currencies, 
and major e-commerce/freelancing sites (like Amazon, Upwork, Fiverr, Shopify, Etsy, etc.).
It shows dates, deposit (credited) amounts, and the matched keyword confirming it's an international payment.
""")

# --- Sidebar Filter for Keywords/Methods/Currencies/Websites ---
default_keywords = ",".join([
    # Service Providers & Methods
    "SKYDO", "WISE", "PAYONEER", "PAYPAL", "TRANSFERWISE", "WESTERN UNION",
    "MONEYGRAM", "XOOM", "WORLDREMIT", "AZIMO", "REMITLY", "RIA", "OFX", "XE", "TRANSFERGO", "TORFX",
    "SMARTPAYNI", "CMS TRANSACTION", "PURPOSE CODE",
    # E-commerce/Freelancing Websites
    "AMAZON", "UPWORK", "FIVERR", "ETSY", "SHOPIFY", "EBAY", "FREELANCER", "GURU", "TOPTAL",
    "PEOPLEPERHOUR", "99DESIGNS", "ENVATO", "ZAZZLE",
    # Currencies
    "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "CNY", "SGD", "MXN",
    "NZD", "ZAR", "HKD", "NOK", "SEK", "DKK", "RUB", "TRY", "BRL",
    # International Payment Methods
    "SWIFT", "ACH", "FPS", "CHAPS", "BACS", "SEPA", "GIRO", "INTERAC", "EFT", "IBAN", "SORT CODE", "ABA", "MT103",
    "CROSS BORDER", "WIRE", "REMITTANCE", "TRUSTLY", "CLEARING", "DEUTSCHE", "NOSTRO"
])
keywords_input = st.sidebar.text_area(
    "Enter international payment keywords/websites/currencies (comma-separated):",
    value=default_keywords
)
keywords = [kw.strip().upper() for kw in keywords_input.split(",") if kw.strip()]

# --- Utility Functions ---
def clean_amount(amount_str):
    # Removes commas, keeps dot; safely converts to float
    cleaned = amount_str.replace(',', '')
    try:
        return float(cleaned)
    except:
        return 0.0

def extract_date(line):
    match = re.search(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', line)
    return match.group(0) if match else ""

def extract_deposit_amount(line):
    # Look for amount before 'CR' or 'CREDIT' (typical deposit credit marker)
    line_upper = line.upper()
    cr_match = re.search(r'([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.\d{2})?)\s*(?=CR|CREDIT)', line_upper)
    if cr_match:
        return cr_match.group(1)
    # Else, pick largest number (most likely the deposit amount)
    all_amounts = re.findall(r'([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.\d{2})?)', line)
    if all_amounts:
        return max(all_amounts, key=lambda s: float(s.replace(',', '')))
    return ""

def find_matched_keyword(line, keywords):
    # Purpose Code is always a match for international payments
    if 'PURPOSE CODE' in line.upper():
        return 'PURPOSE CODE'
    for kw in keywords:
        if kw in line.upper():
            return kw
    return None

# --- Main App Logic ---
uploaded_file = st.file_uploader("Upload your bank statement PDF", type=["pdf"])
if uploaded_file:
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            text = ''
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + '\n'

        lines = text.split('\n')
        transactions = []

        for line in lines:
            matched_kw = find_matched_keyword(line, keywords)
            if matched_kw:
                # Only count credits (CR): skip pure DR lines
                if 'DR' in line.upper() and not 'CR' in line.upper():
                    continue
                date = extract_date(line)
                amount_str = extract_deposit_amount(line)
                amount = clean_amount(amount_str)
                # Valid transaction if date is found, amount is positive
                if date and amount > 0:
                    transactions.append((date, amount_str, amount, matched_kw, line))

        if not transactions:
            st.info("No international deposits found. Try adding keywords/websites/currencies in the sidebar filter or check the PDF format.")
        else:
            df = pd.DataFrame(transactions, columns=[
                "Date", "Deposit Amount", "Amount Value", "Matched Keyword", "Raw Text Preview"
            ])
            df["ParsedDate"] = pd.to_datetime(df["Date"], dayfirst=True, errors='coerce')
            df = df.dropna(subset=["ParsedDate"])
            df["YearMonth"] = df["ParsedDate"].dt.to_period('M')

            st.subheader("Detected International Deposits")
            st.dataframe(df[["Date", "Deposit Amount", "Amount Value", "Matched Keyword", "Raw Text Preview"]])

            monthly_summary = df.groupby("YearMonth").agg(
                Transactions=("Date", "count"),
                Total_Amount=("Amount Value", "sum"),
            ).reset_index()
            monthly_summary["YearMonth"] = monthly_summary["YearMonth"].dt.strftime('%b %Y')

            st.subheader("Monthly Summary")
            st.dataframe(monthly_summary.rename(columns={
                "YearMonth": "Month",
                "Transactions": "Number of Transactions",
                "Total_Amount": "Total Deposit Amount"
            }))
    except Exception as e:
        st.error(f"Error processing PDF: {e}")
else:
    st.info("Please upload your PDF to begin.")
