import streamlit as st
import pdfplumber
import re
import pandas as pd

st.title("International Transaction & Deposit Amount Extractor")

st.write("""
Upload your bank statement PDF.  
The app will detect international payments (credits only) using your keyword filter in the sidebar.  
It skips all debit transactions completely and correctly picks the credited amount before credit indicators like CR, CREDIT, DEPOSIT, etc.
""")

# --- Sidebar Keyword Filter ---
default_keywords = ",".join([
    # Services / Providers
    "SKYDO", "WISE", "PAYONEER", "PAYPAL", "TRANSFERWISE", "WESTERN UNION",
    "MONEYGRAM", "XOOM", "WORLDREMIT", "AZIMO", "REMITLY", "RIA", "OFX", "XE", "TRANSFERGO", "TORFX",
    # E-commerce / Freelance
    "AMAZON", "UPWORK", "FIVERR", "ETSY", "SHOPIFY", "EBAY", "FREELANCER", "GURU", "TOPTAL",
    "PEOPLEPERHOUR", "99DESIGNS", "ENVATO", "ZAZZLE",
    # Other international markers
    "SMARTPAYNI", "CMS TRANSACTION", "PURPOSE CODE",
    # Currencies
    "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "CNY", "SGD", "MXN",
    "NZD", "ZAR", "HKD", "NOK", "SEK", "DKK", "RUB", "TRY", "BRL",
    # International payment methods
    "SWIFT", "ACH", "FPS", "CHAPS", "BACS", "SEPA", "GIRO", "INTERAC", "EFT", "IBAN", "SORT CODE",
    "ABA", "MT103", "CROSS BORDER", "WIRE", "REMITTANCE", "TRUSTLY", "CLEARING", "DEUTSCHE", "NOSTRO"
])
keywords_input = st.sidebar.text_area(
    "Enter international payment keywords/websites/methods/currencies (comma-separated):",
    value=default_keywords
)
keywords = [kw.strip().upper() for kw in keywords_input.split(",") if kw.strip()]

# Credit indicator words (expanded)
credit_words = [
    "CR", "CREDIT", "CREDITED", "CRED", "DEPOSIT", "DEPOSITED", "DEP AMT", "DEP. AMT",
    "FUNDS RECEIVED", "PAYMENT RECEIVED", "RECEIVED FROM",
    "INWARD REMITTANCE", "FOREIGN INWARD REMITTANCE", "REM. CR", "REMITTANCE CREDIT",
    "NEFT CR", "RTGS CR", "ACH CR", "UPI CR", "CMS CREDIT", "FX CREDIT", "TT CREDIT"
]

# Utility functions
def clean_amount(amount_str):
    cleaned = amount_str.replace(',', '')
    try:
        return float(cleaned)
    except:
        return 0.0

def extract_date(line):
    match = re.search(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', line)
    return match.group(0) if match else ""

def extract_deposit_amount(line):
    line_upper = line.upper()
    for word in credit_words:
        if word in line_upper:
            pattern = r'([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.\d{2})?)\s*(?=' + re.escape(word) + r')'
            match = re.search(pattern, line_upper)
            if match:
                return match.group(1)
    # fallback: try second-to-last number
    nums = re.findall(r'([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.\d{2})?)', line)
    if len(nums) >= 2:
        return nums[-2]
    elif nums:
        return nums[-1]
    return ""

def find_matched_keyword(line, keywords):
    if "PURPOSE CODE" in line.upper():
        return "PURPOSE CODE"
    for kw in keywords:
        if kw in line.upper():
            return kw
    return None

# Domestic methods to skip
indian_methods = ["IMPS","NEFT","RTGS","UPI","ECS","NACH","BBPS","FASTAG","QR PAY","E-WALLET"]

# Main
uploaded_file = st.file_uploader("Upload your bank statement PDF", type=["pdf"])
if uploaded_file:
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)

        lines = text.split("\n")
        transactions = []

        for line in lines:
            line_upper = line.upper()

            # Skip domestic methods
            if any(method in line_upper for method in indian_methods):
                continue
            # Skip pure debit lines
            if "DR" in line_upper and not any(cw in line_upper for cw in credit_words):
                continue

            matched_kw = find_matched_keyword(line, keywords)
            if not matched_kw:
                continue

            date = extract_date(line)
            raw_amt = extract_deposit_amount(line)
            amt_val = clean_amount(raw_amt)

            if date and amt_val > 0:
                transactions.append((date, raw_amt, amt_val, matched_kw, line))

        if not transactions:
            st.warning("No international credits found. Try adjusting the sidebar filter.")
        else:
            df = pd.DataFrame(transactions, columns=["Date", "Deposit Amount", "Amount Value", "Matched Keyword", "Raw Text Preview"])
            df["ParsedDate"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
            df = df.dropna(subset=["ParsedDate"])
            df["YearMonth"] = df["ParsedDate"].dt.to_period('M')

            st.subheader("Detected International Credits")
            st.dataframe(df[["Date", "Deposit Amount", "Amount Value", "Matched Keyword", "Raw Text Preview"]])

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
