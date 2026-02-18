import streamlit as st



def rtl(text):
    return f'<div style="direction: rtl; text-align: right;">{text}</div>'

def ltr(text):
    return f'<div style="direction: ltr; text-align: left;">{text}</div>'

def render_query_upload_file():

    TASK_TITLE = "Chat with your Database"

    # =============================================================================
    # Page Configuration
    # =============================================================================
    st.set_page_config(
        page_title=f"Injaz Tech | {TASK_TITLE}",
        layout="centered",
        initial_sidebar_state="collapsed"
    )

    # =============================================================================
    # Custom CSS Styling - DO NOT MODIFY
    # =============================================================================
    st.markdown(
        """
        <style>
        .stApp {
            font-family: "Cairo", "Amiri", sans-serif;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("""
    <style>
        /* Main Colors */
        :root {
            --primary-color: #1A81A5;
            --secondary-color: #5AA7C0;
            --bg-color: #f8fafb;
            --card-bg: white;
            --text-dark: #333333;
            --text-light: #666666;
        }
        
        /* Header Styling */
        .main-header {
            background: linear-gradient(135deg, #1A81A5 0%, #5AA7C0 100%);
            padding: 25px;
            border-radius: 12px;
            text-align: center;
            margin-bottom: 30px;
            box-shadow: 0 8px 24px rgba(26, 129, 165, 0.3);
        }
        
        .main-header h1 {
            color: white;
            font-size: 26px;
            margin: 0;
            font-weight: 600;
        }
        
        /* App Background */
        .stApp {
            background-color: #f8fafb;
        }
        
        /* Main Container Shadow */
        .block-container {
            background-color: white;
            border-radius: 16px;
            padding: 2rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            margin-top: 1rem;
        }
        
        /* File Uploader Shadow */
        .stFileUploader > div {
            box-shadow: 0 2px 12px rgba(26, 129, 165, 0.15);
            border-radius: 10px;
        }
        
        /* Text Area Shadow */
        .stTextArea > div {
            box-shadow: 0 2px 12px rgba(26, 129, 165, 0.15);
            border-radius: 10px;
        }
        
        /* Button Styling */
        .stButton > button {
            background: linear-gradient(135deg, #1A81A5 0%, #5AA7C0 100%);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 12px 30px;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(26, 129, 165, 0.3);
            width: 100%;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(26, 129, 165, 0.5);
        }
        
        /* Text Area Border */
        .stTextArea > div > div > textarea {
            border-color: #5AA7C0;
            border-radius: 8px;
        }
        
        /* Info Box */
        .info-box {
            background-color: rgba(26, 129, 165, 0.1);
            border: 1px solid #1A81A5;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
            box-shadow: 0 4px 12px rgba(26, 129, 165, 0.15);
        }
        
        /* Section Title */
        .section-title {
            color: #1A81A5;
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 15px;
            padding-bottom: 8px;
            border-bottom: 2px solid #5AA7C0;
        }
        
        /* Hide Streamlit Branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

    # =============================================================================
    # Logo (Top Right)
    # =============================================================================
    col1, col2 = st.columns([2, 1])
    with col2:
        st.image("assets/injaz.jpg", width=180)
    
    # =============================================================================
    # Header
    # =============================================================================
    st.markdown(f"""
    <div class="main-header">
        <h1>{TASK_TITLE}</h1>
    </div>
    """, unsafe_allow_html=True)

    # =============================================================================
    # File Upload Section
    # =============================================================================
    st.markdown('<p class="section-title">Upload Database</p>', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "Upload your database file",
        type=['db', 'sqlite', 'sqlite3'],
        help="Supported formats: .db, .sqlite, .sqlite3",
        key="file_uploader"
    )
    
    # Show active database info
    if "file_id" in st.session_state and st.session_state.file_id:
        st.markdown(f"""
        <div class="info-box">
            <strong>Active Database:</strong> {st.session_state.get('last_uploaded_file', '')}
        </div>
        """, unsafe_allow_html=True)
    
    # =============================================================================
    # Question Input Section
    # =============================================================================
    st.markdown('<p class="section-title">Ask Your Question</p>', unsafe_allow_html=True)
    
    question = st.text_area(
        "Enter your question:",
        placeholder="What would you like to know about your database?",
        height=100,
        key="question_input"
    )
    
    return uploaded_file, question






