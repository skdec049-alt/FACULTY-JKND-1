import streamlit as st
import pandas as pd
import os
from datetime import datetime
from fpdf import FPDF
from PIL import Image

# --- 1. Configuration & Persistence Setup ---
DB_FILE = "faculty_database.xlsx"
ADMIN_PASSWORD = "admin123"  # Change this to your preferred password

for folder in ["uploads", "papers"]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# --- 2. Core Functions ---
def save_to_excel(new_data_dict):
    """Appends data to the Excel file to ensure permanent storage."""
    new_df = pd.DataFrame([new_data_dict])
    if os.path.exists(DB_FILE):
        existing_df = pd.read_excel(DB_FILE)
        updated_df = pd.concat([existing_df, new_df], ignore_index=True)
        updated_df.to_excel(DB_FILE, index=False)
    else:
        new_df.to_excel(DB_FILE, index=False)

def generate_pdf_report(data):
    """Generates a professional PDF report from a data row."""
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Faculty Performance Report", ln=True, align='C')
    pdf.ln(10)

    # Profile Photo (if path exists and is not 'None')
    photo_path = data.get('Photo_Path', 'None')
    if photo_path != 'None' and os.path.exists(photo_path):
        pdf.image(photo_path, x=150, y=30, w=40)

    # Basic Info
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(40, 10, "Name: ", 0)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, str(data['Name']), ln=True)

    pdf.cell(40, 10, "Faculty ID: ", 0)
    pdf.cell(0, 10, str(data['Faculty_ID']), ln=True)

    pdf.ln(15)
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, " Academic & Research Summary", ln=True, fill=True)
    
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 10, f"Subjects: {data['Subjects']}")
    pdf.multi_cell(0, 10, f"Labs: {data['Labs']}")
    pdf.multi_cell(0, 10, f"Research Title: {data['Paper_Title']}")
    pdf.multi_cell(0, 10, f"Publisher: {data['Publisher']}")

    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(39, 174, 96)
    pdf.cell(0, 10, f"Total Performance Score: {data['Total_Score']}", ln=True, align='C')

    return pdf.output(dest='S').encode('latin-1')

# --- 3. Sidebar Navigation ---
st.set_page_config(page_title="Faculty ERP System", layout="wide")
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Faculty Submission", "Admin Dashboard"])

# --- 4. Page: Faculty Submission ---
if page == "Faculty Submission":
    st.title("🎓 Faculty API SYSTEM")
    
    with st.form("faculty_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name")
            f_id = st.text_input("Faculty ID")
            photo_file = st.file_uploader("Upload Profile Picture", type=['jpg', 'png', 'jpeg'])
        with col2:
            subjects = st.multiselect("Subjects Handled", ["Machine Learning", "Data Science", "Python", "Software Engineering"])
            labs = st.multiselect("Labs Handled", ["CS Lab 1", "Hardware Lab", "AI Project Lab"])
            pdf_file = st.file_uploader("Upload Research Paper (PDF)", type=['pdf'])

        st.subheader("Research Details")
        p_title = st.text_input("Research Paper Title")
        pub_name = st.text_input("Publisher Name")
        
        submitted = st.form_submit_button("Submit Details")

    if submitted:
        if name and f_id:
            # Handle Photo
            photo_path = "None"
            if photo_file:
                photo_path = os.path.join("uploads", f"{f_id}_{photo_file.name}")
                with open(photo_path, "wb") as f: f.write(photo_file.getbuffer())

            # Handle PDF
            pdf_path = "None"
            if pdf_file:
                pdf_path = os.path.join("papers", f"{f_id}_{pdf_file.name}")
                with open(pdf_path, "wb") as f: f.write(pdf_file.getbuffer())

            # Score & Save
            score = (len(subjects) * 10) + (len(labs) * 15) + (50 if pdf_file else 0)
            record = {
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Name": name, "Faculty_ID": f_id, "Subjects": ", ".join(subjects),
                "Labs": ", ".join(labs), "Paper_Title": p_title, "Publisher": pub_name,
                "Photo_Path": photo_path, "Paper_Path": pdf_path, "Total_Score": score
            }
            save_to_excel(record)
            st.success("Data submitted successfully! Admin will review your record.")
        else:
            st.error("Please enter Name and Faculty ID.")

# --- 5. Page: Admin Dashboard ---
elif page == "Admin Dashboard":
    st.title("🔒 Admin Control Panel")
    
    password = st.sidebar.text_input("Enter Admin Password", type="password")
    
    if password == ADMIN_PASSWORD:
        st.subheader("Faculty Master Database")
        if os.path.exists(DB_FILE):
            df = pd.read_excel(DB_FILE)
            st.dataframe(df, use_container_width=True)
            
            st.divider()
            st.subheader("Generate Individual Reports")
            
            # Select individual faculty for PDF download
            faculty_list = df['Name'].tolist()
            selected_faculty = st.selectbox("Select Faculty to Download PDF", faculty_list)
            
            if selected_faculty:
                # Get the row for selected faculty
                user_data = df[df['Name'] == selected_faculty].iloc[0].to_dict()
                
                # Generate PDF
                pdf_bytes = generate_pdf_report(user_data)
                
                st.download_button(
                    label=f"📥 Download Report for {selected_faculty}",
                    data=pdf_bytes,
                    file_name=f"{selected_faculty}_Report.pdf",
                    mime="application/pdf"
                )
                
            # Master Excel Download
            with open(DB_FILE, "rb") as f:
                st.sidebar.download_button("Download Full Excel Database", f, file_name="Faculty_Master_List.xlsx")
        else:
            st.info("No records found in the database yet.")
    elif password != "":
        st.error("Incorrect Password.")
    else:
        st.warning("Please enter the password in the sidebar to access data.")
