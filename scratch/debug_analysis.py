import os
import sys
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal, Contract
from services import pdf_service, vector_store, llm_service

def debug_analysis(contract_id: str):
    db = SessionLocal()
    try:
        db_contract = db.query(Contract).filter(Contract.id == contract_id).first()
        if not db_contract:
            print(f"[ERROR] Contract {contract_id} not found in database.")
            return
            
        print(f"[*] Found contract in DB: {db_contract.filename}")
        print(f"[*] Path: {db_contract.filepath}")
        
        # 1. Extract text
        print("[*] Extracting text...")
        pages_content = pdf_service.extract_text_by_page(db_contract.filepath)
        print(f"[OK] Extracted {len(pages_content)} pages.")
        
        # 2. Build vector store
        print("[*] Building vector store...")
        vector_store.build_vector_store(contract_id, pages_content)
        print("[OK] Vector store built.")
        
        # 3. Format full text
        full_text_with_pages = ""
        for page in pages_content:
            full_text_with_pages += f"\n--- PAGE {page['page_num']} ---\n{page['text']}\n"
            
        # 4. Call Gemini
        print("[*] Calling Gemini API for analysis...")
        api_key = os.getenv("GEMINI_API_KEY")
        print(f"[*] Using API Key (truncated): {api_key[:8] if api_key else 'None'}...")
        
        analysis_result = llm_service.analyze_contract_text(
            contract_text=full_text_with_pages,
            api_key=api_key
        )
        print("[OK] Analysis succeeded! Output:")
        print(json.dumps(analysis_result, indent=2))
        
    except Exception as e:
        print("[ERROR] Exception occurred during analysis:")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    # We can pass the contract ID as an argument or let it search the database for the last uploaded contract
    contract_id = "60b5e6bb-ccdb-4d8f-9d92-cf329e19e0b4"
    if len(sys.argv) > 1:
        contract_id = sys.argv[1]
    else:
        db = SessionLocal()
        last_contract = db.query(Contract).order_by(Contract.created_at.desc()).first()
        if last_contract:
            contract_id = last_contract.id
        db.close()
        
    if contract_id:
        debug_analysis(contract_id)
    else:
        print("[ERROR] No contracts found in the database.")
