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
         .logout-button {
            font-size: 16px;
            color: #ffffff;
            background-color: #f44336;
            border: none;
            padding: 5px 15px;
            border-radius: 5px;
            cursor: pointer;
        }
        .logout-button:hover {
            background-color: #d32f2f;
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

# Authentication function
def authenticate_user(username, password):
    """
    Authenticate the user by validating the username and password with the backend.
    """
    try:
        response = requests.post(f"{BASE_URL}/login", json={"username": username, "password": password})
        response.raise_for_status()  # Raise exception for HTTP errors
        return response.json().get("authenticated", False)
    except requests.exceptions.RequestException as e:
        print(f"Authentication failed: {e}")
        return False

# Initialize session state for authentication
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    # Login form
    st.title("Login to NestDBTool")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        with st.spinner("Authenticating..."):
            if authenticate_user(username, password):
                st.session_state["authenticated"] = True
                st.set_query_params()  # Clear any query parameters
                st.experimental_rerun()  # Redirect to login page
            else:
                st.error("Invalid username or password.")
else:
    print("Logout")
    if st.button("Logout"):
        st.session_state["authenticated"] = False
        st.set_query_params()  # Clear any query parameters
        st.experimental_rerun()  # Redirect to login page
 

    # Add custom header with logout button
    st.markdown(
        """
          <div class="custom-header">
        <span>Database Sync Tool</span>
    </div>

        """,
        unsafe_allow_html=True,
    )

    # Add main content wrapper
    st.markdown('<div class="main-content">', unsafe_allow_html=True)

    # Tab-based navigation
    tab1, tab2 = st.tabs(["Sync Tool", "Copy Tool"])

    # **TAB 1: Sync Tool**
    with tab1:
        st.markdown("### Sync Tool")
        @st.cache_data
        def fetch_client_databases():
            response = requests.get(f"{BASE_URL}/clients")
            if response.status_code == 200:
                return response.json().get("data", [])
            else:
                st.error("Failed to fetch client databases.")
                return []

        client_databases = fetch_client_databases()
        client_db = st.selectbox("Select Client Database", ["All Clients"] + client_databases)

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
                    st.error("Please select a specific client to compare with the master database.")
                else:
                    with st.spinner(f"Comparing {client_db} with master database..."):
                        response = requests.get(f"{BASE_URL}/compare", params={"client_db": client_db})
                        if response.status_code == 200:
                            data = response.json()["data"]
                            st.success("Comparison completed successfully.")
                            st.write("### Missing Tables")
                            st.write(data["missing_tables"])
                            st.write("### Missing Columns")
                            st.write(data["missing_columns"])
                            st.write("### Datatype Mismatches")
                            st.json(data["datatype_mismatches"])
                            st.write("### Missing Foreign Keys")
                            st.json(data["missing_foreign_keys"])
                            st.write("### Missing Stored Procedures")
                            st.json(data["missing_stored_procedures"])
                        else:
                            st.error(f"Failed to fetch comparison data.")

    # **TAB 2: Copy Tool**
    with tab2:
        st.title("Copy Data Between Tables")
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

        delete_existing = st.checkbox("Delete existing data in the destination table before copying")

        if st.button("Copy Data"):
            if not (source_db and source_table and destination_db and destination_table):
                st.error("Please select all required fields.")
            else:
                with st.spinner("Copying data..."):
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
                        st.success(f"Data copied successfully.")
                    else:
                        st.error(f"Failed to copy data.")

    # End main content wrapper
    st.markdown('</div>', unsafe_allow_html=True)

    # Add custom footer
    st.markdown(
        """
        <div class="footer">
            © 2025 Database Sync Tool | NestBotics Automation Pvt Ltd
        </div>
        """,
        unsafe_allow_html=True,
    )
