import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
from datetime import datetime
from fpdf import FPDF

# --- 1. CLOUD CONFIGURATION ---
DRIVE_FOLDER_ID = "1tKtZVRzlVYIeyvIke8oRRwJ3s3jJPkFy" 
SHEET_NAME = "Faculty_DB" 
ADMIN_PASSWORD = "admin123"

# Authenticate with Google using Secrets
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)

# Initialize Services
client = gspread.authorize(creds)
drive_service = build('drive', 'v3', credentials=creds)

# --- 2. CORE CLOUD FUNCTIONS ---

def append_to_gsheet(record):
    """Saves a single row of data to Google Sheets."""
    try:
        # Open the spreadsheet and the first sheet
        sh = client.open(SHEET_NAME)
        sheet = sh.sheet1
        
        # Add headers if sheet is empty
        if not sheet.get_all_values():
            headers = ["Timestamp", "Name", "Faculty_ID", "Subjects", "Labs", 
                       "Paper_Title", "Publisher", "Photo_ID", "PDF_ID", "Total_Score"]
            sheet.append_row(headers)
            
        sheet.append_row(record)
        return True
    except Exception as e:
        st.error(f"Failed to save to Google Sheets: {e}")
        return False

def upload_to_drive(uploaded_file, folder_id):
    try:
        # 1. Setup Metadata
        file_metadata = {
            'name': uploaded_file.name,
            'parents': [folder_id] 
        }
        
        # 2. Prepare the file stream
        uploaded_file.seek(0) # <--- This must line up with 'file_metadata'
        file_content = uploaded_file.read()
        media = MediaIoBaseUpload(
            io.BytesIO(file_content), 
            mimetype=uploaded_file.type, 
            resumable=False 
        )

        # 3. Execute
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id',
            supportsAllDrives=True 
        ).execute()
        
        return file.get('id'), "Success"

    except Exception as e:
        st.error(f"Internal Drive Error: {str(e)}")
        return "None", str(e)
def generate_pdf_report(data):
    """Generates a professional PDF report."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Faculty Performance Report", ln=True, align='C')
    pdf.ln(10)

    # Basic Info
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Name: {data.get('Name', 'N/A')}", ln=True)
    pdf.cell(0, 10, f"Faculty ID: {data.get('Faculty_ID', 'N/A')}", ln=True)
    pdf.ln(5)
    
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(0, 10, " Academic & Research Summary", ln=True, fill=True)
    pdf.set_font("Arial", '', 11)
    
    summary = (
        f"Subjects: {data.get('Subjects', 'N/A')}\n"
        f"Labs: {data.get('Labs', 'N/A')}\n"
        f"Paper: {data.get('Paper_Title', 'N/A')}\n"
        f"Publisher: {data.get('Publisher', 'N/A')}"
    )
    pdf.multi_cell(0, 10, summary)
    
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(39, 174, 96)
    pdf.cell(0, 10, f"Total Performance Score: {data.get('Total_Score', '0')}", ln=True, align='C')
    
    return pdf.output(dest='S').encode('latin-1')

# --- 3. UI SETUP ---
st.set_page_config(page_title="Faculty ERP Cloud", layout="wide")
page = st.sidebar.radio("Navigation", ["Faculty Submission", "Admin Dashboard"])

# --- 4. PAGE: FACULTY SUBMISSION ---
if page == "Faculty Submission":
    st.title("🎓 Faculty API SYSTEM (Cloud)")
    
    with st.form("faculty_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name")
            f_id = st.text_input("Faculty ID")
            photo_file = st.file_uploader("Profile Picture", type=['jpg', 'png', 'jpeg'])
        with col2:
            subjects = st.multiselect("Subjects", ["Machine Learning", "Data Science", "Python", "Software Engineering"])
            labs = st.multiselect("Labs", ["CS Lab 1", "Hardware Lab", "AI Project Lab"])
            pdf_file = st.file_uploader("Research Paper (PDF)", type=['pdf'])

        st.subheader("Research Details")
        p_title = st.text_input("Research Paper Title")
        pub_name = st.text_input("Publisher Name")
        
        submitted = st.form_submit_button("Submit Details")

    if submitted:
        if name and f_id:
            with st.spinner("Uploading to Google Cloud..."):
                # Upload files
                photo_id, _ = upload_to_drive(photo_file, DRIVE_FOLDER_ID) if photo_file else ("None", "")
                pdf_id, _ = upload_to_drive(pdf_file, DRIVE_FOLDER_ID) if pdf_file else ("None", "")

                # Score calculation
                score = (len(subjects) * 10) + (len(labs) * 15) + (50 if pdf_file else 0)
                
                # Prepare row
                record = [
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    name, f_id, ", ".join(subjects), ", ".join(labs),
                    p_title, pub_name, photo_id, pdf_id, score
                ]
                
                # Save to Sheet
                if append_to_gsheet(record):
                    st.success("Data and files saved permanently to Google Cloud!")
        else:
            st.error("Name and ID are required.")

# --- 5. PAGE: ADMIN DASHBOARD ---
elif page == "Admin Dashboard":
    st.title("🔒 Admin Control Panel")
    password = st.sidebar.text_input("Enter Admin Password", type="password")
    
    if password == ADMIN_PASSWORD:
        try:
            sheet = client.open(SHEET_NAME).sheet1
            data = sheet.get_all_records()
            
            if data:
                df = pd.DataFrame(data)
                st.subheader("Faculty Master Database")
                st.dataframe(df, use_container_width=True)
                
                st.divider()
                st.subheader("Generate Individual Reports")
                selected_faculty = st.selectbox("Select Faculty", df['Name'].unique().tolist())
                
                if selected_faculty:
                    user_row = df[df['Name'] == selected_faculty].iloc[0].to_dict()
                    pdf_bytes = generate_pdf_report(user_row)
                    st.download_button(f"📥 Download Report for {selected_faculty}", pdf_bytes, f"{selected_faculty}_Report.pdf")
            else:
                st.info("No records found in Google Sheets.")
        except Exception as e:
            st.error(f"Could not load data: {e}")
    elif password != "":
        st.error("Incorrect Password.")
