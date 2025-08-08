import streamlit as st
import pdfplumber
import re
import pandas as pd

st.title("International Transaction Date and Deposit Amount Extractor")

keywords_input = st.sidebar.text_area(
    "Enter International Payment Keywords (comma-separated):",
    value="SKYDO,WESTERN UNION,WISE,PAYONEER,PAYPAL,TRANSFERWISE,AMAZON,UPWORK,SMARTPAYNI,CMS TRANSACTION,PURPOSE CODE,USD,EUR,GBP,CAD,AUD"
)
keywords = [kw.strip().upper() for kw in keywords_input.split(",") if kw.strip()]

def clean_indian_amount(amount_str):
    cleaned = amount_str.replace(',', '')
    try:
        return float(cleaned)
    except:
        return 0.0

def parse_date(line):
    date_pattern = r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
    match = re.search(date_pattern, line)
    return match.group(0) if match else ""

def find_deposit_amount(line):
    amount_matches = re.findall(r'([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.\d{2})?)', line)
    # For statements like "Amount (INR) <amount> CR <balance>",
    # the deposit is usually the first or second number before 'CR' or 'CREDIT'
    # We'll try to find amount just before 'CR' or 'CREDIT'
    if 'CR' in line.upper() or 'CREDIT' in line.upper():
        parts = re.split(r'CR|CREDIT', line, flags=re.IGNORECASE)
        left = parts[0]
        # Find rightmost number in that left part
        amount_matches = re.findall(r'([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.\d{2})?)', left)
        if amount_matches:
            return amount_matches[-1]
    # Else return the last large number in the line
    if amount_matches:
        return amount_matches[-1]
    return ""

def get_matched_keyword(line, keywords):
    if 'PURPOSE CODE' in line.upper():
        return 'PURPOSE CODE'
    for kw in keywords:
        if kw in line.upper():
            return kw
    return None

uploaded_file = st.file_uploader("Upload your bank statement PDF", type=["pdf"])
if uploaded_file:
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            full_text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"

        lines = full_text.split("\n")
        transactions = []

        for line in lines:
            matched_keyword = get_matched_keyword(line, keywords)
            if matched_keyword:
                # Only extract for credits ("CR", "CREDIT") not debits ("DR") if DR/CR shown
                if 'DR' in line.upper() and not 'CR' in line.upper():
                    continue  # skip debit lines, focus only on credits/receipts

                date = parse_date(line)
                deposit_str = find_deposit_amount(line)
                deposit_amt = clean_indian_amount(deposit_str)
                if date and deposit_amt > 0:
                    transactions.append((date, deposit_str, deposit_amt, matched_keyword, line))

        if not transactions:
            st.info("No international transactions found. Try changing keywords or check your statement format.")
        else:
            df = pd.DataFrame(transactions, columns=["Date", "Deposit Amount", "Amount Value", "Matched Keyword", "Raw Line Preview"])
            df["ParsedDate"] = pd.to_datetime(df["Date"], dayfirst=True, errors='coerce')
            df = df.dropna(subset=["ParsedDate"])
            df["YearMonth"] = df["ParsedDate"].dt.to_period('M')

            monthly_summary = df.groupby("YearMonth").agg(
                Transactions=("Date", "count"),
                Total_Amount=("Amount Value", "sum"),
            ).reset_index()
            monthly_summary["YearMonth"] = monthly_summary["YearMonth"].dt.strftime('%b %Y')

            st.subheader("Raw Matched Transactions")
            st.dataframe(df[["Date", "Deposit Amount", "Amount Value", "Matched Keyword", "Raw Line Preview"]])

            st.subheader("Monthly Summary of International Transactions")
            st.dataframe(monthly_summary.rename(columns={
                "YearMonth": "Month",
                "Transactions": "Number of Transactions",
                "Total_Amount": "Total Deposit Amount"
            }))
    except Exception as e:
        st.error(f"Error processing PDF: {e}")
else:
    st.info("Please upload a PDF to begin.")
