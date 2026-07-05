import os
import uuid
import shutil
import json
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Header, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

from backend.database import get_db, Contract
from models.schemas import (
    ContractUploadResponse, 
    AnalysisResponse, 
    ChatRequest, 
    ChatResponse
)
from services import (
    pdf_service,
    vector_store,
    llm_service,
    db_service,
    report_service
)

router = APIRouter(prefix="/api")

UPLOAD_DIR = "uploads"
REPORT_DIR = "reports"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

@router.post("/upload", response_model=ContractUploadResponse)
def upload_contract(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Uploads a contract PDF, extracts basic page/size metadata,
    generates a UUID filename, and saves it.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF documents are supported."
        )
        
    contract_id = str(uuid.uuid4())
    filename = f"{contract_id}.pdf"
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    try:
        # Save file to disk
        with open(filepath, "wb") as f:
            shutil.copyfileobj(file.file, f)
            
        # Get PDF metadata
        metadata = pdf_service.get_pdf_metadata(filepath)
        
        # Save record in database
        db_service.create_contract(
            db=db,
            contract_id=contract_id,
            filename=file.filename,
            filepath=filepath
        )
        
        return ContractUploadResponse(
            contract_id=contract_id,
            filename=file.filename,
            pages=metadata["pages"],
            size_kb=metadata["size_kb"]
        )
    except Exception as e:
        # Cleanup file if saved
        if os.path.exists(filepath):
            os.remove(filepath)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )

@router.post("/analyze/{contract_id}", response_model=AnalysisResponse)
def analyze_contract(
    contract_id: str, 
    db: Session = Depends(get_db),
    x_gemini_api_key: Optional[str] = Header(None)
):
    """
    Extracts text page-by-page, chunks/embeds and saves FAISS index,
    sends document to Gemini for full audit, and stores analysis in SQLite.
    """
    db_contract = db_service.get_contract(db, contract_id)
    if not db_contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found."
        )
        
    # Check if analysis has already been performed
    if db_contract.analysis_json:
        return json.loads(db_contract.analysis_json)
        
    try:
        import time
        start_time = time.time()
        
        # 1. Extract text page-by-page
        pages_content = pdf_service.extract_text_by_page(db_contract.filepath)
        
        # 2. Build FAISS index and chunk metadata (Only Done Once!)
        vector_store.build_vector_store(contract_id, pages_content)
        
        # 3. Format full text with page indicators for analysis
        full_text_with_pages = ""
        for page in pages_content:
            full_text_with_pages += f"\n--- PAGE {page['page_num']} ---\n{page['text']}\n"
            
        # 4. Call Gemini for analysis
        analysis_result = llm_service.analyze_contract_text(
            contract_text=full_text_with_pages,
            api_key=x_gemini_api_key
        )
        
        # Calculate analysis duration
        analysis_time = round(time.time() - start_time, 2)
        analysis_result["analysis_time"] = analysis_time
        
        # 5. Save analysis to Database
        db_service.update_contract_analysis(db, contract_id, analysis_result)
        
        return analysis_result
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )

@router.post("/chat/{contract_id}", response_model=ChatResponse)
def chat_contract(
    contract_id: str,
    request: ChatRequest,
    db: Session = Depends(get_db),
    x_gemini_api_key: Optional[str] = Header(None)
):
    """
    Queries FAISS index for similar text blocks, answers question via Gemini RAG.
    """
    db_contract = db_service.get_contract(db, contract_id)
    if not db_contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found."
        )
        
    try:
        # Retrieve similar chunks from FAISS
        context_chunks = vector_store.query_vector_store(contract_id, request.question, k=4)
        
        if not context_chunks:
            return ChatResponse(
                answer="No relevant text was found in the contract vector store to answer your query.",
                context=[]
            )
            
        # Call Gemini chat with retrieved context
        answer = llm_service.chat_with_contract(
            question=request.question,
            context_chunks=context_chunks,
            api_key=x_gemini_api_key
        )
        
        return ChatResponse(
            answer=answer,
            context=context_chunks
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contract vector store not found. Please analyze the contract first."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat query failed: {str(e)}"
        )

@router.get("/contracts/{contract_id}", response_model=Dict[str, Any])
def get_contract_status(contract_id: str, db: Session = Depends(get_db)):
    """
    Retrieves the status/metadata and analysis results (if available).
    """
    db_contract = db_service.get_contract(db, contract_id)
    if not db_contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found."
        )
        
    analysis = None
    if db_contract.analysis_json:
        analysis = json.loads(db_contract.analysis_json)
        
    return {
        "id": db_contract.id,
        "filename": db_contract.filename,
        "created_at": db_contract.created_at.isoformat(),
        "analyzed": db_contract.analysis_json is not None,
        "analysis": analysis
    }

@router.get("/report/{contract_id}")
def download_contract_report(contract_id: str, db: Session = Depends(get_db)):
    """
    Generates and returns the PDF analysis report.
    """
    db_contract = db_service.get_contract(db, contract_id)
    if not db_contract or not db_contract.analysis_json:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract analysis not found. Please upload and analyze the contract first."
        )
        
    analysis = json.loads(db_contract.analysis_json)
    
    report_filename = f"Contract_Analysis_{contract_id}.pdf"
    report_filepath = os.path.join(REPORT_DIR, report_filename)
    
    try:
        report_service.generate_pdf_report(
            contract_id=contract_id,
            filename=db_contract.filename,
            analysis=analysis,
            output_path=report_filepath
        )
        
        return FileResponse(
            path=report_filepath,
            filename=f"Analysis_Report_{db_contract.filename}",
            media_type="application/pdf"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report PDF: {str(e)}"
        )
