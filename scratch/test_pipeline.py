import os
import sys
import shutil

# Add parent directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from services import pdf_service, vector_store, report_service

def generate_mock_pdf(path: str):
    """
    Helper to generate a multi-page PDF contract for testing.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    doc = SimpleDocTemplate(path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Page 1
    story.append(Paragraph("<b>CONFIDENTIAL SERVICES AGREEMENT</b>", styles['Title']))
    story.append(Spacer(1, 20))
    story.append(Paragraph(
        "This Agreement is entered into on this 4th day of July, 2026, by and between "
        "Client Corp ('Client') and Provider LLC ('Provider').",
        styles['Normal']
    ))
    story.append(Spacer(1, 200)) # push text to next pages
    
    # Page 2
    story.append(Paragraph("<b>1. SCOPE OF SERVICES</b>", styles['Heading2']))
    story.append(Paragraph(
        "Provider shall perform software engineering services. Client shall pay Provider "
        "within 30 days of receiving invoices. Late payments shall accrue interest of 1.5% per month.",
        styles['Normal']
    ))
    story.append(Spacer(1, 200))
    
    # Page 3
    story.append(Paragraph("<b>2. INDEMNIFICATION & LIABILITY</b>", styles['Heading2']))
    story.append(Paragraph(
        "Client agrees to indemnify, defend, and hold harmless Provider from any and all claims, "
        "liabilities, losses, damages, or expenses arising from the performance of services.",
        styles['Normal']
    ))
    story.append(Paragraph(
        "Provider's total liability under this agreement is capped at $1,000,000,000 (One Billion Dollars).",
        styles['Normal']
    ))
    story.append(Spacer(1, 200))
    
    # Page 4
    story.append(Paragraph("<b>3. TERMINATION</b>", styles['Heading2']))
    story.append(Paragraph(
        "Either party may terminate this agreement at any time for convenience with 5 days prior written notice. "
        "Upon termination, Client shall pay Provider for all services rendered up to the date of termination.",
        styles['Normal']
    ))
    
    doc.build(story)
    print(f"[OK] Created test PDF contract at: {path}")

def run_test_pipeline():
    test_pdf = os.path.join("scratch", "test_contract.pdf")
    test_report = os.path.join("reports", "Test_Analysis_Report.pdf")
    
    # Ensure clean state
    if os.path.exists("vector_store/test_contract_id"):
        shutil.rmtree("vector_store/test_contract_id")
        
    print("[*] Starting Local Pipeline Verification...")
    
    # 1. Create a dummy contract PDF
    generate_mock_pdf(test_pdf)
    
    # 2. Extract text page by page
    print("[*] Testing PDF Extraction...")
    pages = pdf_service.extract_text_by_page(test_pdf)
    print(f"[OK] Extracted {len(pages)} pages successfully.")
    for p in pages:
        print(f"  - Page {p['page_num']}: {len(p['text'])} chars")
        
    # Get metadata
    meta = pdf_service.get_pdf_metadata(test_pdf)
    print(f"[OK] PDF Metadata: {meta}")
    
    # 3. Build FAISS vector store
    print("[*] Testing Vector Store Building...")
    vector_store.build_vector_store(
        contract_id="test_contract_id",
        pages_content=pages,
        base_dir="vector_store"
    )
    print("[OK] Vector index and metadata saved successfully.")
    
    # 4. Query vector store
    print("[*] Testing similarity search query...")
    query = "liability limitation or indemnification clause"
    results = vector_store.query_vector_store(
        contract_id="test_contract_id",
        query=query,
        k=2,
        base_dir="vector_store"
    )
    print(f"[OK] Query results for: '{query}':")
    for r in results:
        print(f"  - Page {r['page_num']} (Score: {r['distance']:.4f}):")
        print(f"    Text: {r['text'][:120]}...")
        
    # 5. Generate mock report
    print("[*] Testing ReportLab report generation...")
    mock_analysis = {
        "summary": "This is a mock contract evaluation summary testing ReportLab and matplotlib functionality.",
        "risk_score": 65,
        "key_clauses": [
            {
                "name": "Payment Terms",
                "description": "Client pays within 30 days of receiving invoices.",
                "interpretation": "Standard 30-day payment cycle.",
                "page": 2
            },
            {
                "name": "Termination",
                "description": "Allows termination for convenience with 5 days written notice.",
                "interpretation": "Highly flexible termination policy, potentially causing project instability.",
                "page": 4
            }
        ],
        "risky_clauses": [
            {
                "name": "Uncapped Indemnification",
                "risk_level": "High",
                "confidence": 92,
                "description": "Client indemnifies Provider for all expenses without a reasonable cap.",
                "recommendation": "Negotiate a reciprocal indemnification clause capped at fees paid.",
                "page": 3
            },
            {
                "name": "Extremely Short Notice",
                "risk_level": "Medium",
                "confidence": 85,
                "description": "Termination for convenience requires only a 5-day notice.",
                "recommendation": "Increase notice period to 30 days.",
                "page": 4
            }
        ]
    }
    
    report_service.generate_pdf_report(
        contract_id="test_contract_id",
        filename="test_contract.pdf",
        analysis=mock_analysis,
        output_path=test_report
    )
    print(f"[OK] ReportLab PDF generation verified! Output is at: {test_report}")
    print("\n[SUCCESS] ALL LOCAL COMPONENTS VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    run_test_pipeline()
