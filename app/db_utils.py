import pymysql
from decouple import config

# Database Configuration
DB_HOST = "nct.c3q46o4qc42z.ap-south-1.rds.amazonaws.com"  # Hostname or IP of your MySQL server
DB_USER = "admin"  # MySQL username
DB_PASSWORD = "oogabooga"  # MySQL password

print(f"DB_HOST={DB_HOST}, DB_USER={DB_USER}")

def connect_to_db(db_name=None):
    """Establish a connection to the MySQL database."""
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=db_name,
        port=3306
    )

def fetch_schema(db_name):
    """Fetch schema details for tables, columns, datatypes, and default values."""
    connection = connect_to_db(db_name)
    cursor = connection.cursor()

    # Fetch tables, columns, data types, and default values
    cursor.execute("""
        SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, COLUMN_DEFAULT
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s
    """, (db_name,))
    schema = cursor.fetchall()

    connection.close()
    return schema

def fetch_foreign_keys(db_name):
    """Fetch foreign keys for all tables."""
    connection = connect_to_db(db_name)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            TABLE_NAME,
            COLUMN_NAME,
            CONSTRAINT_NAME,
            REFERENCED_TABLE_NAME,
            REFERENCED_COLUMN_NAME
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = %s AND REFERENCED_TABLE_NAME IS NOT NULL
    """, (db_name,))
    foreign_keys = cursor.fetchall()

    connection.close()
    return foreign_keys

def fetch_stored_procedures(db_name):
    """Fetch stored procedures for the given database."""
    connection = connect_to_db(db_name)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT SPECIFIC_NAME, ROUTINE_DEFINITION
        FROM INFORMATION_SCHEMA.ROUTINES
        WHERE ROUTINE_SCHEMA = %s AND ROUTINE_TYPE = 'PROCEDURE'
    """, (db_name,))
    procedures = cursor.fetchall()

    connection.close()
    return procedures

def compare_schemas(master_db="nct", client_db="client_sample"):
    """Compare the schema of the master database with a client database."""
    # Fetch master and client schema
    master_schema = fetch_schema(master_db)
    client_schema = fetch_schema(client_db)

    # Fetch foreign keys
    master_fks = fetch_foreign_keys(master_db)
    client_fks = fetch_foreign_keys(client_db)

    # Fetch stored procedures
    master_procs = fetch_stored_procedures(master_db)
    client_procs = fetch_stored_procedures(client_db)

    # Convert schemas to dictionary format
    master_tables = {}
    for table, column, dtype, default in master_schema:
        if table not in master_tables:
            master_tables[table] = {}
        master_tables[table][column] = {"dtype": dtype, "default": default}

    client_tables = {}
    for table, column, dtype, default in client_schema:
        if table not in client_tables:
            client_tables[table] = {}
        client_tables[table][column] = {"dtype": dtype, "default": default}

    # Identify table, column, datatype, and default value mismatches
    missing_tables = set(master_tables.keys()) - set(client_tables.keys())
    missing_columns = {}
    datatype_mismatches = {}
    default_value_mismatches = {}
    for table, columns in master_tables.items():
        if table in client_tables:
            # Check for missing columns
            missing = set(columns.keys()) - set(client_tables[table].keys())
            if missing:
                missing_columns[table] = list(missing)

            # Check for datatype mismatches
            mismatches = {
                col: {"master": columns[col]["dtype"], "client": client_tables[table][col]["dtype"]}
                for col in columns
                if col in client_tables[table] and columns[col]["dtype"] != client_tables[table][col]["dtype"]
            }
            if mismatches:
                datatype_mismatches[table] = mismatches

            # Check for default value mismatches
            default_mismatches = {
                col: {"master_default": columns[col]["default"], "client_default": client_tables[table][col]["default"]}
                for col in columns
                if col in client_tables[table] and columns[col]["default"] != client_tables[table][col]["default"]
            }
            if default_mismatches:
                default_value_mismatches[table] = default_mismatches

    # Identify missing foreign keys
    missing_fks = [
        fk for fk in master_fks if fk not in client_fks
    ]

    # Identify missing or modified stored procedures
    missing_procs = [
        proc for proc in master_procs if proc not in client_procs
    ]
    print(default_value_mismatches)
    return {
        "missing_tables": list(missing_tables),
        "missing_columns": missing_columns,
        "datatype_mismatches": datatype_mismatches,
        "default_value_mismatches": default_value_mismatches,
        "missing_foreign_keys": missing_fks,
        "missing_stored_procedures": missing_procs
    }

def fetch_schemas_with_prefix(prefix="client_"):
    """Fetch all custom schemas with a given prefix and exclude system schemas."""
    print("Fetching custom schemas with prefix:", prefix)
    connection = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        port=3306
    )
    cursor = connection.cursor()

    try:
        # Query to fetch schemas with the given prefix and exclude system schemas
        cursor.execute("""
            SELECT SCHEMA_NAME 
            FROM INFORMATION_SCHEMA.SCHEMATA 
            WHERE SCHEMA_NAME LIKE %s
            AND SCHEMA_NAME NOT IN ('information_schema', 'mysql', 'performance_schema', 'sys')
        """, (f"{prefix}%",))
        
        schemas = [row[0] for row in cursor.fetchall()]
        return schemas
    except Exception as e:
        print(f"Error fetching schemas: {e}")
        return []
    finally:
        connection.close()

def update_client_database(client_db):
    """Update a specific client database to match the master schema."""
    print("Updating client database...")
    connection_master = connect_to_db("nct")  # Connect to the master database
    connection_client = connect_to_db(client_db)  # Connect to the client database

    cursor_master = connection_master.cursor()
    cursor_client = connection_client.cursor()

    # Fetch tables from both databases
    cursor_master.execute("SHOW TABLES")
    master_tables = {row[0] for row in cursor_master.fetchall()}

    cursor_client.execute("SHOW TABLES")
    client_tables = {row[0] for row in cursor_client.fetchall()}

    # Find and create missing tables
    missing_tables = master_tables - client_tables
    for table in missing_tables:
        cursor_master.execute(f"SHOW CREATE TABLE {table}")
        create_table_sql = cursor_master.fetchone()[1]
        cursor_client.execute(create_table_sql)

    # Compare and update columns for existing tables
    columns_added = []
    datatype_mismatches = []
    default_value_updates = []
    for table in master_tables & client_tables:
        cursor_master.execute(f"""
            SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'nct' AND TABLE_NAME = %s
        """, (table,))
        master_columns = {col[0]: col for col in cursor_master.fetchall()}

        cursor_client.execute(f"""
            SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
        """, (client_db, table))
        client_columns = {col[0]: col for col in cursor_client.fetchall()}

        # Handle missing columns
        missing_columns = set(master_columns.keys()) - set(client_columns.keys())
        for column in missing_columns:
            col_details = master_columns[column]
            add_column_sql = f"ALTER TABLE {table} ADD COLUMN {column} {col_details[1]}"
            cursor_client.execute(add_column_sql)
            columns_added.append(f"{table}.{column}")

        # Handle datatype mismatches
        for column in master_columns.keys() & client_columns.keys():
            master_type = master_columns[column][1]
            client_type = client_columns[column][1]
            if master_type != client_type:
                print(f"Datatype mismatch in {table}.{column}: master={master_type}, client={client_type}")
                datatype_mismatches.append({
                    "table": table,
                    "column": column,
                    "master_type": master_type,
                    "client_type": client_type
                })
                # Alter column to match the master schema
                alter_column_sql = f"ALTER TABLE {table} MODIFY COLUMN {column} {master_type}"
                cursor_client.execute(alter_column_sql)

        # Handle default value mismatches
        for column in master_columns.keys() & client_columns.keys():
            master_default = master_columns[column][2]
            client_default = client_columns[column][2]
            if master_default != client_default:
                print(f"Default value mismatch in {table}.{column}: master_default={master_default}, client_default={client_default}")
                default_value_updates.append({
                    "table": table,
                    "column": column,
                    "master_default": master_default,
                    "client_default": client_default
                })
                # Alter column to update the default value
                alter_default_sql = f"""
                    ALTER TABLE {table} ALTER COLUMN {column} SET DEFAULT {repr(master_default) if master_default is not None else 'NULL'};
                """
                cursor_client.execute(alter_default_sql)

    # Compare and add foreign keys
    cursor_master.execute("""
        SELECT TABLE_NAME, COLUMN_NAME, CONSTRAINT_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = 'nct' AND REFERENCED_TABLE_NAME IS NOT NULL
    """)
    master_fks = cursor_master.fetchall()

    cursor_client.execute("""
        SELECT TABLE_NAME, COLUMN_NAME, CONSTRAINT_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = %s AND REFERENCED_TABLE_NAME IS NOT NULL
    """, (client_db,))
    client_fks = cursor_client.fetchall()

    missing_fks = [fk for fk in master_fks if fk not in client_fks]
    for fk in missing_fks:
        table, column, constraint, ref_table, ref_column = fk
        try:
            add_fk_sql = f"""
                ALTER TABLE {table}
                ADD CONSTRAINT {constraint}
                FOREIGN KEY ({column})
                REFERENCES {ref_table}({ref_column});
            """
            cursor_client.execute(add_fk_sql)
        except pymysql.err.IntegrityError as e:
            print(f"Failed to add foreign key for {table}.{column}: {e}")

    # Commit and close connections
    connection_client.commit()
    connection_master.close()
    connection_client.close()

    return {
        "tables_updated": list(missing_tables),
        "columns_added": columns_added,
        "datatype_mismatches": datatype_mismatches,
        "default_value_updates": default_value_updates,
        "foreign_keys_added": [fk[2] for fk in missing_fks]
    }

def copy_table_data(
    source_table: str,
    target_table: str,
    source_db: str,
    destination_db: str,
    delete_existing: bool = False
):
    """
    Copy data from one table in the source database to another table in the destination database.

    Parameters:
    - source_table: The source table name.
    - target_table: The target table name.
    - source_db: The name of the source database.
    - destination_db: The name of the destination database.
    - delete_existing: Whether to delete existing data in the target table before copying.

    Returns:
    - dict: Result status and message.
    """

    # Connect to both source and destination databases
    source_connection = connect_to_db(source_db)
    destination_connection = connect_to_db(destination_db)

    source_cursor = source_connection.cursor()
    destination_cursor = destination_connection.cursor()

    try:
        # Fetch column names from both tables
        source_cursor.execute(f"SHOW COLUMNS FROM `{source_table}`")
        source_columns = [row[0] for row in source_cursor.fetchall()]

        destination_cursor.execute(f"SHOW COLUMNS FROM `{target_table}`")
        target_columns = [row[0] for row in destination_cursor.fetchall()]

        # Identify common columns between source and target tables
        common_columns = list(set(source_columns) & set(target_columns))

        if not common_columns:
            raise ValueError(f"No matching columns found between `{source_table}` and `{target_table}`.")

        # Prepare the list of columns for the SQL query
        column_list = ", ".join([f"`{col}`" for col in common_columns])

        if delete_existing:
            delete_sql = f"DELETE FROM `{target_table}`"
            destination_cursor.execute(delete_sql)
            destination_connection.commit()
            print(f"Existing data in `{target_table}` has been deleted.")


        # Copy data from source to destination using common columns
        copy_sql = f"""
            INSERT INTO `{target_table}` ({column_list})
            SELECT {column_list}
            FROM `{source_db}`.`{source_table}`;
        """
        print(f"Executing SQL: {copy_sql}")
        destination_cursor.execute(copy_sql)
        destination_connection.commit()

        print(f"Data successfully copied from `{source_db}.{source_table}` to `{destination_db}.{target_table}`.")
        return {"status": "success", "message": f"Data successfully copied from `{source_table}` to `{target_table}`."}

    except Exception as e:
        print(f"Error during data copy: {e}")
        return {"status": "error", "message": str(e)}

    finally:
        # Ensure database connections are closed
        source_connection.close()
        destination_connection.close()
        
def fetch_tables_in_database(db_name):
    """
    Fetch the list of tables for a specific database.
    """
    try:
        print("Hola",db_name)
        connection = connect_to_db(db_name)
        cursor = connection.cursor()

        # Fetch the list of tables
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]

        connection.close()
        return tables
    except pymysql.MySQLError as e:
        print(f"Error fetching tables for database '{db_name}': {e}")
        raise
