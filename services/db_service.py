import json
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from backend.database import Contract

def create_contract(db: Session, contract_id: str, filename: str, filepath: str) -> Contract:
    """
    Creates a new contract record in the database.
    """
    db_contract = Contract(
        id=contract_id,
        filename=filename,
        filepath=filepath,
        analysis_json=None
    )
    db.add(db_contract)
    db.commit()
    db.refresh(db_contract)
    return db_contract

def update_contract_analysis(db: Session, contract_id: str, analysis_data: Dict[str, Any]) -> Contract:
    """
    Updates the analysis result for a given contract.
    """
    db_contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not db_contract:
        raise ValueError(f"Contract with ID {contract_id} not found in database.")
        
    db_contract.analysis_json = json.dumps(analysis_data, ensure_ascii=False)
    db.commit()
    db.refresh(db_contract)
    return db_contract

def get_contract(db: Session, contract_id: str) -> Optional[Contract]:
    """
    Retrieves a single contract by ID.
    """
    return db.query(Contract).filter(Contract.id == contract_id).first()

def get_contract_analysis(db: Session, contract_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves and parses the contract analysis JSON.
    """
    db_contract = get_contract(db, contract_id)
    if db_contract and db_contract.analysis_json:
        return json.loads(db_contract.analysis_json)
    return None

def list_contracts(db: Session) -> List[Contract]:
    """
    Lists all analyzed contracts ordered by creation date descending.
    """
    return db.query(Contract).order_by(Contract.created_at.desc()).all()

def delete_contract(db: Session, contract_id: str) -> bool:
    """
    Deletes a contract record.
    """
    db_contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if db_contract:
        db.delete(db_contract)
        db.commit()
        return True
    return False
