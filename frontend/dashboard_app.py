import streamlit as st
import requests
import time

# FastAPI Backend URL
API_URL = "http://localhost:8000/api"

st.set_page_config(page_title="MSAI Analytics Dashboard", page_icon="", layout="wide")

def login_page():
    st.title(" Dual Dashboard Login")
    st.write("Please log in to access the Admin or Database Manager dashboard.")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            if not username or not password:
                st.error("Please enter both username and password.")
                return
                
            try:
                response = requests.post(f"{API_URL}/login", json={"username": username, "password": password})
                
                if response.status_code == 200:
                    data = response.json()
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = data["username"]
                    st.session_state["role"] = data["role"]
                    st.success(f"Logging you into the {data['role']} dashboard...")
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to the Backend API. Make sure uvicorn is running!")

def tech_admin_dashboard():
    st.sidebar.title(" Tech Admin")
    st.sidebar.write(f"User: **{st.session_state['username']}**")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    tab1, tab2, tab3 = st.tabs(["System Logs & Tokens", "System Prompts", "Resolve Bugs"])
    
    with tab1:
        st.header("Session Logs & Token Usage")
        try:
            res = requests.get(f"{API_URL}/admin/logs", headers={"x-user-role": st.session_state["role"]})
            if res.status_code == 200:
                for log in res.json().get("logs", []):
                    st.code(log)
        except:
            st.warning("Could not fetch logs.")

    with tab2:
        st.header("Active System Prompts")
        try:
            res = requests.get(f"{API_URL}/admin/prompts", headers={"x-user-role": st.session_state["role"]})
            if res.status_code == 200:
                st.json(res.json())
        except:
            st.warning("Could not fetch prompts.")

    with tab3:
        st.header("Bug Resolution Desk")
        st.info("Here you would fetch open bugs from the `system_bugs` table and mark them as resolved.")
        bug_id = st.number_input("Enter Bug ID to resolve", min_value=1, step=1)
        if st.button("Mark Resolved"):
            res = requests.post(f"{API_URL}/admin/bugs/{bug_id}/resolve", headers={"x-user-role": st.session_state["role"]})
            st.success("Bug marked as resolved!")

def db_manager_dashboard():
    st.sidebar.title(" Database Manager")
    st.sidebar.write(f"User: **{st.session_state['username']}**")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    tab1, tab2, tab5, tab6, tab3, tab4 = st.tabs(["Pending Schemas", "ER Graph & Docs", "Edit Descriptions", "Manage Domains", "Employee Roles", "Report a Bug"])
    
    with tab1:
        st.header("Pending Schema Approvals")
        try:
            res = requests.get(f"{API_URL}/db_manager/schema/pending", headers={"x-user-role": st.session_state["role"]})
            if res.status_code == 200:
                pending = res.json()
                if not pending:
                    st.info("No pending schemas to approve.")
                for req in pending:
                    with st.expander(f"New Column: {req['table_name']}.{req['column_name']}"):
                        st.write(f"**Type:** {req['data_type']}")
                        
                        if f"step_{req['id']}" not in st.session_state:
                            st.session_state[f"step_{req['id']}"] = 1
                            
                        if st.session_state[f"step_{req['id']}"] == 1:
                            new_desc = st.text_input("Business Description", value=req['description'], key=f"desc_{req['id']}")
                            if st.button("Next → Add Business Questions", key=f"next_{req['id']}"):
                                st.session_state[f"desc_val_{req['id']}"] = new_desc
                                st.session_state[f"step_{req['id']}"] = 2
                                st.rerun()
                                
                        if st.session_state[f"step_{req['id']}"] == 2:
                            desc_key = f"desc_val_{req['id']}"
                            st.write(f"**Description:** {st.session_state.get(desc_key, '')}")
                            st.write("**Business Questions (Min 2 required)**")
                            q1 = st.text_input("Question 1", key=f"q1_{req['id']}")
                            q2 = st.text_input("Question 2", key=f"q2_{req['id']}")
                            q3 = st.text_input("Question 3 (Optional)", key=f"q3_{req['id']}")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("← Back", key=f"back_{req['id']}"):
                                    st.session_state[f"step_{req['id']}"] = 1
                                    st.rerun()
                            with col2:
                                if st.button("Approve & Sync Everything", key=f"approve_{req['id']}"):
                                    if not q1 or not q2:
                                        st.error("Missing required business questions. Please provide at least 2 questions.")
                                    else:
                                        questions = [q1, q2]
                                        if q3: questions.append(q3)
                                        
                                        res = requests.post(
                                            f"{API_URL}/db_manager/schema/approve/{req['id']}", 
                                            json={"updated_description": st.session_state[desc_key], "questions": questions},
                                            headers={"x-user-role": st.session_state["role"], "x-username": st.session_state["username"]}
                                        )
                                        if res.status_code == 200:
                                            st.success("Approved successfully!")
                                            st.session_state.pop(f"step_{req['id']}")
                                            time.sleep(1)
                                            st.rerun()
                                        else:
                                            st.error(f"Failed: {res.text}")
        except Exception as e:
            st.error(f"Error rendering pending schemas: {e}")
            st.warning("Could not fetch pending schemas.")

    with tab2:
        st.header("ER Graph & Documentation")
        if st.button("Fetch ER Graph Data"):
            res = requests.get(f"{API_URL}/db_manager/er_graph", headers={"x-user-role": st.session_state["role"]})
            if res.status_code == 200:
                data = res.json()
                st.write("**Tables (Nodes):**")
                st.write([n["id"] for n in data["nodes"]])
                st.write("**Relationships (Edges):**")
                st.json(data["edges"])
        
                st.divider()
        st.subheader(" Live Existing Documentation")
        
        # Put the buttons in columns so they sit side-by-side
        doc_col1, doc_col2 = st.columns(2)
        with doc_col1:
            view_schema_btn = st.button("View Table & Column Docs", use_container_width=True)
        with doc_col2:
            view_domain_btn = st.button("View Domain Summaries", use_container_width=True)
            
        # Render the massive JSON output OUTSIDE the columns so it takes full width!
        if view_schema_btn:
            res = requests.get(f"{API_URL}/db_manager/docs/schema", headers={"x-user-role": st.session_state["role"]})
            if res.status_code == 200:
                st.json(res.json())
                
        if view_domain_btn:
            res = requests.get(f"{API_URL}/db_manager/docs/domain", headers={"x-user-role": st.session_state["role"]})
            if res.status_code == 200:
                data = res.json()
                st.write("**Domain Tags:**")
                st.json(data.get("tags", {}))
                st.write("**Domain Summaries:**")
                st.markdown(data.get("summaries", ""))



    with tab5:
        st.header("Edit Existing Descriptions")
        st.info("Update descriptions for existing columns. Changes will automatically sync to BigQuery vector embeddings.")
        
        try:
            res = requests.get(f"{API_URL}/db_manager/docs/schema", headers={"x-user-role": st.session_state["role"]})
            if res.status_code == 200:
                schema_docs = res.json().get("tables", [])
                if not schema_docs:
                    st.warning("No existing schema documentation found.")
                else:
                    table_names = [t.get("table") for t in schema_docs]
                    selected_table = st.selectbox("Select Table", table_names)
                    
                    if selected_table:
                        table_data = next((t for t in schema_docs if t.get("table") == selected_table), {})
                        columns = table_data.get("columns", [])
                        
                        if not columns:
                            st.warning("No columns found for this table.")
                        else:
                            col_names = [c.get("column") for c in columns]
                            selected_col = st.selectbox("Select Column", col_names)
                            
                            if selected_col:
                                col_data = next((c for c in columns if c.get("column") == selected_col), {})
                                current_desc = col_data.get("description", "")
                                
                                if f"edit_step_{selected_table}_{selected_col}" not in st.session_state:
                                    st.session_state[f"edit_step_{selected_table}_{selected_col}"] = 1
                                    
                                step_key = f"edit_step_{selected_table}_{selected_col}"
                                
                                if st.session_state[step_key] == 1:
                                    new_desc = st.text_area("Update Description", value=current_desc, key=f"edit_desc_{selected_table}_{selected_col}")
                                    if st.button("Next → Update Business Questions"):
                                        st.session_state[f"edit_val_{selected_table}_{selected_col}"] = new_desc
                                        st.session_state[step_key] = 2
                                        st.rerun()
                                        
                                if st.session_state[step_key] == 2:
                                    edit_val_key = f"edit_val_{selected_table}_{selected_col}"
                                    st.write(f"**Description:** {st.session_state.get(edit_val_key, '')}")
                                    st.write("**Business Questions (Min 2 required)**")
                                    eq1 = st.text_input("Question 1", key=f"eq1_{selected_table}_{selected_col}")
                                    eq2 = st.text_input("Question 2", key=f"eq2_{selected_table}_{selected_col}")
                                    eq3 = st.text_input("Question 3 (Optional)", key=f"eq3_{selected_table}_{selected_col}")
                                    
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        if st.button("← Back"):
                                            st.session_state[step_key] = 1
                                            st.rerun()
                                    with col2:
                                        if st.button("Save & Sync to BigQuery"):
                                            if not eq1 or not eq2:
                                                st.error("Missing required business questions. Please provide at least 2 questions.")
                                            else:
                                                qs = [eq1, eq2]
                                                if eq3: qs.append(eq3)
                                                
                                                edit_res = requests.post(
                                                    f"{API_URL}/db_manager/schema/edit",
                                                    json={"table_name": selected_table, "column_name": selected_col, "updated_description": st.session_state[edit_val_key], "questions": qs},
                                                    headers={"x-user-role": st.session_state["role"], "x-username": st.session_state["username"]}
                                                )
                                                if edit_res.status_code == 200:
                                                    st.success(f"Successfully updated `{selected_table}.{selected_col}` and synced embedding to BigQuery!")
                                                    st.session_state[step_key] = 1
                                                else:
                                                    st.error(f"Failed to update: {edit_res.text}")
        except Exception as e:
            st.error(f"Failed to load schema data: {e}")

    with tab6:
        st.header("Manage Domains")
        st.info("Assign domains to new or existing tables. This automatically updates local YAMLs and BigQuery.")
        
        try:
            # Fetch all tables and current domains from the API
            res_schema = requests.get(f"{API_URL}/db_manager/docs/schema", headers={"x-user-role": st.session_state["role"]})
            res_domains = requests.get(f"{API_URL}/db_manager/docs/domain", headers={"x-user-role": st.session_state["role"]})
            
            if res_schema.status_code == 200 and res_domains.status_code == 200:
                schema_docs = res_schema.json().get("tables", [])
                domain_data = res_domains.json().get("tags", {}).get("tables", [])
                
                all_domains = set()
                table_to_domains = {}
                for t in domain_data:
                    t_name = t.get("table")
                    d_tags = t.get("domain_tags", [])
                    table_to_domains[t_name] = d_tags
                    for d in d_tags:
                        all_domains.add(d)
                
                # If there are no existing domains, provide a default list
                if not all_domains:
                    all_domains = {"ops", "hr", "loan", "kyc", "risk", "collections", "incentive", "leads", "marketing", "sales", "treasury", "finance", "insurance", "compliance", "audit", "support"}
                
                table_names = [t.get("table") for t in schema_docs]
                selected_table = st.selectbox("Select Table to Assign Domains", table_names, key="domain_table_select")
                
                if selected_table:
                    current_tags = table_to_domains.get(selected_table, [])
                    selected_domains = st.multiselect("Select Domains", options=sorted(list(all_domains)), default=current_tags)
                    
                    if st.button("Save Domain Mapping"):
                        dataset_name = "unknown"
                        for t in schema_docs:
                            if t.get("table") == selected_table:
                                dataset_name = t.get("dataset", "unknown")
                                break
                                
                        map_res = requests.post(
                            f"{API_URL}/db_manager/schema/domains",
                            json={"table_name": selected_table, "dataset_name": dataset_name, "domains": selected_domains},
                            headers={"x-user-role": st.session_state["role"], "x-username": st.session_state["username"]}
                        )
                        if map_res.status_code == 200:
                            st.success(f"Successfully mapped `{selected_table}` to domains: {selected_domains}")
                        else:
                            st.error(f"Failed to map domains: {map_res.text}")
        except Exception as e:
            st.error(f"Failed to load domain mapping interface: {e}")

    with tab3:
        st.header("Manage Employee Roles")

         # 1. Fetch the live roles from BigQuery first
        live_roles = ["Loading..."]
        try:
            role_res = requests.get(f"{API_URL}/db_manager/roles/available", headers={"x-user-role": st.session_state["role"]})
            if role_res.status_code == 200:
                live_roles = role_res.json().get("roles", [])
        except:
            st.error("Failed to fetch roles from API")
            
        # 2. Display them in the form
        with st.form("role_form"):
            emp_id = st.text_input("Employee ID ")
            new_role = st.selectbox("Select Role (Live from BigQuery)", live_roles)
            
            if st.form_submit_button("Assign Role"):
                res = requests.post(f"{API_URL}/db_manager/roles/assign", 
                                    json={"employee_id": emp_id, "new_role": new_role},
                                    headers={"x-user-role": st.session_state["role"]})
                if res.status_code == 200:
                    st.success(res.json()["message"])





    with tab4:
        st.header("Report a Bug to Tech Admin")
        with st.form("bug_form"):
            bug_desc = st.text_area("Describe the technical issue")
            if st.form_submit_button("Submit Bug"):
                res = requests.post(f"{API_URL}/db_manager/bugs", 
                                    json={"description": bug_desc},
                                    headers={"x-user-role": st.session_state["role"], "x-username": st.session_state["username"]})
                if res.status_code == 200:
                    st.success("Bug successfully submitted to the Tech Admin!")

# --- Routing Logic ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    login_page()
else:
    if st.session_state["role"] == "admin":
        tech_admin_dashboard()
    elif st.session_state["role"] == "db_manager":
        db_manager_dashboard()
    else:
        st.error("Unknown role.")
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()
