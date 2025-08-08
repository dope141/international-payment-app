import streamlit as st
import pdfplumber
import re
import pandas as pd

st.title("International Transaction Date and Deposit Amount Extractor")

st.write("""
Upload your bank statement PDF. The app will detect all international payments by scanning for international payment keywords, 
currencies, service providers, and "Purpose Code". It extracts the date, deposit amount, and shows the matched keyword that caused detection.
""")

# Expanded international keywords excluding Indian payment methods
keywords = [
    # Service Providers
    "SKYDO", "WISE", "PAYONEER", "PAYPAL", "TRANSFERWISE", "WESTERN UNION",
    "MONEYGRAM", "XOOM", "WORLDREMIT", "AZIMO", "REMITLY", "RIA", "OFX",
    "XE", "TRANSFERGO", "TORFX",
    # Currencies
    "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "CNY", "SGD", "MXN",
    "NZD", "ZAR", "HKD", "NOK", "SEK", "DKK", "RUB", "TRY", "BRL",
    # International Payment Methods (Expanded)
    "SWIFT", "ACH", "FPS", "GIRO", "INTERAC", "EFT", "AUTOPAY", "P2P", "OBT",
    "BACS", "CHAPS", "SEPA", "IBAN", "SORT CODE", "ABA", "MT103",
    "CROSS BORDER", "WIRE", "REMITTANCE", "TRUSTLY", "CLEARING", "DEUTSCHE", "NOSTRO"
]

# Convert keywords to uppercase for case-insensitive matching
keywords = [kw.upper() for kw in keywords]

uploaded_file = st.file_uploader("Upload your bank statement PDF", type=["pdf"])

def clean_indian_amount(amount_str):
    # Remove all commas (Indian style thousands/lakhs separators), keep dot as decimal
    cleaned = amount_str.replace(',', '')
    try:
        return float(cleaned)
    except:
        return 0.0

def parse_date(d):
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"):
        try:
            return pd.to_datetime(d, format=fmt)
        except:
            pass
    try:
        return pd.to_datetime(d, dayfirst=True, errors='coerce')
    except:
        return pd.NaT

if uploaded_file:
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            full_text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"

        lines = full_text.split("\n")

        # List to hold extracted transaction tuples: (date, deposit_amount_str, matched_keyword)
        transactions = []

        # Regex for dates like 01/01/2025, 1-1-25 etc.
        date_pattern = re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b')

        # Regex to find amounts: numbers with commas and decimals, possibly preceded by currency symbols or words
        amount_pattern = re.compile(r'([\d,]+(?:\.\d{2})?)')

        for line in lines:
            line_upper = line.upper()

            matched_keyword = None
            # Check for "Purpose Code" first (strong international payment flag)
            if "PURPOSE CODE" in line_upper:
                matched_keyword = "PURPOSE CODE"
            else:
                # Check for any keyword match
                for kw in keywords:
                    if kw in line_upper:
                        matched_keyword = kw
                        break

            if matched_keyword:
                # Extract date
                dates = date_pattern.findall(line)
                date = dates[0] if dates else ""

                # Extract deposit amount - focus on amounts appearing typically in deposit column
                # Approach: assume last numeric amount in line is the deposit amount (common in statements)
                amounts = amount_pattern.findall(line)
                deposit_amount_str = amounts[-1] if amounts else ""

                # Only keep if we have date and deposit amount
                if date and deposit_amount_str:
                    transactions.append((date, deposit_amount_str, matched_keyword))

        if not transactions:
            st.info("No international transactions found based on keywords or 'Purpose Code'. Please check your statement or keywords.")
        else:
            # Create DataFrame
            df_trans = pd.DataFrame(transactions, columns=["Date", "Deposit Amount", "Matched Keyword"])

            # Parse and clean data for analysis
            df_trans["ParsedDate"] = df_trans["Date"].apply(parse_date)
            df_trans = df_trans.dropna(subset=["ParsedDate"])

            df_trans["AmountValue"] = df_trans["Deposit Amount"].apply(clean_indian_amount)

            # Group by Year-Month
            df_trans["YearMonth"] = df_trans["ParsedDate"].dt.to_period('M')

            monthly_summary = df_trans.groupby("YearMonth").agg(
                Number_of_Transactions=("Date", "count"),
                Total_Amount=("AmountValue", "sum"),
            ).reset_index()

            monthly_summary["YearMonth"] = monthly_summary["YearMonth"].dt.strftime('%b %Y')

            st.subheader("International Payment Details")
            st.table(df_trans[["Date", "Deposit Amount", "Matched Keyword"]])

            st.subheader("Monthly Summary of International Transactions")
            st.dataframe(monthly_summary.rename(columns={
                "YearMonth": "Month",
                "Number_of_Transactions": "Number of Transactions",
                "Total_Amount": "Total Deposit Amount"
            }))

    except Exception as e:
        st.error(f"Error processing PDF: {e}")

else:
    st.info("Please upload a PDF file to start extracting international transactions.")

