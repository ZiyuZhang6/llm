import streamlit as st
import requests
import subprocess
import time


fastapi_process = subprocess.Popen(["uvicorn", "llm_research_assistant.main:app", "--host", "0.0.0.0", "--port", "8000"])
time.sleep(5)  


API_BASE_URL = "http://localhost:8000"  # Adjust if needed


def do_login(email, password):
    """Helper function to handle the login call and session state update."""
    resp = requests.post(
        f"{API_BASE_URL}/auth/login", json={"email": email, "password": password}
    )
    if resp.status_code == 200:
        data = resp.json()
        st.session_state["access_token"] = data["access_token"]
        st.session_state["email"] = email
        st.success("Logged in successfully!")
        st.rerun()  # Force a page re-run to show protected content
    else:
        st.error(f"Login failed: {resp.text}")


def logout():
    """Clear the session state and rerun."""
    st.session_state["access_token"] = None
    st.session_state["email"] = None
    st.rerun()


def main():
    st.title("LLM Research Assistant - Auth via MongoDB + JWT")

    # Initialize session keys
    if "access_token" not in st.session_state:
        st.session_state["access_token"] = None
    if "email" not in st.session_state:
        st.session_state["email"] = None

    # If no token is stored, show login form
    if not st.session_state["access_token"]:
        st.header("Login")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            do_login(email, password)

        st.stop()  # Stop so we don't render the rest of the page
    else:
        # Already logged in
        if st.button("Logout"):
            logout()

        st.write(f"You're logged in as **{st.session_state['email']}**!")

        # Retrieve current user info from /users/me
        headers = {"Authorization": f"Bearer {st.session_state['access_token']}"}
        user_me_resp = requests.get(f"{API_BASE_URL}/users/me", headers=headers)
        if user_me_resp.status_code == 200:
            current_user = user_me_resp.json()
            user_id = current_user["id"]

            # 1) List Papers
            st.header("My Papers")
            papers_resp = requests.get(
                f"{API_BASE_URL}/papers?owner_id={user_id}", headers=headers
            )
            if papers_resp.status_code == 200:
                papers = papers_resp.json()
                for p in papers:
                    st.write(
                        f"- **Title**: {p['filename']} | Shared: {p['shared']} "
                        f"| ID: {p['id']}"
                    )
            else:
                st.error("Failed to list papers: " + papers_resp.text)

            # 2) Create new Paper
            st.subheader("Create a Paper")
            new_title = st.text_input("Paper Title", key="paper_title_input")
            new_shared = st.checkbox("Shared?", key="paper_shared_input")
            if st.button("Create Paper"):
                create_resp = requests.post(
                    f"{API_BASE_URL}/papers",
                    headers=headers,
                    json={
                        "title": new_title,
                        "shared": new_shared,
                        "owner_id": user_id,
                    },
                )
                if create_resp.status_code == 201:
                    st.success("Paper created!")
                    st.rerun()  # re-run to reflect new paper in the list
                else:
                    st.error(f"Error: {create_resp.text}")

            # 3) Show My Chats
            st.header("My Chats")
            chats_resp = requests.get(
                f"{API_BASE_URL}/chats?owner_id={user_id}", headers=headers
            )
            if chats_resp.status_code == 200:
                chats = chats_resp.json()
                for c in chats:
                    st.write(f"Chat ID: {c['id']}, Messages: {c['message_chain']}")
            else:
                st.error("Could not retrieve chats: " + chats_resp.text)

            if st.button("Create Empty Chat"):
                new_chat_resp = requests.post(
                    f"{API_BASE_URL}/chats",
                    headers=headers,
                    json={
                        "owner_id": user_id,
                        "message_chain": [
                            {"role": "system", "content": "New chat started"}
                        ],
                    },
                )
                if new_chat_resp.status_code == 201:
                    st.success("Chat created!")
                    st.rerun()
                else:
                    st.error(f"Error: {new_chat_resp.text}")

        else:
            st.error("Failed to retrieve current user info (maybe token expired?).")
            if st.button("Clear token and re-login"):
                logout()


if __name__ == "__main__":
    main()
