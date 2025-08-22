import streamlit as st
import pandas as pd
import pdfplumber
import io
import re
from collections import defaultdict

# ------------------ DEFAULT FILTER LISTS ------------------
DEFAULT_CURRENCIES = [
    "USD","EUR","GBP","AUD","CAD","JPY","CHF","SGD","AED","NZD","ZAR","HKD","SAR","MYR","NOK",
    "SEK","DKK","KRW","MXN","BRL","TRY","PLN","CZK","HUF","ILS","THB","IDR","TWD","COP","RUB",
    "CNY","XOF","KES","PHP","ARS","EGP","PKR","BDT","VND","LKR","QAR","UAH","CLP","ISK","BGN",
    "RON","HNL","NGN","HRK","UYU","JOD","OMR"
]

DEFAULT_INTL_METHODS = [
    "swift","iban","ach","fedwire","sepa","chaps","rtgs","neft","imps","wire transfer","bacs","eft","telex transfer",
    "faster payments","direct deposit","remitly","moneygram","western union","xoom","paypal","stripe","skrill",
    "payoneer","wise","revolut","currencycloud","instarem","paysera","alipay","wechat pay","google pay","apple pay",
    "amazon pay","jcb","maestro","visa","mastercard","american express","discover","unionpay","zelle","interac",
    "venmo","square cash","payson","klarna","afterpay","trustly","billpay","poli","sofort","giropay","multibanco",
    "euteller","eps","ideal","bank giro"
]

DEFAULT_ECOM = [
    "amazon","ebay","flipkart","aliexpress","fiverr","upwork","freelancer","shopify","etsy","stripe","instamojo",
    "razorpay","paytm","wise","skrill","bigcommerce","walmart","zomato","swiggy","uber","ola","zoom","netflix",
    "spotify","linkedin","airtasker","taskrabbit","payoneer","paypal"
]

DEFAULT_FOREX_PROVIDERS = [
    "skydo","wise","payoneer","briskpay","worldremit","remitly","xoom","transferwise","dbs remittance",
    "westernunion","moneygram","azimo","revolut","instarem","currencycloud","skrill","neteller","paysera",
    "paypal","paypalx"
]

DEFAULT_PURPOSE_CODES = [
    "P0001","P0002","P0003","P0004","P0005","P0006","P0007","P0008","P0009","P0010","P0011","P0012","P0013","P0014",
    "P0015","P0016","P0017","P0018","P0101","P0102","P0103","P0104","P0105","P0106","P0107","P0108","P0201","P0202",
    "P0203","P0204","P0205","P0206","P0207","P0208","P0209","P0210","P0211","P0212","P0213","P0301","P0302","P0303",
    "P0304","P0305","P0306","P0307","P0308","P0401","P0402","P0403","P0404","P0501","P0502","P0601","P0602","P0603",
    "P0604","P0605","P0606","P0701","P0702","P0703","P0801","P0802","P0803","P0804","P0805","P0806","P0807","P0901",
    "P0902","P1001","P1002","P1003","P1004","P1005","P1006","P1007","P1008","P1009","P1010","P1011","P1012","P1013",
    "P1014","P1015","P1016","P1017","P1018","P1019","P1101","P1102","P1201","P1202","P1301","P1302","P1303","P1304",
    "P1305","P1306","P1401","P1402","P1403","P1404","P1405","P1406","P1407","P1501","P1502","P1503","P1504","P1505",
    "P1506","P1507","P1508","P1509","P1510","P1590"
]

# ------------------ STREAMLIT UI ------------------
st.title("📊 International Payment Statement Analyzer")

uploaded_file = st.file_uploader("Upload your bank statement (PDF)", type=["pdf"])

st.sidebar.header("Keyword Filters")
currencies = st.sidebar.text_area("Currencies (comma separated)", value=",".join(DEFAULT_CURRENCIES))
intl_methods = st.sidebar.text_area("International Methods", value=",".join(DEFAULT_INTL_METHODS))
ecom = st.sidebar.text_area("E-Commerce Providers", value=",".join(DEFAULT_ECOM))
forex_providers = st.sidebar.text_area("Forex Providers", value=",".join(DEFAULT_FOREX_PROVIDERS))
purpose_codes = st.sidebar.text_area("Purpose Codes", value=",".join(DEFAULT_PURPOSE_CODES))
extra_include = st.sidebar.text_area("Extra Include Keywords", "")
exclude_keywords = st.sidebar.text_area("Exclude Keywords", "")

# ------------------ PROCESS PDF ------------------
def extract_text_from_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

def process_transactions(text, include_keywords, exclude_keywords):
    transactions = []
    monthly_data = defaultdict(list)

    lines = text.splitlines()
    for line in lines:
        if any(word in line.lower() for word in exclude_keywords):
            continue
        if any(word in line.lower() for word in include_keywords):
            transactions.append(line)
            # Extract month if present
            month_match = re.search(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\b", line, re.IGNORECASE)
            if month_match:
                month = month_match.group(0).capitalize()
                monthly_data[month].append(line)

    return transactions, monthly_data

# ------------------ MAIN LOGIC ------------------
if uploaded_file is not None:
    text = extract_text_from_pdf(uploaded_file)

    include_keywords = [kw.strip().lower() for kw in (currencies + "," + intl_methods + "," + ecom + "," + forex_providers + "," + purpose_codes + "," + extra_include).split(",") if kw.strip()]
    exclude_keywords = [kw.strip().lower() for kw in exclude_keywords.split(",") if kw.strip()]

    transactions, monthly_data = process_transactions(text, include_keywords, exclude_keywords)

    if not transactions:
        st.warning("No matching transactions found with the given filters.")
    else:
        st.subheader("🔑 Keyword Triggered Transactions")
        for t in transactions:
            st.write(t)

        grand_total = 0
        grand_count = 0

        st.subheader("📅 Monthly Breakdown")
        for month, txns in monthly_data.items():
            st.markdown(f"### {month}")
            df = pd.DataFrame(txns, columns=["Transaction Details"])
            st.dataframe(df)

            # Dummy calculation for totals (replace with actual numeric extraction)
            total_amount = len(txns) * 100  # Example placeholder
            txn_count = len(txns)

            st.write(f"**Total for {month}:** {total_amount}")
            st.write(f"**Number of Transactions:** {txn_count}")
            st.markdown("---")

            grand_total += total_amount
            grand_count += txn_count

        # Grand total
        st.subheader("📊 Grand Total Summary")
        st.write(f"**Overall Total:** {grand_total}")
        st.write(f"**Overall Transaction Count:** {grand_count}")
