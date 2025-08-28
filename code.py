import streamlit as st
from jira import JIRA
from jira.exceptions import JIRAError

# ---------------------------
# CONNECT TO JIRA
# ---------------------------
@st.cache_resource
def connect_jira():
    options = {"server": "https://jira.grazitti.com"}  # your Jira server
    jira = JIRA(options, basic_auth=("singh", "#029"))
    return jira

jira = connect_jira()

# ---------------------------
# HELPERS
# ---------------------------
def get_project_users(project_key):
    """Fetch assignable users for a project"""
    try:
        users = jira.search_assignable_users_for_projects("", project_key, maxResults=1000)
        assignees = {}
        for u in users:
            if hasattr(u, "accountId"):   # Jira Cloud
                assignees[u.displayName] = u.accountId
            elif hasattr(u, "name"):      # Jira Server
                assignees[u.displayName] = u.name
            elif hasattr(u, "key"):       # fallback
                assignees[u.displayName] = u.key
        return assignees
    except Exception as e:
        st.error(f"Error fetching users: {e}")
        return {}

def get_epics(project_key):
    """Fetch epics in project"""
    try:
        jql = f'project = {project_key} AND issuetype = Epic ORDER BY created DESC'
        epics = jira.search_issues(jql, maxResults=100)
        return {epic.fields.summary: epic.key for epic in epics}
    except Exception as e:
        st.error(f"Error fetching epics: {e}")
        return {}

def create_epic(project_key, epic_name):

    """Create a new Epic"""
    try:
        epic = jira.create_issue(
            fields={
                "project": {"key": project_key},
                "summary": epic_name,
                "issuetype": {"name": "Epic"},
                "customfield_10102": epic_name
            }
        )
        return epic
    except Exception as e:
        st.error(f"Error creating epic: {e}")
        return None

# ---------------------------
# STREAMLIT UI
# ---------------------------
st.title("🎫 Jira Ticket Creator")

# Project selection
project_key = st.text_input("Enter Project Key (e.g., LDP):")

if project_key:
    assignees = get_project_users(project_key)
    epics = get_epics(project_key)

    if assignees:
        assignee_name = st.selectbox("Select Assignee", list(assignees.keys()))
        assignee_id = assignees[assignee_name]

        # Epic dropdown
        epic_options = list(epics.keys()) + ["➕ Add new epic"]
        selected_epic = st.selectbox("Select Epic", epic_options)

        epic_key = None
        if selected_epic == "➕ Add new epic":
            new_epic_name = st.text_input("Enter New Epic Name")
            if st.button("Create Epic"):
                new_epic = create_epic(project_key, new_epic_name)
                if new_epic:
                    st.success(f"✅ Epic created: {new_epic.key}")
                    epic_key = new_epic.key
        else:
            epic_key = epics[selected_epic]

        # Ticket details
        summary = st.text_input("Issue Summary")
        description = st.text_area("Issue Description")

        if st.button("Create Ticket"):
            try:
                issue_dict = {
                    "project": {"key": project_key},
                    "summary": summary,
                    "description": description,
                    "issuetype": {"name": "Task"},
                    # Cloud → accountId, Server → name
                    "assignee": {"accountId": assignee_id} if "@" in assignee_id or len(assignee_id) > 20 else {"name": assignee_id},
                    'customfield_10100': epic_key # replace with your Epic Link field id
                }

                fields = jira.fields()
                epic_field = [f for f in fields if f["name"] == "Epic Name"]
                print(epic_field)

                issue = jira.create_issue(fields=issue_dict)
                st.success(f"✅ Ticket created: {issue.key} (Epic: {epic_key})")
            except JIRAError as e:
                st.error(f"❌ Error creating ticket: {e.text}")
