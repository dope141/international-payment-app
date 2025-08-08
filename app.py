import streamlit as st
import pdfplumber
import re
import pandas as pd

st.title("International Transaction Date and Amount Extractor")

st.write("""
Upload your bank statement PDF to find out on which dates you received international payments, and for how much.
You can adjust the keywords in the sidebar to improve detection.
The app also displays total transactions and amount received per month.
""")

# --- Sidebar for customizable keywords ---
default_keywords = "SWIFT, INTL, USD, EUR, GBP"
keywords_input = st.sidebar.text_area(
    "Enter International Payment Keywords (comma-separated):",
    value=default_keywords
)
keywords = [kw.strip().upper() for kw in keywords_input.split(",") if kw.strip()]

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

        # Filter lines containing any keyword
        filtered_lines = [
            line for line in lines
            if any(kw in line.upper() for kw in keywords)
        ]

        st.write(f"Found {len(filtered_lines)} possible international payment lines.")

        # Regex patterns
        date_pattern = re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b')
        amount_pattern = re.compile(r'([A-Za-z]{0,3}[\s$₹€£]?\d{1,3}(?:,\d{3})*(?:\.\d{2})?)')

        transactions = []  # list of (date_str, amount_str)
        for line in filtered_lines:
            dates = date_pattern.findall(line)
            amounts = amount_pattern.findall(line)
            if dates and amounts:
                transactions.append((dates[0], amounts[0]))
            elif dates:
                transactions.append((dates[0], "(Amount not found)"))

        if not transactions:
            st.info("No payment dates and amounts found. Try adjusting your keywords or check your statement format.")
        else:
            # Show individual transactions (dates and amounts)
            st.subheader("International Payment Dates and Amounts:")
            df_trans = pd.DataFrame(transactions, columns=["Date", "Amount"])
            st.table(df_trans)

            # Convert Date to datetime for grouping
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

            df_trans["ParsedDate"] = df_trans["Date"].apply(parse_date)
            df_trans = df_trans.dropna(subset=["ParsedDate"])

            def clean_amount(a):
                a_clean = re.sub(r'[^\d.,]', '', a)
                a_clean = a_clean.replace(',', '')
                try:
                    return float(a_clean)
                except:
                    return 0.0

            df_trans["AmountValue"] = df_trans["Amount"].apply(clean_amount)

            df_trans["YearMonth"] = df_trans["ParsedDate"].dt.to_period('M')

            monthly_summary = df_trans.groupby("YearMonth").agg(
                Total_Transactions=("Date", "count"),
                Total_Amount=("AmountValue", "sum"),
            ).reset_index()

            monthly_summary["YearMonth"] = monthly_summary["YearMonth"].dt.strftime('%b %Y')

            st.subheader("Monthly Summary of International Transactions:")
            st.dataframe(monthly_summary.rename(columns={
                "YearMonth": "Month",
                "Total_Transactions": "Number of Transactions",
                "Total_Amount": "Total Amount Received"
            }))

    except Exception as e:
        st.error(f"Error reading the PDF: {e}")

else:
    st.info("Please upload a PDF file to get started.")
