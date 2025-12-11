import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from fpdf import FPDF
import io
import pandas as pd
from datetime import datetime

# Page config
st.set_page_config(page_title="AI Chatbot with PDF", page_icon="🤖", layout="wide")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""
if "data_context" not in st.session_state:
    st.session_state.data_context = ""
if "request_count" not in st.session_state:
    st.session_state.request_count = 0

# Configure API Key from Streamlit Secrets
# Configure API Key with better error handling
api_configured = False
try:
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
        api_configured = True
    else:
        st.error("⚠️ API Key not found in secrets. Please configure GEMINI_API_KEY in Streamlit Cloud.")
        st.info("💡 Go to your app settings → Secrets → Add: GEMINI_API_KEY = \"your-api-key\"")
        st.stop()
except Exception as e:
    st.error(f"⚠️ Error configuring API: {str(e)}")
    st.info("💡 Please check your Streamlit secrets configuration.")
    st.stop()

# Sidebar
with st.sidebar:
    st.title("⚙️ AI Chatbot")
    st.caption("Analyze documents and generate reports")
    
    # Usage indicator
    st.info(f"💬 Messages this session: {st.session_state.request_count}")
    
    st.divider()
    
    # File upload section
    st.subheader("📄 Upload Files")
    
    # PDF Upload
    uploaded_pdf = st.file_uploader("Upload PDF", type=["pdf"])
    if uploaded_pdf:
        try:
            pdf_reader = PdfReader(uploaded_pdf)
            pdf_text = ""
            for page in pdf_reader.pages:
                pdf_text += page.extract_text()
            st.session_state.pdf_text = pdf_text
            st.success(f"✅ PDF loaded ({len(pdf_text)} characters)")
            with st.expander("Preview PDF Content"):
                st.text_area("Content", pdf_text[:500] + "...", height=150, disabled=True)
        except Exception as e:
            st.error(f"Error reading PDF: {e}")
    
    # CSV Upload
    uploaded_csv = st.file_uploader("Upload CSV/Excel", type=["csv", "xlsx"])
    if uploaded_csv:
        try:
            if uploaded_csv.name.endswith('.csv'):
                df = pd.read_csv(uploaded_csv)
            else:
                df = pd.read_excel(uploaded_csv)
            
            st.session_state.data_context = df.to_string()
            st.success(f"✅ Data loaded ({df.shape[0]} rows, {df.shape[1]} columns)")
            with st.expander("Preview Data"):
                st.dataframe(df.head())
        except Exception as e:
            st.error(f"Error reading file: {e}")
    
    st.divider()
    
    # Clear chat button
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.session_state.request_count = 0
        st.rerun()
    
    # Remove uploaded files button
    if st.button("❌ Remove Files"):
        st.session_state.pdf_text = ""
        st.session_state.data_context = ""
        st.rerun()

# Main chat interface
st.title("🤖 AI Document Chatbot")
st.caption("Upload PDFs or data files, ask questions, and generate reports!")

# Show current context
if st.session_state.pdf_text or st.session_state.data_context:
    with st.expander("📋 Active Context"):
        if st.session_state.pdf_text:
            st.write("✓ PDF document loaded")
        if st.session_state.data_context:
            st.write("✓ Data file loaded")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask me anything about your data..."):
    
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Prepare context
    context = ""
    if st.session_state.pdf_text:
        context += f"\n\nPDF Content:\n{st.session_state.pdf_text[:8000]}\n"
    if st.session_state.data_context:
        context += f"\n\nData:\n{st.session_state.data_context[:8000]}\n"
    
    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # Build full prompt with context
                full_prompt = prompt
                if context:
                    full_prompt = f"Context information:\n{context}\n\nUser question: {prompt}"
                
                response = model.generate_content(full_prompt)
                assistant_response = response.text
                
                # Increment request count
                st.session_state.request_count += 1
                
                st.markdown(assistant_response)
                
                # Check if user wants a PDF
                if any(keyword in prompt.lower() for keyword in ["generate pdf", "create pdf", "make pdf", "pdf report", "download report"]):
                    st.divider()
                    st.subheader("📄 Generate PDF Report")
                    
                    # Create PDF
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", size=12)
                    
                    # Add title
                    pdf.set_font("Arial", 'B', 16)
                    pdf.cell(0, 10, "AI Generated Report", ln=True, align='C')
                    pdf.ln(5)
                    
                    # Add timestamp
                    pdf.set_font("Arial", 'I', 10)
                    pdf.cell(0, 10, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
                    pdf.ln(10)
                    
                    # Add content
                    pdf.set_font("Arial", size=11)
                    # Clean and encode the text
                    clean_text = assistant_response.encode('latin-1', 'replace').decode('latin-1')
                    pdf.multi_cell(0, 10, clean_text)
                    
                    # Generate PDF bytes
                    pdf_output = pdf.output(dest='S').encode('latin-1')
                    
                    # Download button
                    st.download_button(
                        label="⬇️ Download PDF Report",
                        data=pdf_output,
                        file_name=f"ai_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                
                # Add to chat history
                st.session_state.messages.append({"role": "assistant", "content": assistant_response})
                
            except Exception as e:
                error_msg = str(e)
                if "quota" in error_msg.lower() or "limit" in error_msg.lower():
                    st.error("⚠️ Daily usage limit reached. Please try again later or contact support.")
                else:
                    st.error(f"Error: {error_msg}")
                st.info("💡 If you continue experiencing issues, please refresh the page or contact support.")

# Footer
st.divider()
col1, col2, col3 = st.columns(3)
with col1:
    st.caption("🤖 Powered by Google Gemini")
with col2:
    st.caption("📊 Upload PDFs, CSV, Excel")
with col3:
    st.caption("📝 Generate PDF Reports")