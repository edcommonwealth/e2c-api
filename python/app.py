import streamlit as st
import pandas as pd
import requests
from fpdf import FPDF

# Load data
@st.cache_data
def load_data():
    url = "https://educationtocareer.data.mass.gov/resource/n2xa-p822.json"
    response = requests.get(url)
    df = pd.DataFrame(response.json())
    num_cols = ['cohort_cnt', 'grad_pct', 'in_sch_pct', 'non_grad_pct', 'ged_pct', 'drpout_pct', 'exclud_pct']
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

df = load_data()

st.title("📊 Massachusetts Graduation Statistics Dashboard")

# Sidebar filters
with st.sidebar:
    st.header("Filter Options")
    org_type = st.selectbox("Report Type", [""] + sorted(df['org_type'].dropna().unique().tolist()))
    sy = st.selectbox("School Year", [""] + sorted(df['sy'].dropna().unique().tolist(), reverse=True))
    grad_rate_type = st.selectbox("Rate Type", [""] + sorted(df['grad_rate_type'].dropna().unique().tolist()))
    stu_grp = st.selectbox("Student Group", [""] + sorted(df['stu_grp'].dropna().unique().tolist()))

# Apply filters
filtered = df.copy()
if org_type: filtered = filtered[filtered['org_type'] == org_type]
if sy: filtered = filtered[filtered['sy'] == sy]
if grad_rate_type: filtered = filtered[filtered['grad_rate_type'] == grad_rate_type]
if stu_grp: filtered = filtered[filtered['stu_grp'] == stu_grp]

# Select columns
cols = {
    'dist_name': 'District Name',
    'dist_code': 'District Code',
    'cohort_cnt': '# in Cohort',
    'grad_pct': '% Graduated',
    'in_sch_pct': '% Still in School',
    'non_grad_pct': '% Non-Grad Completers',
    'ged_pct': '% H.S. Equiv.',
    'drpout_pct': '% Dropped Out',
    'exclud_pct': '% Permanently Excluded'
}
display_df = filtered[list(cols.keys())].rename(columns=cols)

# Display
st.dataframe(display_df, use_container_width=True)

# Export options
st.download_button("📥 Download CSV", display_df.to_csv(index=False), "report.csv", "text/csv")

# PDF export
def export_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, txt="Graduation Report", ln=True, align='C')
    for _, row in df.iterrows():
        row_text = ', '.join(str(val) for val in row.values)
        pdf.multi_cell(0, 8, row_text)
    pdf.output("report.pdf")

if st.button("📄 Export PDF"):
    export_pdf(display_df)
    with open("report.pdf", "rb") as f:
        st.download_button("Download PDF", f, "report.pdf", mime="application/pdf")
