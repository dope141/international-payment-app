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

# --- Regex patterns ---
DATE_RE = re.compile(
    r'\b\d{2}[-/\.]\d{2}[-/\.]\d{4}\b|'    # dd-mm-yyyy / dd/mm/yyyy
    r'\b\d{4}[-/\.]\d{2}[-/\.]\d{2}\b|'    # yyyy-mm-dd
    r'\b\d{2}[-/\.]\d{2}[-/\.]\d{2}\b|'    # dd-mm-yy / dd/mm/yy
    r'\b\d{2}\s+[A-Za-z]{3}\s+\d{4}\b|'    # 02 Jan 2025
    r'\b[A-Za-z]{3,9}\s+\d{2},\s+\d{4}\b'  # January 02, 2025
)

AMT_CRDR_RE = re.compile(
    r'(?P<amount>(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)[ ]*(?P<dir>CR|DR)?\b',
    re.IGNORECASE
)

# --- Helpers ---
def get_month_year(date_str: str) -> str:
    if not date_str:
        return ''
    try:
        if '-' in date_str or '/' in date_str or '.' in date_str:
            delim = '-' if '-' in date_str else '/' if '/' in date_str else '.'
            parts = date_str.split(delim)
            if len(parts[0]) == 4:        # yyyy-mm-dd
                year, month = parts[0], parts[1]
            elif len(parts[2]) == 4:      # dd-mm-yyyy
                month, year = parts[1], parts[2]
            else:                         # dd-mm-yy → assume 20yy
                month, year = parts[1], "20" + parts[2]
            return f"{month.zfill(2)}-{year}"
        if re.match(r'\d{2}\s+[A-Za-z]{3}\s+\d{4}', date_str):
            _, mon, year = date_str.split()
            return f"{mon}-{year}"
        if re.match(r'[A-Za-z]{3,9}\s+\d{2},\s+\d{4}', date_str):
            parts = date_str.replace(',', '').split()
            mon, year = parts[0], parts[2]
            return f"{mon}-{year}"
    except Exception:
        pass
    return ''

def extract_tabular_from_pdf(uploaded_file):
    all_keywords = [kw.lower() for kw in (
        CURRENCIES + DEFAULT_INTL_METHODS + DEFAULT_ECOM + DEFAULT_FOREX_PROVIDERS + DEFAULT_PURPOSE_CODES
    )]

    transactions = []
    with pdfplumber.open(uploaded_file) as pdf:
        last_date = ""
        for page in pdf.pages:
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    df = pd.DataFrame(table)
                    for _, row in df.iterrows():
                        row_str = " ".join(str(x) for x in row if pd.notna(x)).lower()
                        found = [kw for kw in all_keywords if kw in row_str]
                        if found:
                            date_val = None
                            for cell in row:
                                if pd.notna(cell) and DATE_RE.search(str(cell)):
                                    date_val = DATE_RE.search(str(cell)).group()
                                    break
                            if date_val:
                                last_date = date_val
                            amt_val, drcr = None, ""
                            for cell in row:
                                if pd.notna(cell):
                                    m_amt = AMT_CRDR_RE.search(str(cell))
                                    if m_amt:
                                        amt_val = float(m_amt.group("amount").replace(",", ""))
                                        drcr = (m_amt.group("dir") or "").upper()
                            if amt_val is not None:
                                transactions.append({
                                    "Date": date_val or last_date,
                                    "Amount": amt_val,
                                    "DRCR": drcr,
                                    "Keyword": ", ".join(sorted(set(found)))
                                })
            else:
                lines = (page.extract_text() or "").split("\n")
                for line in lines:
                    lcase = line.lower()
                    m_date = DATE_RE.search(line)
                    if m_date:
                        last_date = m_date.group()
                    found = [kw for kw in all_keywords if kw in lcase]
                    m_amt = AMT_CRDR_RE.search(line)
                    if found and m_amt:
                        amt_val = float(m_amt.group("amount").replace(",", ""))
                        drcr = (m_amt.group("dir") or "").upper()
                        transactions.append({
                            "Date": last_date,
                            "Amount": amt_val,
                            "DRCR": drcr,
                            "Keyword": ", ".join(sorted(set(found)))
                        })
    return transactions

# --- Streamlit Layout ---
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
                df["Month-Year"] = df["Date"].apply(get_month_year)
                df["Signed Amount"] = df.apply(
                    lambda r: r["Amount"] if r["DRCR"] == "CR" else -r["Amount"], axis=1
                )

                def filter_row(row):
                    kw_lower = (row["Keyword"] or "").lower()
                    include = any(kw in kw_lower for kw in include_keywords) if include_keywords else True
                    exclude = any(kw in kw_lower for kw in exclude_keywords) if exclude_keywords else False
                    return include and not exclude

                df_filtered = df[df.apply(filter_row, axis=1)].copy()

                months = sorted(df_filtered["Month-Year"].dropna().unique())
                for m in months:
                    month_df = df_filtered[df_filtered["Month-Year"] == m].copy()
                    st.markdown(f"### Transactions for {m}")
                    st.dataframe(month_df[["Date", "Amount", "DRCR", "Keyword"]].reset_index(drop=True))
                    cr_total = month_df.loc[month_df["DRCR"] == "CR", "Amount"].sum()
                    dr_total = month_df.loc[month_df["DRCR"] == "DR", "Amount"].sum()
                    net_total = month_df["Signed Amount"].sum()
                    st.markdown(
                        f"**Total CR:** {cr_total:,.2f} &nbsp;&nbsp; "
                        f"**Total DR:** {dr_total:,.2f} &nbsp;&nbsp; "
                        f"**Net:** {net_total:,.2f}"
                    )
                    st.markdown("---")
        else:
            st.warning("CSV handling remains same as before.")
    else:
        st.info("Upload a CSV or PDF file to begin.")
