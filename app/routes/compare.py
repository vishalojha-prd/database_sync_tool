from fastapi import APIRouter, Query, Body

from app.db_utils import fetch_schemas_with_prefix, compare_schemas,fetch_tables_in_database, copy_table_data
from fastapi import HTTPException

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

# New Route: Fetch all available databases
@router.get("/databases")
def get_databases():
    """Fetch all available databases."""
    try:
        databases = fetch_schemas_with_prefix("")  # Fetch all databases without prefix filtering
        return {"status": "success", "data": databases}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch databases: {str(e)}")


# New Route: Fetch tables for a specific database
@router.get("/tables")
def get_tables(database_name: str = Query(...)):
    """
    Fetch tables for a specific database.
    """
    print("Database name:", database_name)
    if not database_name:
        raise HTTPException(status_code=400, detail="Database name is required.")

    try:
        tables = fetch_tables_in_database(database_name)
        return {"status": "success", "data": tables}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch tables for database '{database_name}': {str(e)}")


# New Route: Copy data from one table to another
@router.post("/copy")
def copy_data(
    source_db: str = Body(...),
    source_table: str = Body(...),
    destination_db: str = Body(...),
    destination_table: str = Body(...),
    delete_existing: bool = Body(False),
):        
    print("Copying data...1111",source_db, source_table, destination_db, destination_table, delete_existing)

    result = copy_table_data(
            source_table=source_table,
            target_table=destination_table,
            source_db=source_db,
            destination_db=destination_db,
            delete_existing=delete_existing
        )
    """
    Copy data from one table to another.
    """
    # if not all([source_db, source_table, destination_db, destination_table]):
    #     raise HTTPException(status_code=400, detail="Source and destination database/table are required.")

    # try:
        
    #     return {"status": "success", "message": result}
    # except Exception as e:
    #     raise HTTPException(status_code=500, detail=f"Failed to copy data: {str(e)}")

