import os
import streamlit as st
import requests
import json
import matplotlib.pyplot as plt
from typing import Dict, Any, List

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="AI Contract Analyzer",
    page_icon="📜",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# API Configurations
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

def load_css(file_name: str):
    """Loads and injects custom CSS for modern theme styling."""
    if os.path.exists(file_name):
        with open(file_name, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Inject modern styling
load_css("frontend/style.css")

# Initialize Session State Variables
if "contract_id" not in st.session_state:
    st.session_state.contract_id = None
if "filename" not in st.session_state:
    st.session_state.filename = None
if "metadata" not in st.session_state:
    st.session_state.metadata = None
if "analysis" not in st.session_state:
    st.session_state.analysis = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "api_key" not in st.session_state:
    st.session_state.api_key = os.getenv("GEMINI_API_KEY", "")

# --- UI HEADER ---
st.markdown(
    """
    <div class="header-container">
        <h1 class="header-title">📜 AI Contract Analyzer</h1>
        <p class="header-subtitle">Professional legal risk assessment and interactive clause exploration</p>
    </div>
    """,
    unsafe_allow_html=True
)

# --- CONFIGURATION (API KEY FALLBACK) ---
env_key = os.getenv("GEMINI_API_KEY", "").strip()
if not env_key:
    with st.expander("🔑 Gemini API Key Configuration", expanded=st.session_state.api_key == ""):
        api_key_input = st.text_input(
            "Enter your Gemini API Key:",
            type="password",
            value=st.session_state.api_key,
            help="Your API key is used directly to call Gemini 2.5 and is not stored on the server."
        )
        if api_key_input:
            st.session_state.api_key = api_key_input
            st.success("API Key updated for this session!")
else:
    # Clear the session state variable if environment key exists to avoid conflicts
    st.session_state.api_key = env_key

# Prepare request headers
headers = {}
if st.session_state.api_key:
    headers["x-gemini-api-key"] = st.session_state.api_key

# --- UPLOAD SECTION ---
st.markdown("### 1. Upload Contract")
uploaded_file = st.file_uploader(
    "Choose a PDF file to analyze",
    type=["pdf"],
    label_visibility="collapsed"
)

# Handle file upload change
if uploaded_file is not None and st.session_state.filename != uploaded_file.name:
    with st.spinner("Uploading and parsing contract..."):
        try:
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
            response = requests.post(f"{BACKEND_URL}/api/upload", files=files)
            
            if response.status_code == 200:
                data = response.json()
                st.session_state.contract_id = data["contract_id"]
                st.session_state.filename = data["filename"]
                st.session_state.metadata = data
                st.session_state.analysis = None # Reset previous analysis
                st.session_state.chat_history = [] # Reset chat
                st.success("File uploaded successfully!")
            else:
                err_detail = response.json().get("detail", "Unknown server error.")
                st.error(f"Upload failed: {err_detail}")
        except Exception as e:
            st.error(f"Failed to connect to backend service: {str(e)}")

# Display uploaded file details
if st.session_state.contract_id:
    meta = st.session_state.metadata
    st.markdown(
        f"""
        <div class="file-uploaded-alert">
            <span>✓ <b>File Uploaded:</b> {st.session_state.filename} ({meta['pages']} Pages • {meta['size_kb']} KB)</span>
            <span>ID: {st.session_state.contract_id[:8]}...</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    # --- ANALYSIS INITIATION ---
    st.markdown("<br/>", unsafe_allow_html=True)
    
    # Check if we need to show the Analyze button
    if st.session_state.analysis is None:
        col1, col2 = st.columns([1, 4])
        with col1:
            analyze_clicked = st.button("🔍 Analyze Contract", use_container_width=True)
        with col2:
            st.markdown(
                "<span style='color: #6b7280; font-size: 0.9rem; line-height: 2.2;'>Takes about 15-30 seconds to extract text, build embeddings, and complete risk audit.</span>",
                unsafe_allow_html=True
            )
            
        if analyze_clicked:
            # Check key exists
            if not st.session_state.api_key:
                st.warning("Please configure your Gemini API Key first.")
            else:
                with st.spinner("Analyzing contract text... Embedding and auditing risk levels..."):
                    try:
                        response = requests.post(
                            f"{BACKEND_URL}/api/analyze/{st.session_state.contract_id}",
                            headers=headers
                        )
                        
                        if response.status_code == 200:
                            st.session_state.analysis = response.json()
                            st.rerun()
                        else:
                            err_detail = response.json().get("detail", "Unknown server error.")
                            st.error(f"Analysis failed: {err_detail}")
                    except Exception as e:
                        st.error(f"Failed to perform analysis: {str(e)}")

# --- ANALYSIS DASHBOARD ---
if st.session_state.contract_id and st.session_state.analysis:
    analysis = st.session_state.analysis
    meta = st.session_state.metadata
    
    # Extract analysis duration
    analysis_time_val = analysis.get("analysis_time", "N/A")
    analysis_time_str = f"{analysis_time_val} seconds" if isinstance(analysis_time_val, (int, float)) else "N/A"
    
    # 1. Document Information Card & Results Header
    st.markdown("<br/>", unsafe_allow_html=True)
    st.markdown("### 2. Analysis Results")
    
    import datetime
    st.markdown(
        f"""
        <div class="detail-card" style="background-color: #f5f3ff; border: 1px solid #ddd6fe; margin-bottom: 1.5rem;">
            <div style="font-weight: 700; color: #4f46e5; font-size: 1.05rem; margin-bottom: 0.75rem; display: flex; align-items: center; gap: 0.5rem;">
                📁 Document Information
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1.25rem; font-size: 0.9rem; color: #1f2937;">
                <div><b>File Name:</b><br/><span style="color: #4b5563;">{st.session_state.filename}</span></div>
                <div><b>Total Pages:</b><br/><span style="color: #4b5563;">{meta['pages']} Pages</span></div>
                <div><b>File Size:</b><br/><span style="color: #4b5563;">{meta['size_kb']} KB</span></div>
                <div><b>Upload Date:</b><br/><span style="color: #4b5563;">{datetime.datetime.now().strftime("%Y-%m-%d")}</span></div>
                <div><b>Analysis Duration:</b><br/><span style="color: #4b5563;">{analysis_time_str}</span></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.markdown(
        f"""
        <div class="quick-summary-box">
            <h5 style="color: #4f46e5; margin-top: 0;">Quick Summary</h5>
            <p style="color: #4b5563; font-size: 0.95rem; margin: 0; line-height: 1.5;">
                {analysis['summary']}
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # 2. Metric Row Card Setup
    risk_score = analysis["risk_score"]
    key_clauses_count = len(analysis["key_clauses"])
    risks_count = len(analysis["risky_clauses"])
    pages_count = meta["pages"]
    
    # Classify color for risk score
    risk_class = "metric-risk-low"
    risk_label = "Low"
    risk_color = "#10b981" # Green
    risk_icon = "🟢"
    if risk_score >= 70:
        risk_class = "metric-risk-high"
        risk_label = "High"
        risk_color = "#ef4444" # Red
        risk_icon = "🔴"
    elif risk_score >= 40:
        risk_class = "metric-risk-medium"
        risk_label = "Medium"
        risk_color = "#f59e0b" # Orange
        risk_icon = "🟡"
        
    # Generate text progress bar (e.g., ████████░░ 80%)
    filled_blocks = min(10, max(0, round(risk_score / 10)))
    empty_blocks = 10 - filled_blocks
    bar_str = "█" * filled_blocks + "░" * empty_blocks
        
    st.markdown(
        f"""
        <div class="metric-row">
            <div class="metric-card {risk_class}">
                <div class="metric-title">{risk_icon} OVERALL RISK</div>
                <div style="font-family: monospace; font-size: 1.1rem; color: {risk_color}; font-weight: 700; letter-spacing: 1px; margin-bottom: 2px;">
                    {bar_str} {risk_score}%
                </div>
                <div style="font-size: 0.85rem; color: #4b5563; font-weight: 600;">
                    {risk_label} Risk
                </div>
            </div>
            <div class="metric-card metric-clauses">
                <div class="metric-title">KEY CLAUSES FOUND</div>
                <div class="metric-value-row">
                    <span class="metric-value">{key_clauses_count}</span>
                    <span class="metric-sub">Clauses</span>
                </div>
            </div>
            <div class="metric-card metric-issues">
                <div class="metric-title">ISSUES FOUND</div>
                <div class="metric-value-row">
                    <span class="metric-value">{risks_count}</span>
                    <span class="metric-sub">Risks</span>
                </div>
            </div>
            <div class="metric-card metric-pages">
                <div class="metric-title">DOCUMENT PAGES</div>
                <div class="metric-value-row">
                    <span class="metric-value">{pages_count}</span>
                    <span class="metric-sub">Pages</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # 3. TABS CONTAINER
    tab_summary, tab_clauses, tab_risks, tab_chat = st.tabs([
        "📊 Summary & Overview", 
        "🔑 Key Clauses", 
        "⚠️ Risky Clauses", 
        "💬 Chat with Contract"
    ])
    
    # --- TAB: SUMMARY ---
    with tab_summary:
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown("##### Detailed Risk Distribution")
            
            # Count risks
            high_count = sum(1 for c in analysis["risky_clauses"] if c.get("risk_level", "").lower() == "high")
            med_count = sum(1 for c in analysis["risky_clauses"] if c.get("risk_level", "").lower() == "medium")
            low_count = sum(1 for c in analysis["risky_clauses"] if c.get("risk_level", "").lower() == "low")
            
            levels = ["High Risk", "Medium Risk", "Low Risk"]
            counts = [high_count, med_count, low_count]
            colors = ["#ef4444", "#f59e0b", "#10b981"]
            
            # Draw matplotlib donut
            fig, ax = plt.subplots(figsize=(4, 4))
            
            total_risks = sum(counts)
            if total_risks == 0:
                ax.pie([1], labels=["No Risks"], colors=["#10b981"], startangle=90, pctdistance=0.75)
            else:
                # filter out 0 slices
                filtered = [(l, c, col) for l, c, col in zip(levels, counts, colors) if c > 0]
                lbls = [x[0] for x in filtered]
                sizes = [x[1] for x in filtered]
                clrs = [x[2] for x in filtered]
                
                ax.pie(
                    sizes, 
                    labels=lbls, 
                    colors=clrs, 
                    autopct='%1.0f%%', 
                    startangle=90,
                    pctdistance=0.75,
                    textprops={'color': '#1f2937', 'weight': 'bold', 'size': 9}
                )
                
            centre_circle = plt.Circle((0,0), 0.55, fc='white')
            fig.gca().add_artist(centre_circle)
            ax.axis('equal')
            plt.tight_layout()
            
            st.pyplot(fig)
            
        with col2:
            st.markdown("##### Executive Evaluation Summary")
            st.write(analysis["summary"])
            
            st.markdown("##### Risk Breakdown Counts")
            st.markdown(f"- 🔴 **High Risk Clauses**: {high_count}")
            st.markdown(f"- 🟡 **Medium Risk Clauses**: {med_count}")
            st.markdown(f"- 🟢 **Low Risk/Info Clauses**: {low_count}")
            
    # --- TAB: CLAUSES ---
    with tab_clauses:
        st.markdown("##### Key Agreement Clauses")
        st.markdown("The AI has identified the following primary clauses governing this contract:")
        
        for idx, kc in enumerate(analysis["key_clauses"]):
            page_val = kc.get("page", "N/A")
            page_badge = f"<span class='badge badge-info'>Page {page_val}</span>" if page_val != "N/A" else ""
            
            st.markdown(
                f"""
                <div class="detail-card">
                    <div class="detail-card-title">
                        <span>📄 {kc['name']}</span>
                        {page_badge}
                    </div>
                    <p style="margin-bottom: 0.5rem; color: #1f2937; font-size: 0.95rem;">
                        {kc['description']}
                    </p>
                    <p style="margin-bottom: 0; color: #4f46e5; font-size: 0.95rem; background-color: #f5f3ff; padding: 0.6rem 0.8rem; border-radius: 6px; border-left: 3px solid #818cf8;">
                        <b>Interpretation:</b> <i>{kc['interpretation']}</i>
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
            
    # --- TAB: RISKS ---
    with tab_risks:
        st.markdown("##### Flagged Risks & Mitigations")
        st.markdown("The following clauses have been flagged as unfavorable, carrying potential legal or commercial risk:")
        
        if not analysis["risky_clauses"]:
            st.success("No significant risky clauses were identified in this agreement!")
        else:
            for idx, rc in enumerate(analysis["risky_clauses"]):
                r_level = rc.get("risk_level", "Low").lower()
                badge_class = "badge-low"
                icon = "🟢"
                border_color = "#10b981"
                if r_level == "high":
                    badge_class = "badge-high"
                    icon = "🔴"
                    border_color = "#ef4444"
                elif r_level == "medium":
                    badge_class = "badge-medium"
                    icon = "🟡"
                    border_color = "#f59e0b"
                    
                confidence = rc.get("confidence", "N/A")
                conf_str = f" • Confidence {confidence}%" if confidence != "N/A" else ""
                page_val = rc.get("page", "N/A")
                page_str = f"Page {page_val}" if page_val != "N/A" else "N/A"
                
                st.markdown(
                    f"""
                    <div class="detail-card" style="border-left: 5px solid {border_color};">
                        <div class="detail-card-title">
                            <span>{icon} {rc['name']}</span>
                            <div>
                                <span class="badge {badge_class}">{r_level.upper()} RISK</span>
                                <span class="badge badge-info">{page_str}</span>
                            </div>
                        </div>
                        <div style="margin-top: 0.75rem; font-size: 0.95rem;">
                            <p style="margin-bottom: 0.5rem; color: #1f2937;">
                                <b>Risk:</b><br/>{rc['description']}
                            </p>
                            <p style="margin-bottom: 0.5rem; color: #4f46e5; background-color: #f5f3ff; padding: 0.6rem 0.8rem; border-radius: 6px; border-left: 3px solid #818cf8;">
                                <b>Recommendation:</b><br/><i>{rc['recommendation']}</i>
                            </p>
                            <p style="margin-bottom: 0; color: #6b7280; font-size: 0.85rem; font-weight: 500;">
                                <b>Confidence:</b> {confidence}%
                            </p>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
    # --- TAB: CHAT ---
    with tab_chat:
        st.markdown("##### Ask Questions About This Contract")
        st.markdown("Ask specific questions (e.g. *'What are the late fees?'*, *'How can either party terminate the agreement?'*) and the AI will scan the FAISS index to answer based on exact contract source text.")
        
        # Display chat logs
        for chat_idx, msg in enumerate(st.session_state.chat_history):
            role = msg["role"]
            content = msg["content"]
            
            if role == "user":
                st.markdown(
                    f"""
                    <div class="chat-message message-user">
                        <b>You:</b> {content}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"""
                    <div class="chat-message message-bot">
                        <b>AI Assistant:</b> {content}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                # Expand context sources if present
                if "context" in msg and msg["context"]:
                    with st.expander("🔍 View Context Sources"):
                        for c_idx, ctx in enumerate(msg["context"]):
                            st.markdown(
                                f"""
                                <div style="background-color: #f3f4f6; border-left: 3px solid #6b7280; padding: 0.5rem; margin-bottom: 0.5rem; font-size: 0.85rem;">
                                    <b>Source {c_idx+1} (Page {ctx['page_num']}):</b><br/>
                                    {ctx['text']}
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                            
        # Chat input field
        chat_query = st.chat_input("Ask a question about the contract...")
        
        if chat_query:
            # Add user query to history
            st.session_state.chat_history.append({"role": "user", "content": chat_query})
            
            # Request backend for chat
            with st.spinner("Searching vector index and drafting response..."):
                try:
                    payload = {"question": chat_query}
                    chat_response = requests.post(
                        f"{BACKEND_URL}/api/chat/{st.session_state.contract_id}",
                        json=payload,
                        headers=headers
                    )
                    
                    if chat_response.status_code == 200:
                        ans_data = chat_response.json()
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": ans_data["answer"],
                            "context": ans_data["context"]
                        })
                        st.rerun()
                    else:
                        err_detail = chat_response.json().get("detail", "Unknown server error.")
                        st.error(f"Chat failed: {err_detail}")
                except Exception as e:
                    st.error(f"Failed to submit query: {str(e)}")

    # --- DOWNLOAD REPORT BUTTON ---
    st.markdown("<br/>", unsafe_allow_html=True)
    st.markdown("### 3. Export Audit")
    
    try:
        report_url = f"{BACKEND_URL}/api/report/{st.session_state.contract_id}"
        
        # Download bytes from backend report endpoint
        report_response = requests.get(report_url)
        if report_response.status_code == 200:
            st.download_button(
                label="📥 Download PDF Audit Report",
                data=report_response.content,
                file_name=f"Audit_Report_{st.session_state.filename}",
                mime="application/pdf",
                use_container_width=True
            )
        else:
            st.error("Failed to compile PDF Report from backend.")
    except Exception as e:
        st.error(f"Failed to connect to report download: {str(e)}")

# --- FOOTER & DISCLAIMER ---
st.markdown(
    """
    <div class="disclaimer-box">
        <b>Disclaimer:</b> This AI-generated analysis is for informational purposes only and is not legal advice. 
        Consult a qualified legal professional before making decisions based on this report.
    </div>
    """,
    unsafe_allow_html=True
)
st.markdown("<p style='text-align: center; color: #9ca3af; font-size: 0.8rem; margin-top: 1rem;'>100% Free • One-time secure local audit</p>", unsafe_allow_html=True)
