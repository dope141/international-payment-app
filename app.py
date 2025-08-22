import streamlit as st
import pandas as pd
import re
import io
import pdfplumber

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

CREDIT_TERMS = [
    "cr","credit","credited","credit received","amount received","payment received",
    "transfer received","deposit","inward remittance","remittance credit","incoming payment","proceeds"
]

# ------------ Sidebar filters -------------
st.sidebar.header("Keyword Filters")

currencies = st.sidebar.text_area("Currencies (comma separated)", value=",".join(DEFAULT_CURRENCIES))
intl_methods = st.sidebar.text_area("International Methods", value=",".join(DEFAULT_INTL_METHODS))
ecom = st.sidebar.text_area("E-Commerce Providers", value=",".join(DEFAULT_ECOM))
forex_providers = st.sidebar.text_area("Forex Providers", value=",".join(DEFAULT_FOREX_PROVIDERS))
purpose_codes = st.sidebar.text_area("Purpose Codes", value=",".join(DEFAULT_PURPOSE_CODES))
extra_include = st.sidebar.text_area("Extra Include Keywords", "")
exclude_keywords = st.sidebar.text_area("Exclude Keywords", "")

include_keywords = (
    [k.strip().lower() for k in currencies.split(",") if k.strip()] +
    [k.strip().lower() for k in intl_methods.split(",") if k.strip()] +
    [k.strip().lower() for k in ecom.split(",") if k.strip()] +
    [k.strip().lower() for k in forex_providers.split(",") if k.strip()] +
    [k.strip().lower() for k in purpose_codes.split(",") if k.strip()] +
    [k.strip().lower() for k in extra_include.split(",") if k.strip()]
)
exclude_keywords_list = [k.strip().lower() for k in exclude_keywords.split(",") if k.strip()]

st.title("🌐 International Transactions Extractor (Offline Mode)")

uploaded_file = st.file_uploader("Upload your Bank Statement PDF", type=["pdf"])

# --- Helper function to parse date and amount ---
def parse_line_for_date_amount(line: str):
    date_match = re.search(r"\b\d{2}[-/]\d{2}[-/]\d{2,4}\b", line)
    date_val = None
    if date_match:
        try:
            date_val = pd.to_datetime(date_match.group(), dayfirst=True, errors='coerce')
        except:
            date_val = None
    amount_match = re.search(r"[-+]?\d{1,3}(?:,\d{3})*(?:\.\d+)?", line.replace(",",""))
    amount_val = None
    if amount_match:
        try:
            amount_val = float(amount_match.group())
        except:
            amount_val = None
    return date_val, amount_val

def extract_transactions(pdf_text, includes, excludes):
    records = []
    for line in pdf_text.split("\n"):
        lline = line.lower()
        if any(excl in lline for excl in excludes):
            continue
        matched_kw = None
        for kw in includes:
            if kw in lline:
                matched_kw = kw
                break
        if not matched_kw:
            continue
        date_val, amount_val = parse_line_for_date_amount(line)
        if date_val is None or amount_val is None:
            continue
        records.append({
            "Date": date_val,
            "Amount": amount_val,
            "Keyword Triggered": matched_kw,
            "Narration": line.strip()
        })
    return records

def display_monthly_summary(df):
    if df.empty:
        st.warning("No transactions found.")
        return
    df["Month"] = df["Date"].dt.to_period("M").astype(str)
    grand_total = df["Amount"].sum()
    grand_count = len(df)
    st.markdown(f"### Grand Total: ₹{grand_total:,.2f}")
    st.markdown(f"### Grand Count: {grand_count}")
    st.divider()

    for month, group in df.groupby("Month", sort=True):
        st.subheader(f"📅 {month}")
        display_cols = ["Date", "Amount", "Keyword Triggered", "Narration"]
        st.dataframe(group[display_cols], use_container_width=True)
        month_total = group["Amount"].sum()
        month_count = len(group)
        st.markdown(f"**Total for {month}: ₹{month_total:,.2f}**")
        st.markdown(f"**Count for {month}: {month_count}**")
        st.divider()

if uploaded_file is not None:
    import pdfplumber
    with pdfplumber.open(uploaded_file) as pdf:
        full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    transactions = extract_transactions(full_text, include_keywords, exclude_keywords_list)
    df = pd.DataFrame(transactions)

    if not df.empty:
        df = df.sort_values("Date")
    display_monthly_summary(df)
else:
    st.info("Please upload a PDF to start.")
