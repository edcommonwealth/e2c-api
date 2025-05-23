import streamlit as st
st.set_page_config(page_title="Graduation Dashboard", layout="wide")

import pandas as pd
from sodapy import Socrata
from fpdf import FPDF
from io import BytesIO
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
SOCRATA_APP_TOKEN = os.getenv("SOCRATA_APP_TOKEN")

# Socrata Client
client = Socrata("educationtocareer.data.mass.gov", SOCRATA_APP_TOKEN)

# --------------------------
# 🔧 Get Filter Options
# --------------------------
@st.cache_data
def get_filter_options():
    sample = client.get("n2xa-p822", limit=1000)
    df = pd.DataFrame.from_records(sample)
    return {
        "org_types": sorted(df["org_type"].dropna().unique()),
        "school_years": sorted(df["sy"].dropna().unique(), reverse=True),
        "rate_types": sorted(df["grad_rate_type"].dropna().unique()),
        "student_groups": sorted(df["stu_grp"].dropna().unique())
    }

filter_options = get_filter_options()

# --------------------------
# 📥 Load Filtered Data
# --------------------------
@st.cache_data(show_spinner="Loading filtered data...")
def fetch_filtered_data(org_type, sy, grad_rate_type, stu_grp, max_rows=50000):
    where_clause = (
        f"org_type='{org_type}' AND sy='{sy}' AND "
        f"grad_rate_type='{grad_rate_type}' AND stu_grp='{stu_grp}'"
    )

    all_data = []
    offset = 0

    while True:
        rows = client.get("n2xa-p822", where=where_clause, limit=50000, offset=offset)
        if not rows:
            break
        all_data.extend(rows)
        if len(rows) < 50000 or len(all_data) >= max_rows:
            break
        offset += 50000

    df = pd.DataFrame.from_records(all_data)

    numeric_cols = ['cohort_cnt', 'grad_pct', 'in_sch_pct', 'non_grad_pct', 'ged_pct', 'drpout_pct', 'exclud_pct']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        else:
            df[col] = pd.NA

    return df

# --------------------------
# 🌐 Streamlit UI
# --------------------------
st.title("🎓 Massachusetts Graduation Statistics Dashboard")

# Filters
st.sidebar.header("🔍 Filters")
org_type = st.sidebar.selectbox("Report Type", filter_options["org_types"], index=filter_options["org_types"].index("District"))
sy = st.sidebar.selectbox("School Year", filter_options["school_years"], index=0)
rate_type = st.sidebar.selectbox("Graduation Rate Type", filter_options["rate_types"], index=0)
stu_grp = st.sidebar.selectbox("Student Group", filter_options["student_groups"], index=0)

# Load filtered data
df = fetch_filtered_data(org_type, sy, rate_type, stu_grp)

if df.empty:
    st.warning("⚠️ No data found for the selected filter combination.")
    st.stop()

# Dynamic column name logic
if org_type == "District":
    name_col = 'dist_name'
    code_col = 'dist_code'
    name_label = 'District Name'
    code_label = 'District Code'
elif org_type == "School":
    name_col = 'org_name'
    code_col = 'org_code'
    name_label = 'School Name'
    code_label = 'School Code'
else:
    name_col = 'org_name'
    code_col = 'org_code'
    name_label = 'State Name'
    code_label = 'State Code'

# Rename and filter relevant columns
df_display = df.rename(columns={
    name_col: name_label,
    code_col: code_label,
    'cohort_cnt': '# in Cohort',
    'grad_pct': '% Graduated',
    'in_sch_pct': '% Still in School',
    'non_grad_pct': '% Non-Grad Completers',
    'ged_pct': '% H.S. Equiv.',
    'drpout_pct': '% Dropped Out',
    'exclud_pct': '% Permanently Excluded'
})[[name_label, code_label, '# in Cohort', '% Graduated', '% Still in School',
    '% Non-Grad Completers', '% H.S. Equiv.', '% Dropped Out', '% Permanently Excluded']]

# Add serial number
df_display.insert(0, "S. No.", range(1, len(df_display) + 1))

# Show table
st.subheader(f"Filtered Results ({len(df_display)} rows)")
st.dataframe(df_display, use_container_width=True, hide_index=True)

# --------------------------
# 📤 Export Buttons
# --------------------------
csv_data = df_display.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Download CSV", csv_data, file_name="graduation_stats.csv", mime="text/csv")

def generate_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, txt="Graduation Stats Report", ln=True, align="C")
    pdf.ln(5)
    for _, row in df.iterrows():
        line = ", ".join(str(x) for x in row.values)
        pdf.multi_cell(0, 8, line)
    return pdf.output(dest='S').encode('latin-1')

pdf_bytes = generate_pdf(df_display)
st.download_button("📄 Download PDF", data=pdf_bytes, file_name="graduation_stats.pdf", mime="application/pdf")
