from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Import update_client_database if it's defined elsewhere
from db_utils import update_client_database
from db_utils import fetch_schemas_with_prefix

router = APIRouter()

class UpdateRequest(BaseModel):
    client_db: str = None
    apply_to_all: bool = False

@router.post("/update")
def update(request: UpdateRequest):
    """
    Update client database(s) to match the master schema.
    """
    client_db = request.client_db
    apply_to_all = request.apply_to_all
    
    print("Request payload:", {"client_db": client_db, "apply_to_all": apply_to_all})
    
    if apply_to_all:
        # Fetch all client databases
        client_databases = fetch_schemas_with_prefix("client_")
        if not client_databases:
            raise HTTPException(status_code=404, detail="No client databases found.")
        
        results = {db: update_client_database(db) for db in client_databases}
        return {"status": "success", "message": "Updates applied to all clients.", "results": results}
    
    elif client_db:
        # Update a specific client database
        result = update_client_database(client_db)
        return {"status": "success", "message": f"Updates applied to {client_db}.", "result": result}
    
    else:
        raise HTTPException(status_code=400, detail="Invalid request. Provide a client database or set apply_to_all=True.")
