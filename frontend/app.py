import streamlit as st
import requests

# Set the app title and favicon
st.set_page_config(
    page_title="NestDBTool",  # Custom App Name
    page_icon="/home/vishal/Downloads/nestbotics.png",  # Replace with the URL of your custom icon
    layout="wide"  # Optional: Use "wide" layout for better spacing
)
BASE_URL = "http://127.0.0.1:8000"

# Apply custom CSS for header, footer, and modal
st.markdown(
    """
    <style>
        /* Hide Streamlit's default header and toolbar */
        header[data-testid="stHeader"] {
            display: none;
        }
        .stAppToolbar {
            display: none;
        }

        /* Custom header */
        .custom-header {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            width: 100%;
            background-color: #452a70;
            color: #ffffff;
            text-align: left;
            padding: 15px 20px;
            font-size: 24px;
            font-weight: bold;
            font-family: 'Roboto', sans-serif;
            z-index: 1000;
            border-bottom: 2px solid #3a235e;
        }

        /* Custom footer */
        .footer {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            width: 100%;
            background-color: #452a70;
            color: #ffffff;
            text-align: center;
            padding: 10px 0;
            font-size: 14px;
            font-family: 'Roboto', sans-serif;
            z-index: 1000;
            border-top: 2px solid #3a235e;
        }

        /* Add padding to prevent content overlap with header and footer */
        .main-content {
            padding-top: 70px;
            padding-bottom: 50px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# Add Custom Header
st.markdown(
    """
    <div class="custom-header">
        Database Sync Tool
    </div>
    """,
    unsafe_allow_html=True,
)

# Add Main Content Wrapper
st.markdown('<div class="main-content">', unsafe_allow_html=True)

# Tab-based navigation
tab1, tab2 = st.tabs(["Sync Tool", "Copy Tool"])

# **TAB 1: Sync Tool**
with tab1:
    st.markdown("### Sync Tool")
    # Fetch the list of client databases
    @st.cache_data
    def fetch_client_databases():
        response = requests.get(f"{BASE_URL}/clients")
        if response.status_code == 200:
            return response.json().get("data", [])
        else:
            st.error("Failed to fetch client databases.")
            return []

    client_databases = fetch_client_databases()

    # Dropdown to select a specific client database
    client_db = st.selectbox("Select Client Database", ["All Clients"] + client_databases)

    # Existing buttons to apply changes
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.button("Apply Changes to Selected Client"):
            st.session_state["modal_action"] = "selected"
            st.write('<script>showModal("selected");</script>', unsafe_allow_html=True)

    with col2:
        if st.button("Apply Changes to All Clients"):
            st.session_state["modal_action"] = "all"
            st.write('<script>showModal("all");</script>', unsafe_allow_html=True)

    with col3:
        if st.button("Compare Selected Client with Master"):
            if client_db == "All Clients":
                st.error("Please select a specific client to compare with the master database. The comparison feature is not available for 'All Clients'.")
            else:
                with st.spinner(f"Comparing {client_db} with master database..."):
                    response = requests.get(f"{BASE_URL}/compare", params={"client_db": client_db})
                    if response.status_code == 200:
                        data = response.json()["data"]
                        st.success("Comparison completed successfully.")

                        # Display results
                        st.write("### Missing Tables")
                        st.write(data["missing_tables"])

                        st.write("### Missing Columns")
                        st.write(data["missing_columns"])

                        st.write("### Datatype Mismatches")
                        st.json(data["datatype_mismatches"])

                        st.write("### Default Value Mismatches")
                        st.json(data["default_value_mismatches"])

                        st.write("### Missing Foreign Keys")
                        st.json(data["missing_foreign_keys"])

                        st.write("### Missing Stored Procedures")
                        st.json(data["missing_stored_procedures"])
                    else:
                        error_message = response.json().get("message", "Unknown error occurred.")
                        st.error(f"Failed to fetch comparison data. Error: {error_message}")

# **TAB 2: Copy Tool**

# Copy Tool Tab
with tab2:  # Second tab for "Copy Tool"
    st.title("Copy Data Between Tables")

    # Source Database and Table Selection
    st.header("Source Configuration")
    source_db = st.selectbox(
        "Select Source Database",
        [""] + requests.get(f"{BASE_URL}/databases").json().get("data", [])
    )
    if source_db:
        source_table = st.selectbox(
            "Select Source Table",
            [""] + requests.get(f"{BASE_URL}/tables", params={"database_name": source_db}).json().get("data", [])
        )
    else:
        source_table = None

    # Destination Database and Table Selection
    st.header("Destination Configuration")
    destination_db = st.selectbox(
        "Select Destination Database",
        [""] + requests.get(f"{BASE_URL}/databases").json().get("data", [])
    )
    if destination_db:
        destination_table = st.selectbox(
            "Select Destination Table",
            [""] + requests.get(f"{BASE_URL}/tables", params={"database_name": destination_db}).json().get("data", [])
        )
    else:
        destination_table = None

    # Option to delete existing data
    delete_existing = st.checkbox("Delete existing data in the destination table before copying")

# Copy Button
if st.button("Copy Data"):
    if not (source_db and source_table and destination_db and destination_table):
        st.error("Please select all required fields: source database, source table, destination database, and destination table.")
    else:
        with st.spinner("Copying data..."):
            try:
                # Perform the API request to copy data
                response = requests.post(
                    f"{BASE_URL}/copy",
                    json={
                        "source_db": source_db,
                        "source_table": source_table,
                        "destination_db": destination_db,
                        "destination_table": destination_table,
                        "delete_existing": bool(delete_existing),
                    },
                )
                if response.status_code == 200:
                    st.success(f"Data copied successfully from `{source_table}` in `{source_db}` to `{destination_table}` in `{destination_db}`.")
                else:
                    try:
                        error_message = response.json().get("message", "Unknown error occurred.")
                    except ValueError:
                        error_message = "Invalid response from server."
                    st.error(f"Failed to copy data. Error: {error_message}")
            except requests.exceptions.RequestException as e:
                st.error(f"An error occurred while copying data: {str(e)}")


# End Main Content Wrapper
st.markdown('</div>', unsafe_allow_html=True)

# Add Custom Footer
st.markdown(
    """
    <div class="footer">
        © 2025 Database Sync Tool | NestBotics Automation Pvt Ltd
    </div>
    """,
    unsafe_allow_html=True,
)
