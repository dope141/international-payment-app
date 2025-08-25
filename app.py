import streamlit as st
import pandas as pd
import pdfplumber
import re

# === Full filter lists ===
CURRENCIES = [
    "USD","EUR","GBP","AUD","CAD","JPY","CHF","SGD","AED","NZD","ZAR",
    "HKD","SAR","MYR","NOK","SEK","DKK","KRW","MXN","BRL","TRY","PLN","CZK","HUF",
    "ILS","THB","IDR","TWD","COP","RUB","CNY","XOF","KES","PHP","ARS","EGP","PKR",
    "BDT","VND","LKR","QAR","UAH","CLP","ISK","BGN","RON","HNL","NGN","HRK","UYU",
    "JOD","OMR"
]

DEFAULT_INTL_METHODS = [
    "swift","iban","ach","fedwire","sepa","chaps","rtgs","neft","imps","wire transfer","bacs",
    "eft","telex transfer","faster payments","direct deposit","remitly","moneygram",
    "western union","xoom","paypal","stripe","skrill","payoneer","wise","revolut",
    "currencycloud","instarem","paysera","alipay","wechat pay","google pay","apple pay",
    "amazon pay","jcb","maestro","visa","mastercard","american express","discover",
    "unionpay","zelle","interac","venmo","square cash","payson","klarna","afterpay",
    "trustly","billpay","poli","sofort","giropay","multibanco","euteller","eps","ideal",
    "bank giro"
]

DEFAULT_ECOM = [
    "amazon","ebay","flipkart","aliexpress","fiverr","upwork","freelancer","shopify",
    "etsy","stripe","instamojo","razorpay","paytm","wise","skrill","bigcommerce","walmart",
    "zomato","swiggy","uber","ola","zoom","netflix","spotify","linkedin","airtasker",
    "taskrabbit","payoneer","paypal"
]

DEFAULT_FOREX_PROVIDERS = [
    "skydo","wise","payoneer","briskpay","worldremit","remitly","xoom","transferwise",
    "dbs remittance","westernunion","moneygram","azimo","revolut","instarem","currencycloud",
    "skrill","neteller","paysera","paypal","paypalx"
]

DEFAULT_PURPOSE_CODES = [
    "P0001","P0002","P0003","P0004","P0005","P0006","P0007","P0008","P0009","P0010","P0011","P0012",
    "P0013","P0014","P0015","P0016","P0017","P0018","P0101","P0102","P0103","P0104","P0105","P0106",
    "P0107","P0108","P0201","P0202","P0203","P0204","P0205","P0206","P0207","P0208","P0209","P0210",
    "P0211","P0212","P0213","P0301","P0302","P0303","P0304","P0305","P0306","P0307","P0308","P0401",
    "P0402","P0403","P0404","P0501","P0502","P0601","P0602","P0603","P0604","P0605","P0606","P0701",
    "P0702","P0703","P0801","P0802","P0803","P0804","P0805","P0806","P0807","P0901","P0902","P1001",
    "P1002","P1003","P1004","P1005","P1006","P1007","P1008","P1009","P1010","P1011","P1012","P1013",
    "P1014","P1015","P1016","P1017","P1018","P1019","P1101","P1102","P1201","P1202","P1301","P1302",
    "P1303","P1304","P1305","P1306","P1401","P1402","P1403","P1404","P1405","P1406","P1407","P1501",
    "P1502","P1503","P1504","P1505","P1506","P1507","P1508","P1509","P1510","P1590"
]

def extract_tabular_from_pdf(uploaded_file):
    transactions = []
    last_date = ''
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            lines = (page.extract_text() or "").split('\n')
            for line in lines:
                date_match = re.search(
                    r'(\d{2}[-/.]\d{2}[-/.]\d{4})|(\d{4}[-/.]\d{2}[-/.]\d{2})|'
                    r'(\d{2}\s+[A-Za-z]{3}\s+\d{4})|([A-Za-z]{3,9}\s+\d{2},\s+\d{4})',
                    line
                )
                if date_match:
                    last_date = date_match.group()
                lcase = line.lower()
                keywords = CURRENCIES + DEFAULT_INTL_METHODS + DEFAULT_ECOM + DEFAULT_FOREX_PROVIDERS + DEFAULT_PURPOSE_CODES
                found_keywords = [kw.lower() for kw in keywords if kw.lower() in lcase]
                if found_keywords:
                    amt_match = re.search(r'\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\b', line)
                    amount = amt_match.group() if amt_match else ''
                    transactions.append({
                        "Date": last_date,
                        "Amount": amount,
                        "Keyword": ', '.join(sorted(set(found_keywords)))
                    })
    return transactions

def get_month_year(date_str):
    if not date_str:
        return ''
    try:
        delim = '-' if '-' in date_str else '/' if '/' in date_str else '.' if '.' in date_str else None
        if delim:
            parts = date_str.split(delim)
            month = parts[1]
            year = parts[2]
            return f"{month.zfill(2)}-{year}"
        elif re.match(r'\d{2}\s+[A-Za-z]{3}\s+\d{4}', date_str):
            parts = date_str.split()
            month = parts[1]
            year = parts[2]
            return f"{month}-{year}"
        elif re.match(r'[A-Za-z]{3,9}\s+\d{2},\s+\d{4}', date_str):
            parts = date_str.replace(',', '').split()
            month = parts[0]
            year = parts[2]
            return f"{month}-{year}"
    except Exception:
        return ''
    return ''

# Layout setup with columns: Left for filters, right for main content
col_filters, col_main = st.columns([1, 3])

with col_filters:
    st.subheader("Filters (Comma Separated)")
    currencies_input = st.text_area("Currencies", ", ".join(CURRENCIES), height=120)
    methods_input = st.text_area("Payment Methods", ", ".join(DEFAULT_INTL_METHODS), height=120)
    ecom_input = st.text_area("E-Commerce Platforms", ", ".join(DEFAULT_ECOM), height=120)
    forex_input = st.text_area("Forex Providers", ", ".join(DEFAULT_FOREX_PROVIDERS), height=100)
    purpose_codes_input = st.text_area("Purpose Codes", ", ".join(DEFAULT_PURPOSE_CODES), height=120)
    exclude_input = st.text_area("Exclude Keywords", "", height=80)

    include_keywords = set()
    for block in [currencies_input, methods_input, ecom_input, forex_input, purpose_codes_input]:
        include_keywords.update(k.strip().lower() for k in block.split(",") if k.strip())

    exclude_keywords = set(k.strip().lower() for k in exclude_input.split(",") if k.strip())

with col_main:
    st.title("International Transaction Identifier")
    uploaded_file = st.file_uploader("Upload CSV or PDF file", type=["csv", "pdf"])

    if uploaded_file:
        if uploaded_file.name.lower().endswith(".pdf"):
            tabular = extract_tabular_from_pdf(uploaded_file)
            df = pd.DataFrame(tabular)
            if df.empty:
                st.info("No international keywords found in the PDF content.")
            else:
                def filter_row(row):
                    kw_lower = row['Keyword'].lower()
                    include = any(kw in kw_lower for kw in include_keywords)
                    exclude = any(kw in kw_lower for kw in exclude_keywords)
                    return include and not exclude
                df_filtered = df[df.apply(filter_row, axis=1)]
                df_filtered['Month-Year'] = df_filtered['Date'].apply(get_month_year)
                months = sorted(df_filtered['Month-Year'].dropna().unique())
                for m in months:
                    month_df = df_filtered[df_filtered['Month-Year'] == m][['Date','Amount','Keyword']]
                    month_df['Amount'] = pd.to_numeric(month_df['Amount'].str.replace(',',''), errors='coerce').fillna(0)
                    total = month_df['Amount'].sum()
                    st.markdown(f"### Transactions for {m}")
                    st.dataframe(month_df)
                    st.markdown(f"**Total Amount: {total:.2f}**")
                    st.markdown("---")
        elif uploaded_file.name.lower().endswith(".csv"):
            df = pd.read_csv(uploaded_file)
            str_cols = list(df.select_dtypes(include="object").columns)
            scan_cols = st.multiselect("Columns to scan for keywords:", str_cols, default=str_cols)
            flagged_rows = []
            for _, row in df.iterrows():
                for col in scan_cols:
                    val = str(row[col]).lower()
                    include = any(kw in val for kw in include_keywords)
                    exclude = any(kw in val for kw in exclude_keywords)
                    if include and not exclude:
                        flagged_rows.append({
                            "Date": row.get("Date", ""),
                            "Amount": row.get("Amount", ""),
                            "Keyword": val,
                            "Month-Year": get_month_year(str(row.get("Date", "")))
                        })
            df_flagged = pd.DataFrame(flagged_rows)
            if df_flagged.empty:
                st.info("No international keywords detected in the selected columns.")
            else:
                months = sorted(df_flagged['Month-Year'].dropna().unique())
                for m in months:
                    month_df = df_flagged[df_flagged['Month-Year'] == m][['Date','Amount','Keyword']]
                    month_df['Amount'] = pd.to_numeric(month_df['Amount'].str.replace(',',''), errors='coerce').fillna(0)
                    total = month_df['Amount'].sum()
                    st.markdown(f"### Transactions for {m}")
                    st.dataframe(month_df)
                    st.markdown(f"**Total Amount: {total:.2f}**")
                    st.markdown("---")
    else:
        st.info("Upload a CSV or PDF file to begin.")
