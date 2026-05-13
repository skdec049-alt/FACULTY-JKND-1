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
# Replace this with your actual Folder ID from the Google Drive URL
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

def upload_to_drive(uploaded_file, folder_id):
    try:
        # 1. Setup Metadata
        file_metadata = {
            'name': uploaded_file.name,
            'parents': [folder_id] # Forces file into your shared folder
        }
        
        # 2. Prepare the file stream
        uploaded_file.seek(0)
        file_content = uploaded_file.read()
        media = MediaIoBaseUpload(
            io.BytesIO(file_content), 
            mimetype=uploaded_file.type, 
            resumable=False  # Switch to False for smaller files to avoid some quota checks
        )

        # 3. Execute with 'supportsAllDrives'
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id',
            supportsAllDrives=True # Required if the folder is in a Shared Drive
        ).execute()
        
        return file.get('id'), "Success"

    except Exception as e:
        # This will print the specific error in your Streamlit UI for debugging
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
    pdf.cell(40, 10, f"Name: {data['Name']}", ln=True)
    pdf.cell(40, 10, f"Faculty ID: {data['Faculty_ID']}", ln=True)
    pdf.ln(10)
    
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(0, 10, " Academic & Research Summary", ln=True, fill=True)
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 10, f"Subjects: {data['Subjects']}\nLabs: {data['Labs']}\nPaper: {data['Paper_Title']}\nPublisher: {data['Publisher']}")
    
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(39, 174, 96)
    pdf.cell(0, 10, f"Total Performance Score: {data['Total_Score']}", ln=True, align='C')
    
    return pdf.output(dest='S').encode('latin-1')

# --- 3. SIDEBAR NAVIGATION ---
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
                # Upload files to Drive and get URLs
                photo_url, _ = upload_to_drive(photo_file, DRIVE_FOLDER_ID) if photo_file else ("None", "")
                pdf_url, _ = upload_to_drive(pdf_file, DRIVE_FOLDER_ID) if pdf_file else ("None", "")

                # Score calculation
                score = (len(subjects) * 10) + (len(labs) * 15) + (50 if pdf_file else 0)
                
                # Prepare row for Google Sheets
                record = [
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    name, f_id, ", ".join(subjects), ", ".join(labs),
                    p_title, pub_name, photo_url, pdf_url, score
                ]
                
                # Save permanently to Sheet
                append_to_gsheet(record)
                st.success("Data and files saved permanently to Google Cloud!")
        else:
            st.error("Name and ID are required.")

# --- 5. PAGE: ADMIN DASHBOARD ---
elif page == "Admin Dashboard":
    st.title("🔒 Admin Control Panel")
    password = st.sidebar.text_input("Enter Admin Password", type="password")
    
    if password == ADMIN_PASSWORD:
        # Pull data from Google Sheets for display
        sheet = client.open(SHEET_NAME).sheet1
        data = sheet.get_all_records()
        
        if data:
            df = pd.DataFrame(data)
            st.subheader("Faculty Master Database")
            st.dataframe(df, use_container_width=True)
            
            st.divider()
            st.subheader("Generate Individual Reports")
            selected_faculty = st.selectbox("Select Faculty", df['Name'].tolist())
            
            if selected_faculty:
                user_row = df[df['Name'] == selected_faculty].iloc[0].to_dict()
                pdf_bytes = generate_pdf_report(user_row)
                st.download_button(f"📥 Download Report for {selected_faculty}", pdf_bytes, f"{selected_faculty}_Report.pdf")
        else:
            st.info("No records found in Google Sheets.")
    elif password != "":
        st.error("Incorrect Password.")
