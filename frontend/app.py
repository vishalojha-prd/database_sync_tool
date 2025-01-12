import streamlit as st
import requests

# Set the app title and favicon
st.set_page_config(
    page_title="NestDBTool",  # Custom App Name
    page_icon="/home/vishal/Downloads/nestbotics.png", # Replace with the URL of your custom icon
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

        /* Modal background overlay */
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
            z-index: 9998;
        }

        /* Modal container */
        .modal-container {
            display: none;
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background-color: #ffffff;
            border-radius: 8px;
            box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.2);
            padding: 20px;
            z-index: 9999;
            max-width: 400px;
            text-align: center;
        }

        /* Modal buttons */
        .modal-buttons {
            margin-top: 20px;
            display: flex;
            justify-content: space-between;
        }

        .modal-buttons button {
            padding: 10px 20px;
            font-size: 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }

        .modal-buttons .confirm-button {
            background-color: #452a70;
            color: #ffffff;
        }

        .modal-buttons .cancel-button {
            background-color: #f0f0f0;
            color: #000000;
        }

        /* Full-width container for comparison results */
        .full-width-container {
            width: 100%;
            margin: 0 auto;
            padding: 10px;
            background-color: #ffffff;
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow-x: auto; /* Enable horizontal scrolling for wide content */
        }

        /* Import Roboto font */
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');
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

# Buttons to trigger modal or perform actions
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

                    # Display results in a full-width container
                    st.markdown('<div class="full-width-container">', unsafe_allow_html=True)

                    # Display missing tables
                    st.write("### Missing Tables")
                    st.write(data["missing_tables"])

                    # Display missing columns
                    st.write("### Missing Columns")
                    st.write(data["missing_columns"])

                    # Display datatype mismatches
                    st.write("### Datatype Mismatches")
                    st.json(data["datatype_mismatches"])

                    # Display missing foreign keys
                    st.write("### Missing Foreign Keys")
                    st.json(data["missing_foreign_keys"])

                    # Display missing stored procedures
                    st.write("### Missing Stored Procedures")
                    st.json(data["missing_stored_procedures"])

                    # Close the full-width container
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    error_message = response.json().get("message", "Unknown error occurred.")
                    st.error(f"Failed to fetch comparison data. Error: {error_message}")


# Handle modal confirmation
if "modal_action" in st.session_state:
    if st.session_state["modal_action"] == "selected":
        if client_db != "All Clients":
            st.write("Updating the selected client...")
            response = requests.post(f"{BASE_URL}/update", json={"client_db": client_db})
            if response.status_code == 200:
                st.success(f"Updates applied to client '{client_db}' successfully.")
            else:
                st.error(f"Failed to update client '{client_db}'. Error: {response.json().get('message', 'Unknown error')}")
        else:
            st.warning("Please select a specific client.")

    elif st.session_state["modal_action"] == "all":
        st.write("Updating all clients...")
        response = requests.post(f"{BASE_URL}/update", json={"apply_to_all": True})
        if response.status_code == 200:
            st.success("Updates applied to all clients successfully.")
        else:
            st.error(f"Failed to update all clients. Error: {response.json().get('message', 'Unknown error')}")

    # Reset modal state
    st.session_state["modal_action"] = None

# End Main Content Wrapper
st.markdown('</div>', unsafe_allow_html=True)

# Add Custom Footer
st.markdown(
    """
    <div class="footer">
        © 2025 Database Sync Tool | NestBotics Automation Pvt Ltd</a>
    </div>
    """,
    unsafe_allow_html=True,
)
