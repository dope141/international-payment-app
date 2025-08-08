import streamlit as st
import pdfplumber
import re

st.title("International Payments Date Extractor")

st.write("""
Upload your bank statement PDF and extract the dates when international payments were received.
Add or change keywords for filtering in the sidebar (comma-separated).
""")

# --- Sidebar for keyword entry ---
keywords_input = st.sidebar.text_area(
    "Enter Keywords to Search (comma-separated):",
    value="SWIFT, INTL, USD, EUR, GBP"
)
keywords = [kw.strip().upper() for kw in keywords_input.split(",") if kw.strip()]

uploaded_file = st.file_uploader("Upload your bank statement PDF", type=["pdf"])

if uploaded_file is not None:
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            full_text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"

        # Split text into lines
        lines = full_text.split("\n")

        # Filter lines with any keyword
        filtered_lines = [line for line in lines if any(kw in line.upper() for kw in keywords)]

        st.write(f"Found {len(filtered_lines)} matching line(s).")

        # Look for date patterns (supports DD/MM/YYYY, DD-MM-YYYY, etc.)
        date_pattern = re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b')

        found_dates = []
        for line in filtered_lines:
            matches = date_pattern.findall(line)
            if matches:
                found_dates.extend(matches)

        unique_dates = sorted(set(found_dates))

        if unique_dates:
            st.subheader("Dates of International Payments:")
            for date in unique_dates:
                st.write(date)
        else:
            st.info("No payment dates found for the given keywords. Try adjusting your keywords or check your statement format.")
    except Exception as e:
        st.error(f"Error reading the PDF: {e}")

else:
    st.info("Please upload a PDF file to get started.")
