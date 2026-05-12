import streamlit as st
import pandas as pd
import os
from datetime import datetime
from fpdf import FPDF
from PIL import Image
import io

# --- 1. Folder & File Setup ---
for folder in ["uploads", "papers"]:
    if not os.path.exists(folder):
        os.makedirs(folder)

DB_FILE = "faculty_database.xlsx"

# --- 2. Logic Functions ---
def save_to_excel(new_data_dict):
    """Appends data to Excel to ensure it persists after refresh."""
    new_df = pd.DataFrame([new_data_dict])
    if os.path.exists(DB_FILE):
        existing_df = pd.read_excel(DB_FILE)
        updated_df = pd.concat([existing_df, new_df], ignore_index=True)[cite: 1]
        updated_df.to_excel(DB_FILE, index=False)
    else:
        new_df.to_excel(DB_FILE, index=False)

def generate_pdf_report(data, photo_path):
    """Generates a professional PDF report for the faculty member."""
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Faculty Performance Report", ln=True, align='C')
    pdf.ln(10)

    # Profile Photo
    if photo_path and os.path.exists(photo_path):
        pdf.image(photo_path, x=150, y=30, w=40)

    # Basic Info
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(40, 10, "Name: ", 0)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, data['Name'], ln=True)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(40, 10, "Faculty ID: ", 0)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, str(data['Faculty_ID']), ln=True)

    pdf.ln(15)

    # Workload & Research
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, " Academic & Research Details", ln=True, fill=True)
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 10, f"Subjects: {data['Subjects']}")
    pdf.multi_cell(0, 10, f"Labs: {data['Labs']}")
    pdf.ln(5)
    pdf.multi_cell(0, 10, f"Research Paper: {data['Paper_Title']}")
    pdf.multi_cell(0, 10, f"Publisher: {data['Publisher']}")

    # Final Score
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(39, 174, 96)
    pdf.cell(0, 10, f"Calculated Performance Score: {data['Total_Score']}", ln=True, align='C')

    return pdf.output(dest='S').encode('latin-1')

# --- 3. Streamlit Interface ---
st.set_page_config(page_title="Faculty ERP System", layout="wide")
st.title("🎓 Faculty ERP & Performance Analytics")

with st.form("faculty_erp_form", clear_on_submit=True):
    c1, c2 = st.columns(2)
    
    with c1:
        name = st.text_input("Full Name")
        f_id = st.text_input("Faculty ID")
        photo_file = st.file_uploader("Upload Profile Picture", type=['jpg', 'png', 'jpeg'])

    with c2:
        subjects = st.multiselect("Subjects Handled", ["Machine Learning", "Data Science", "Python", "Software Engineering"])
        labs = st.multiselect("Labs Handled", ["CS Lab 1", "Hardware Lab", "AI Project Lab"])
        pdf_file = st.file_uploader("Upload Research Paper (PDF)", type=['pdf'])

    st.divider()
    st.subheader("Research Details")
    paper_title = st.text_input("Research Paper Title")
    publisher_name = st.text_input("Publisher's Name")
    
    submitted = st.form_submit_button("Submit Data & Generate Report")

if submitted:
    if not name or not f_id:
        st.error("Name and Faculty ID are required.")
    else:
        # Process Files
        photo_path = "None"
        if photo_file:
            photo_path = os.path.join("uploads", f"{f_id}_{photo_file.name}")
            with open(photo_path, "wb") as f:
                f.write(photo_file.getbuffer())

        pdf_path = "None"
        if pdf_file:
            pdf_path = os.path.join("papers", f"{f_id}_{pdf_file.name}")
            with open(pdf_path, "wb") as f:
                f.write(pdf_file.getbuffer())

        # Calculate Score
        score = (len(subjects) * 10) + (len(labs) * 15) + (50 if pdf_file else 0)

        # Create Record
        faculty_record = {
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Name": name,
            "Faculty_ID": f_id,
            "Subjects": ", ".join(subjects),
            "Labs": ", ".join(labs),
            "Paper_Title": paper_title if paper_title else "N/A",
            "Publisher": publisher_name if publisher_name else "N/A",
            "Photo_Path": photo_path,
            "Paper_Path": pdf_path,
            "Total_Score": score
        }

        # Save to Permanent Excel
        save_to_excel(faculty_record)
        
        st.success(f"Record saved for {name}!")

        # Generate and provide PDF for download
        pdf_bytes = generate_pdf_report(faculty_record, photo_path)
        st.download_button(
            label="📥 Download Faculty Report (PDF)",
            data=pdf_bytes,
            file_name=f"Report_{f_id}.pdf",
            mime="application/pdf"
        )

# --- 4. Database View ---
st.divider()
st.subheader("📋 Master Faculty Database")
if os.path.exists(DB_FILE):
    df = pd.read_excel(DB_FILE)
    st.dataframe(df, use_container_width=True)
    
    with open(DB_FILE, "rb") as f:
        st.download_button("Excel Database Download", f, file_name="Faculty_Data.xlsx")
