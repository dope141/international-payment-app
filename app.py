import streamlit as st
import pandas as pd
import re
from datetime import datetime
import requests

# ===== Default Filters =====
DEFAULT_CURRENCIES = ["USD","EUR","GBP","AUD","CAD","JPY","CHF","SGD","AED","NZD","ZAR","HKD","SAR","MYR","NOK","SEK","DKK","KRW",
"MXN","BRL","TRY","PLN","CZK","HUF","ILS","THB","IDR","TWD","COP","RUB","CNY","XOF","KES","PHP","ARS","EGP","PKR","BDT","VND","LKR",
"QAR","UAH","CLP","ISK","BGN","RON","HNL","NGN","HRK","UYU","JOD","OMR"]

DEFAULT_INTL_METHODS = ["swift","iban","ach","fedwire","sepa","chaps","rtgs","neft","imps","wire transfer","bacs","eft","telex transfer",
"faster payments","direct deposit","remitly","moneygram","western union","xoom","paypal","stripe","skrill",
"payoneer","wise","revolut","currencycloud","instarem","paysera","alipay","wechat pay","google pay","apple pay",
"amazon pay","jcb","maestro","visa","mastercard","american express","discover","unionpay","zelle","interac",
"venmo","square cash","payson","klarna","afterpay","trustly","billpay","poli","sofort","giropay","multibanco",
"euteller","eps","ideal","bank giro"]

DEFAULT_ECOM = ["amazon","ebay","flipkart","aliexpress","fiverr","upwork","freelancer","shopify","etsy","stripe","instamojo",
"razorpay","paytm","wise","skrill","bigcommerce","walmart","zomato","swiggy","uber","ola","zoom","netflix",
"spotify","linkedin","airtasker","taskrabbit","payoneer","paypal"]

DEFAULT_FOREX_PROVIDERS = ["skydo","wise","payoneer","briskpay","worldremit","remitly","xoom","transferwise","dbs remittance",
"westernunion","moneygram","azimo","revolut","instarem","currencycloud","skrill","neteller","paysera","paypal","paypalx"]

DEFAULT_PURPOSE_CODES = [
    # full P- and S-series list
    "P0001","P0002","P0003","P0004","P0005","P0006","P0007","P0008","P0009","P0010","P0011","P0012","P0013","P0014","P0015","P0016","P0017","P0018",
    "P0101","P0102","P0103","P0104","P0105","P0106","P0107","P0108","P0201","P0202","P0203","P0204","P0205","P0206","P0207","P0208","P0209","P0210",
    "P0211","P0212","P0213","P0301","P0302","P0303","P0304","P0305","P0306","P0307","P0308","P0401","P0402","P0403","P0404","P0501","P0502","P0601",
    "P0602","P0603","P0604","P0605","P0606","P0701","P0702","P0703","P0801","P0802","P0803","P0804","P0805","P0806","P0807","P0901","P0902","P1001",
    "P1002","P1003","P1004","P1005","P1006","P1007","P1008","P1009","P1010","P1011","P1012","P1013","P1014","P1015","P1016","P1017","P1018","P1019",
    "P1101","P1102","P1201","P1202","P1203","P1301","P1302","P1303","P1304","P1305","P1306","P1401","P1402","P1403","P1404","P1405","P1406","P1407",
    "P1501","P1502","P1503","P1504","P1505","P1506","P1507","P1508","P1509","P1510","P1590",
    "S0001","S0002","S0003","S0004","S0005","S0006","S0007","S0008","S0009","S0010","S0011","S0012","S0013","S0014","S0015","S0016","S0017","S0018",
    "S0101","S0102","S0103","S0104","S0105","S0106","S0107","S0108","S0109","S0110","S0111","S0112","S0113","S0114","S0115","S0116","S0117","S0118",
    "S0119","S0120","S0130","S0131","S0132","S0133","S0134","S0135","S0136","S0137","S0138","S0139","S0140","S0141","S0142","S0143","S0144","S0145",
    "S0146","S0147","S0148","S0149","S0150","S0190","S0201","S0202","S0203","S0204","S0205","S0206","S0207","S0208","S0209","S0210","S0211","S0212",
    "S0213","S0301","S0302","S0303","S0304","S0305","S0306","S0401","S0402","S0403","S0404","S0501","S0502","S0601","S0602","S0603","S0604","S0605",
    "S0606","S0701","S0702","S0703","S0801","S0802","S0803","S0804","S0805","S0806","S0901","S0902","S1001","S1002","S1003","S1004","S1005","S1006",
    "S1007","S1008","S1009","S1010","S1011","S1012","S1013","S1014","S1015","S1016","S1017","S1018","S1019","S1101","S1102","S1201","S1202","S1301",
    "S1302","S1303","S1304","S1305","S1306","S1401","S1402","S1403","S1404","S1405","S1406","S1407","S1501","S1502","S1503","S1504"
]

CREDIT_TERMS = ["cr","credit","credited","credit received","amount received","payment received",
"transfer received","deposit","inward remittance","remittance credit","incoming payment","proceeds"]

# ==== API-based Parser ====
def parse_pdf_api(file, api_key, api_url):
    headers = {"Authorization": f"Bearer {api_key}"}
    files = {"file": (file.name, file, "application/pdf")}
    try:
        resp = requests.post(api_url, headers=headers, files=files)
        if resp.status_code == 200:
            data = resp.json()
            if "transactions" in data:
                return pd.DataFrame(data["transactions"])
            else:
                return pd.DataFrame(data)
        else:
            st.error(f"API error: {resp.status_code} - {resp.text}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"API request failed: {e}")
        return pd.DataFrame()

# ==== Filtering Logic ====
def filter_international_credits(df, include_keywords, credit_terms):
    inc_lower = [k.lower() for k in include_keywords]
    credit_lower = [ct.lower() for ct in credit_terms]
    matches = []
    for _, row in df.iterrows():
        narr = str(row["Narration"]).lower()
        if any(ct in narr for ct in credit_lower) and any(k in narr for k in inc_lower):
            matches.append(row)
    return pd.DataFrame(matches)

# ==== UI ====
st.set_page_config(page_title="International Credit Detector (OCR only)", layout="wide")
st.title("🌐 International Credited Transactions Detector (OCR API Only)")

st.sidebar.header("Filters")
extra_inc = st.sidebar.text_area("Add Include Keywords", "")
extra_exc = st.sidebar.text_area("Add Exclude Keywords", "")

with st.sidebar.expander("Default: Currencies"): st.write(", ".join(DEFAULT_CURRENCIES))
with st.sidebar.expander("Default: Intl Payment Methods"): st.write(", ".join(DEFAULT_INTL_METHODS))
with st.sidebar.expander("Default: E-commerce"): st.write(", ".join(DEFAULT_ECOM))
with st.sidebar.expander("Default: Forex Providers"): st.write(", ".join(DEFAULT_FOREX_PROVIDERS))
with st.sidebar.expander("Default: Purpose Codes"): st.write(", ".join(DEFAULT_PURPOSE_CODES))
with st.sidebar.expander("Default: Credit Terms"): st.write(", ".join(CREDIT_TERMS))

include_keywords = (
    DEFAULT_CURRENCIES +
    DEFAULT_INTL_METHODS +
    DEFAULT_ECOM +
    DEFAULT_FOREX_PROVIDERS +
    DEFAULT_PURPOSE_CODES +
    [k.strip() for k in extra_inc.split(",") if k.strip()]
)
exclude_keywords = [k.strip().lower() for k in extra_exc.split(",") if k.strip()]

api_key = st.sidebar.text_input("OCR API Key", type="password")
api_url = st.sidebar.text_input("OCR API Endpoint URL", value="")

uploaded_file = st.file_uploader("Upload Bank Statement PDF", type=["pdf"])

if uploaded_file:
    if not api_key or not api_url:
        st.error("Please enter your OCR API key and endpoint to proceed.")
    else:
        st.info("Using OCR API for extraction…")
        df_all = parse_pdf_api(uploaded_file, api_key, api_url)
        if not df_all.empty:
            df_filtered = filter_international_credits(df_all, include_keywords, CREDIT_TERMS)
            if exclude_keywords and not df_filtered.empty:
                pat = '|'.join(re.escape(k) for k in exclude_keywords)
                df_filtered = df_filtered[~df_filtered["Narration"].str.lower().str.contains(pat)]
            if not df_filtered.empty:
                df_filtered["Date"] = pd.to_datetime(df_filtered["Date"], errors="coerce")
                df_filtered = df_filtered.dropna(subset=["Date"])
                df_filtered["Month"] = df_filtered["Date"].dt.to_period("M")
                for m in sorted(df_filtered["Month"].unique()):
                    st.subheader(f"📅 {m}")
                    mdf = df_filtered[df_filtered["Month"] == m]
                    st.dataframe(mdf, use_container_width=True)
                    if "Amount" in mdf.columns:
                        st.markdown(f"**Total: ₹{mdf['Amount'].sum():,.2f}**")
                csv = df_filtered.to_csv(index=False).encode("utf-8")
                st.download_button("⬇️ Download CSV", csv, "international_credits.csv", "text/csv")
            else:
                st.warning("No transactions match the filters.")
        else:
            st.error("No transactions extracted from OCR API.")
else:
    st.info("Upload a PDF to start.")
