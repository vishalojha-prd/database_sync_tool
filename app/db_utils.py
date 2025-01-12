import pymysql
from decouple import config

# Database Configuration
DB_HOST="nct.c3q46o4qc42z.ap-south-1.rds.amazonaws.com"               # Hostname or IP of your MySQL server
DB_USER="admin"                    # MySQL username
DB_PASSWORD="oogabooga"       # MySQL password


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
    """Fetch schema details for tables, columns, and datatypes."""
    connection = connect_to_db(db_name)
    cursor = connection.cursor()

    # Fetch tables, columns, and data types
    cursor.execute("""
        SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE
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
    for table, column, dtype in master_schema:
        if table not in master_tables:
            master_tables[table] = {}
        master_tables[table][column] = dtype

    client_tables = {}
    for table, column, dtype in client_schema:
        if table not in client_tables:
            client_tables[table] = {}
        client_tables[table][column] = dtype

    # Identify table, column, and datatype mismatches
    missing_tables = set(master_tables.keys()) - set(client_tables.keys())
    missing_columns = {}
    datatype_mismatches = {}
    for table, columns in master_tables.items():
        if table in client_tables:
            # Check for missing columns
            missing = set(columns.keys()) - set(client_tables[table].keys())
            if missing:
                missing_columns[table] = list(missing)

            # Check for datatype mismatches
            mismatches = {
                col: {"master": columns[col], "client": client_tables[table][col]}
                for col in columns
                if col in client_tables[table] and columns[col] != client_tables[table][col]
            }
            if mismatches:
                datatype_mismatches[table] = mismatches

    # Identify missing foreign keys
    missing_fks = [
        fk for fk in master_fks if fk not in client_fks
    ]

    # Identify missing or modified stored procedures
    missing_procs = [
        proc for proc in master_procs if proc not in client_procs
    ]

    return {
        "missing_tables": list(missing_tables),
        "missing_columns": missing_columns,
        "datatype_mismatches": datatype_mismatches,
        "missing_foreign_keys": missing_fks,
        "missing_stored_procedures": missing_procs
    }
def fetch_schemas_with_prefix(prefix="client_"):
    """Fetch all schemas with a given prefix."""
    print("Prefix:", prefix); 
    connection = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        port=3306
    )
    cursor = connection.cursor()

    # Query to fetch schemas with the given prefix
    cursor.execute(
        "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME LIKE %s",
        (f"{prefix}%",)
    )
    schemas = [row[0] for row in cursor.fetchall()]
    connection.close()
    return schemas

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
    for table in master_tables & client_tables:
        cursor_master.execute(f"DESCRIBE {table}")
        master_columns = {col[0]: col for col in cursor_master.fetchall()}

        cursor_client.execute(f"DESCRIBE {table}")
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

            # Debug missing or invalid values
            cursor_client.execute(f"""
                SELECT {column}
                FROM {table}
                WHERE {column} NOT IN (
                    SELECT {ref_column}
                    FROM {ref_table}
                ) OR {column} IS NULL;
            """)
            missing_values = cursor_client.fetchall()
            print(f"Missing or invalid values for {column} in {table}: {missing_values}")

            # Insert missing values into the referenced table
            for missing_value in missing_values:
                missing_id = missing_value[0]
                if missing_id is None:
                    print(f"Skipping NULL value for {column} in {table}")
                    continue
                try:
                    # Check if the value already exists before inserting
                    cursor_client.execute(f"""
                        SELECT COUNT(*)
                        FROM {ref_table}
                        WHERE {ref_column} = {missing_id};
                    """)
                    exists = cursor_client.fetchone()[0]

                    if exists == 0:
                        # Adapt INSERT to actual schema
                        insert_sql = f"""
                            INSERT INTO {ref_table} ({ref_column})
                            VALUES ({missing_id});
                        """
                        cursor_client.execute(insert_sql)
                        connection_client.commit()
                        print(f"Inserted missing value {missing_id} into {ref_table}")
                    else:
                        print(f"Value {missing_id} already exists in {ref_table}")
                except Exception as insert_error:
                    print(f"Failed to insert missing value {missing_id} into {ref_table}: {insert_error}")

    # Commit and close connections
    connection_client.commit()
    connection_master.close()
    connection_client.close()

    return {
        "tables_updated": list(missing_tables),
        "columns_added": columns_added,
        "datatype_mismatches": datatype_mismatches,
        "foreign_keys_added": [fk[2] for fk in missing_fks]
    }
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
    for table in master_tables & client_tables:
        cursor_master.execute(f"DESCRIBE {table}")
        master_columns = {col[0]: col for col in cursor_master.fetchall()}

        cursor_client.execute(f"DESCRIBE {table}")
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

            # Debug missing or invalid values
            cursor_client.execute(f"""
                SELECT {column}
                FROM {table}
                WHERE {column} NOT IN (
                    SELECT {ref_column}
                    FROM {ref_table}
                ) OR {column} IS NULL;
            """)
            missing_values = cursor_client.fetchall()
            print(f"Missing or invalid values for {column} in {table}: {missing_values}")

            # Insert missing values into the referenced table
            for missing_value in missing_values:
                missing_id = missing_value[0]
                try:
                    # Check if the value already exists before inserting
                    cursor_client.execute(f"""
                        SELECT COUNT(*)
                        FROM {ref_table}
                        WHERE {ref_column} = {missing_id};
                    """)
                    exists = cursor_client.fetchone()[0]

                    if exists == 0:
                        # Replace with actual schema for `ref_table`
                        insert_sql = f"""
                            INSERT INTO {ref_table} ({ref_column}, COMPANY_NAME)
                            VALUES ({missing_id}, 'Default Company Name');
                        """
                        cursor_client.execute(insert_sql)
                        connection_client.commit()
                        print(f"Inserted missing value {missing_id} into {ref_table}")
                    else:
                        print(f"Value {missing_id} already exists in {ref_table}")
                except Exception as insert_error:
                    print(f"Failed to insert missing value {missing_id} into {ref_table}: {insert_error}")

    # Commit and close connections
    connection_client.commit()
    connection_master.close()
    connection_client.close()

    return {
        "tables_updated": list(missing_tables),
        "columns_added": columns_added,
        "datatype_mismatches": datatype_mismatches,
        "foreign_keys_added": [fk[2] for fk in missing_fks]
    }
