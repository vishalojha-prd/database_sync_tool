from fastapi import APIRouter, Query
from app.db_utils import fetch_schemas_with_prefix, compare_schemas

router = APIRouter()

@router.get("/clients")
def get_clients():
    """Fetch all client databases prefixed with 'client_'."""
    client_schemas = fetch_schemas_with_prefix("client_")
    return {"status": "success", "data": client_schemas}


@router.get("/compare")
def compare(client_db: str = Query(...)):
    """
    Compare the client database with the master database (nct).
    """
    differences = compare_schemas(master_db="nct", client_db=client_db)
    return {"status": "success", "data": differences}
