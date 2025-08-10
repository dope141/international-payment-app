import streamlit as st
import pdfplumber
import pandas as pd
import re
from datetime import datetime

# ===== Default lists =====
DEFAULT_CURRENCIES = [
    "USD","EUR","GBP","AUD","CAD","JPY","CHF","SGD","AED","NZD",
    "ZAR","HKD","SAR","MYR","NOK","SEK","DKK","KRW","MXN","BRL",
    "TRY","PLN","CZK","HUF","ILS","THB","IDR","TWD","COP","RUB",
    "CNY","XOF","KES","PHP","ARS","EGP","PKR","BDT","VND","LKR",
    "QAR","UAH","CLP","ISK","BGN","RON","HNL","NGN","HRK","UYU",
    "JOD","OMR"
]
DEFAULT_INTL_METHODS = [
    "swift","iban","ach","fedwire","sepa","chaps","rtgs","neft","imps",
    "wire transfer","bacs","eft","telex transfer","faster payments",
    "direct deposit","remitly","moneygram","western union","xoom",
    "paypal","stripe","skrill","payoneer","wise","revolut","currencycloud",
    "instarem","paysera","alipay","wechat pay","google pay","apple pay",
    "amazon pay","jcb","maestro","visa","mastercard","american express",
    "discover","unionpay","zelle","interac","venmo","square cash","payson",
    "klarna","afterpay","trustly","billpay","poli","sofort","giropay",
    "multibanco","euteller","eps","ideal","bank giro"
]
DEFAULT_ECOM = [
    "amazon","ebay","flipkart","aliexpress","fiverr","upwork","freelancer",
    "shopify","etsy","stripe","instamojo","razorpay","paytm","wise","skrill",
    "bigcommerce","walmart","zomato","swiggy","uber","ola","zoom","netflix",
    "spotify","linkedin","airtasker","taskrabbit","payoneer","paypal"
]
DEFAULT_FOREX_PROVIDERS = [
    "skydo","wise","payoneer","briskpay","worldremit","remitly","xoom",
    "transferwise","dbs remittance","westernunion","moneygram","azimo",
    "revolut","instarem","currencycloud","skrill","neteller","paysera",
    "paypal","paypalx"
]
DEFAULT_PURPOSE_CODES = [
    # Full list here…
    "P0001","P0002","P0003","P0004","P0005", "S1504"
]
CREDIT_TERMS = [
    "cr", "credit", "credited", "credit received", "amount received",
    "payment received","transfer received","deposit","inward remittance",
    "remittance credit","incoming payment","proceeds"
]

# ===== Extraction =====
def extract_keyword_credit_transactions(file, include_keywords, credit_terms):
    transactions = []
    include_keywords_lower = [kw.lower() for kw in include_keywords]
    credit_terms_lower = [t.lower() for t in credit_terms]

    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            for line in text.split("\n"):
                date_match = re.match(r'^(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', line)
                if not date_match:  # skip non-date lines
                    continue
                date_str = date_match.group(1)
                rest = line[len(date_str):].strip()

                # Must have BOTH credit term + keyword
                if not any(term in line.lower() for term in credit_terms_lower):
                    continue
                if not any(kw in rest.lower() for kw in include_keywords_lower):
                    continue

                # Try amount
                amount_f = 0.0
                for part in rest.split():
                    if re.match(r'^\d{1,3}(?:,\d{3})*(?:\.\d+)?$', part):
                        try:
                            amount_f = float(part.replace(",", ""))
                            break
                        except:
                            pass
                # Parse date
                date_obj = None
                for fmt in ("%d/%m/%Y","%d-%m-%Y","%d/%m/%y","%d-%m-%y"):
                    try:
                        date_obj = datetime.strptime(date_str, fmt)
                        break
                    except:
                        pass
                if date_obj:
                    transactions.append({
                        "Date": date_obj,
                        "Amount": amount_f,
                        "Narration": rest,
                        "Type": "credit"
                    })
    return pd.DataFrame(transactions)

# ===== Streamlit UI =====
st.set_page_config(page_title="International Fund Receipt Detector", layout="wide")
st.title("🌐 International Fund Receipt Detector — Clean Sidebar Filters")

with st.sidebar:
    st.header("Filters (comma-separated)")

    currencies_input = st.text_area("Currencies", ", ".join(DEFAULT_CURRENCIES))
    methods_input = st.text_area("Int'l Payment Methods", ", ".join(DEFAULT_INTL_METHODS))
    ecom_input = st.text_area("E-commerce Platforms", ", ".join(DEFAULT_ECOM))
    forex_input = st.text_area("Forex Providers", ", ".join(DEFAULT_FOREX_PROVIDERS))
    purposes_input = st.text_area("Purpose Codes (RBI)", ", ".join(DEFAULT_PURPOSE_CODES))
    credit_terms_input = st.text_area("Credit Terms", ", ".join(CREDIT_TERMS))

    extra_include = st.text_area("Add MORE Include Keywords", "")
    extra_exclude = st.text_area("Add Exclude Keywords", "")

include_keywords = (
    [kw.strip() for kw in currencies_input.split(",") if kw.strip()]
    + [kw.strip() for kw in methods_input.split(",") if kw.strip()]
    + [kw.strip() for kw in ecom_input.split(",") if kw.strip()]
    + [kw.strip() for kw in forex_input.split(",") if kw.strip()]
    + [kw.strip() for kw in purposes_input.split(",") if kw.strip()]
    + [kw.strip() for kw in extra_include.split(",") if kw.strip()]
)
exclude_keywords = [kw.strip().lower() for kw in extra_exclude.split(",") if kw.strip()]
credit_terms = [ct.strip() for ct in credit_terms_input.split(",") if ct.strip()]

# ===== File Upload & Process =====
uploaded_file = st.file_uploader("Upload bank statement PDF", type=["pdf"])

if uploaded_file:
    with st.spinner("Scanning..."):
        df_txn = extract_keyword_credit_transactions(uploaded_file, include_keywords, credit_terms)
        if not df_txn.empty:
            if exclude_keywords:
                pattern = '|'.join(re.escape(ek) for ek in exclude_keywords)
                df_txn = df_txn[~df_txn['Narration'].str.lower().str.contains(pattern)]
            if not df_txn.empty:
                df_txn['Month'] = df_txn['Date'].dt.to_period("M")
                for m in sorted(df_txn['Month'].unique()):
                    st.subheader(f"📅 {m}")
                    mdf = df_txn[df_txn['Month'] == m]
                    st.dataframe(mdf, use_container_width=True)
                    st.markdown(f"**Total for {m}: ₹{mdf['Amount'].sum():,.2f}**")
            else:
                st.warning("No transactions left after exclude filter.")
        else:
            st.error("No matching credit transactions found.")
else:
    st.info("Upload a bank statement PDF to start.")
