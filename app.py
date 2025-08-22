import streamlit as st
import pandas as pd
import io
import json
import re
from PyPDF2 import PdfReader

# ------------ DEFAULT FILTER LISTS ------------
DEFAULT_CURRENCIES = [
    "USD","EUR","GBP","AUD","CAD","JPY","CHF","SGD","AED","NZD","ZAR","HKD","SAR","MYR","NOK","SEK","DKK","KRW",
    "MXN","BRL","TRY","PLN","CZK","HUF","ILS","THB","IDR","TWD","COP","RUB","CNY","XOF","KES","PHP","ARS","EGP",
    "PKR","BDT","VND","LKR","QAR","UAH","CLP","ISK","BGN","RON","HNL","NGN","HRK","UYU","JOD","OMR"
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
    "P0001","P0002","P0003","P0004","P0005","P0006","P0007","P0008","P0009","P0010","P0011","P0012","P0013","P0014","P0015",
    "P0016","P0017","P0018","P0101","P0102","P0103","P0104","P0105","P0106","P0107","P0108","P0201","P0202","P0203","P0204",
    "P0205","P0206","P0207","P0208","P0209","P0210","P0211","P0212","P0213","P0301","P0302","P0303","P0304","P0305","P0306",
    "P0307","P0308","P0401","P0402","P0403","P0404","P0501","P0502","P0601","P0602","P0603","P0604","P0605","P0606","P0701",
    "P0702","P0703","P0801","P0802","P0803","P0804","P0805","P0806","P0807","P0901","P0902","P1001","P1002","P1003","P1004",
    "P1005","P1006","P1007","P1008","P1009","P1010","P1011","P1012","P1013","P1014","P1015","P1016","P1017","P1018","P1019",
    "P1101","P1102","P1201","P1202","P1301","P1302","P1303","P1304","P1305","P1306","P1401","P1402","P1403","P1404",
    "P1405","P1406","P1407","P1501","P1502","P1503","P1504","P1505","P1506","P1507","P1508","P1509","P1510","P1590"
]
CREDIT_TERMS = [
    "cr","credit","credited","credit received","amount received","payment received",
    "transfer received","deposit","inward remittance","remittance credit","incoming payment","proceeds"
]

# ------------ Sidebar filters -------------
st.sidebar.header("Keyword Filters")
currencies = st.sidebar.text_area(
    "Currencies (comma separated)", value=",".join(DEFAULT_CURRENCIES))
intl_methods = st.sidebar.text_area(
    "International Methods", value=",".join(DEFAULT_INTL_METHODS))
ecom = st.sidebar.text_area(
    "E-Commerce Providers", value=",".join(DEFAULT_ECOM))
forex_providers = st.sidebar.text_area(
    "Forex Providers", value=",".join(DEFAULT_FOREX_PROVIDERS))
purpose_codes = st.sidebar.text_area(
    "Purpose Codes", value=",".join(DEFAULT_PURPOSE_CODES))
extra_include = st.sidebar.text_area("Extra Include Keywords", "")
exclude_keywords = st.sidebar.text_area("Exclude Keywords", "")
include_keywords = (
    [k.strip() for k in currencies.split(",") if k.strip()] +
    [k.strip() for k in intl_methods.split(",") if k.strip()] +
    [k.strip() for k in ecom.split(",") if k.strip()] +
    [k.strip() for k in forex_providers.split(",") if k.strip()] +
    [k.strip() for k in purpose_codes.split(",") if k.strip()] +
    [k.strip() for k in extra_include.split(",") if k.strip()]
)
exclude_keywords_list = [k.strip() for k in exclude_keywords.split(",") if k.strip()]

# ------------ Main UI -------------
st.title("🌐 International Transactions Extractor (Offline Mode)")
uploaded_file = st.file_uploader("Upload your Bank Statement PDF", type=["pdf"])

def extract_transactions(pdf_text, includes, excludes, credit_mode=False):
    """
    Naive parser: looks for lines with dates, amounts, and narration.
    Uses regex and keyword matching.
    """
    records = []
    lines = pdf_text.split("\n")
    date_pattern = r"\b\d{2}[-/]\d{2}[-/]\d{2,4}\b"  # e.g., 01-05-2024 or 01/05/24
    amount_pattern = r"[-+]?\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?"  # numbers like 1,234.56

    for line in lines:
        lline = line.lower()
        if any(exc in lline for exc in excludes):
            continue

        # check if keywords present
        matched_keyword = None
        for kw in includes:
            if kw.lower() in lline:
                matched_keyword = kw
                break

        if not matched_keyword:
            continue

        # check credit mode filter
        if credit_mode and not any(term in lline for term in CREDIT_TERMS):
            continue

        # extract date
        date_match = re.search(date_pattern, line)
        date_val = date_match.group() if date_match else None

        # extract amount
        amt_match = re.search(amount_pattern, line.replace(",", ""))
        amount_val = float(amt_match.group()) if amt_match else None

        if date_val and amount_val:
            records.append({
                "date": date_val,
                "amount": amount_val,
                "narration": line.strip(),
                "keyword_that_triggered": matched_keyword
            })

    return records

if uploaded_file:
    reader = PdfReader(uploaded_file)
    pdf_text = ""
    for page in reader.pages:
        pdf_text += page.extract_text() + "\n"

    # ---- CREDIT MODE ----
    with st.spinner("Processing Credit Transactions..."):
        credit_records = extract_transactions(pdf_text, include_keywords, exclude_keywords_list, credit_mode=True)

    if credit_records:
        st.subheader("💳 Credit Transactions (Priority Results)")
        df_credit = pd.DataFrame(credit_records)
        if not df_credit.empty:
            df_credit["date"] = pd.to_datetime(df_credit["date"], errors="coerce", dayfirst=True)
            df_credit = df_credit.dropna(subset=["date"])
            df_credit = df_credit.rename(columns={
                "amount": "Amount Received",
                "keyword_that_triggered": "Keyword Triggered",
                "narration": "Narration",
                "date": "Date"
            })
            st.dataframe(df_credit, use_container_width=True)
            st.markdown(
                f"**Total Credit Transactions: {len(df_credit)} | Total Amount: ₹{df_credit['Amount Received'].sum():,.2f}**"
            )

    # ---- KEYWORD MODE ----
    with st.spinner("Processing Keyword Matches..."):
        keyword_records = extract_transactions(pdf_text, include_keywords, exclude_keywords_list, credit_mode=False)

    if keyword_records:
        st.subheader("🔍 Keyword-only Transactions (All Matches)")
        df_key = pd.DataFrame(keyword_records)
        if not df_key.empty:
            df_key["date"] = pd.to_datetime(df_key["date"], errors="coerce", dayfirst=True)
            df_key = df_key.dropna(subset=["date"])
            df_key = df_key.rename(columns={
                "amount": "Amount",
                "keyword_that_triggered": "Keyword Triggered",
                "narration": "Narration",
                "date": "Date"
            })
            st.dataframe(df_key, use_container_width=True)
            st.markdown(
                f"**Total Keyword Matches: {len(df_key)} | Total Amount: ₹{df_key['Amount'].sum():,.2f}**"
            )

else:
    st.info("Please upload a PDF to start.")
