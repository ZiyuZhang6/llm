import streamlit as st
import requests
import openai

# API configuration
API_BASE_URL = "http://localhost:8000"  # Adjust as needed


# ----------------------------
# Authentication Helpers
# ----------------------------
def do_login(email, password):
    """Perform login and save token in session state."""
    resp = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={"email": email, "password": password},
    )
    if resp.status_code == 200:
        data = resp.json()
        st.session_state["access_token"] = data["access_token"]
        st.session_state["email"] = email
        st.success("Logged in successfully!")
        st.rerun()
    else:
        st.error(f"Login failed: {resp.text}")


def logout():
    """Clear session state and reload."""
    st.session_state["access_token"] = None
    st.session_state["email"] = None
    st.rerun()


# ----------------------------
# Chat Title Generation Helpers
# ----------------------------
def generate_chat_title(first_message: str) -> str:
    """
    Uses OpenAI to generate a short, descriptive chat title based on the first message.
    Adjust engine, prompt, and parameters as needed.
    """
    prompt = (
        f"Generate a concise title for a chat conversation "
        f"that starts with: '{first_message}'"
    )
    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=10,
            temperature=0.7,
        )
        title = response.choices[0].text.strip().strip('"')
        return title if title else "Chat"
    except Exception as e:
        st.error(f"Chat title generation failed: {e}")
        return "Chat"


def update_chat_title(chat_id: str, new_title: str, headers: dict):
    """
    Update the chat title on the backend.
    Assumes the update endpoint accepts a "name" field.
    """
    payload = {"name": new_title}
    resp = requests.put(
        f"{API_BASE_URL}/chats/{chat_id}", headers=headers, json=payload
    )
    return resp


# ----------------------------
# Main App
# ----------------------------
def main():
    st.title("LLM Research Assistant - Chat")

    # Only show the login form if not authenticated.
    if "access_token" not in st.session_state or not st.session_state["access_token"]:
        st.header("Login")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            do_login(email, password)
        st.stop()  # Stop further rendering if not logged in.

    # Set authorization header for API calls.
    headers = {"Authorization": f"Bearer {st.session_state['access_token']}"}

    # Fetch current user info (assumes /users/me endpoint exists).
    user_me_resp = requests.get(f"{API_BASE_URL}/users/me", headers=headers)
    if user_me_resp.status_code != 200:
        st.error("Failed to retrieve user info. Please log in again.")
        st.stop()
    current_user = user_me_resp.json()
    st.session_state["user_id"] = current_user["id"]

    # ----------------------------
    # Sidebar: Display Chat List and Controls
    # ----------------------------
    with st.sidebar:
        # Inject custom CSS for a ChatGPT-like sidebar.
        st.markdown(
            """
            <style>
            .chat-entry {
                padding: 6px 10px;
                margin: 4px 0;
                border-radius: 6px;
                cursor: pointer;
                transition: background-color 0.2s ease-in-out;
                display: flex;
                align-items: center;
                justify-content: space-between;
                font-size: 15px;
            }
            .chat-entry:hover {
                background-color: #f0f0f0;
            }
            .chat-entry button {
                background: none;
                border: none;
                font-size: 15px;
                color: #333;
                text-align: left;
                flex: 1;
                padding: 0;
            }
            .delete-btn {
                background: none;
                border: none;
                font-size: 15px;
                color: #888;
                cursor: pointer;
                margin-left: 8px;
            }
            .delete-btn:hover {
                color: #e74c3c;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        st.header("Your Chats")
        # New Chat button (always visible).
        if st.button("➕ New Chat"):
            new_chat_resp = requests.post(
                f"{API_BASE_URL}/chats",
                headers=headers,
                json={
                    "owner_id": current_user["id"],
                    "message_chain": [
                        {"role": "system", "content": "New chat started"}
                    ],
                },
            )
            if new_chat_resp.status_code == 201:
                st.success("New chat created!")
                st.rerun()
            else:
                st.error(f"Error creating new chat: {new_chat_resp.text}")

        # Fetch the chat list for the current user.
        chats_resp = requests.get(
            f"{API_BASE_URL}/chats?owner_id={current_user['id']}", headers=headers
        )
        if chats_resp.status_code == 200:
            chats = chats_resp.json()
        else:
            st.error("Failed to load chats.")
            chats = []

        # Display each chat as a styled entry with a delete widget.
        for chat in chats:
            chat_name = chat.get("name") or f"Chat {chat.get('id')}"
            st.markdown('<div class="chat-entry">', unsafe_allow_html=True)
            col1, col2 = st.columns([4, 1])
            with col1:
                if st.button(
                    chat_name,
                    key=f"chat_{chat['id']}",
                    help="Select Chat",
                    use_container_width=True,
                ):
                    st.session_state["selected_chat_id"] = chat["id"]
            with col2:
                if st.button("🗑", key=f"delete_{chat['id']}", help="Delete Chat"):
                    del_resp = requests.delete(
                        f"{API_BASE_URL}/chats/{chat['id']}", headers=headers
                    )
                    if del_resp.status_code == 204:
                        st.success("Chat deleted!")
                        st.rerun()
                    else:
                        st.error("Failed to delete chat.")
            st.markdown("</div>", unsafe_allow_html=True)

        if st.button("Logout"):
            logout()

    # ----------------------------
    # Main Chat Interface
    # ----------------------------
    st.header("Conversation")
    selected_chat_id = st.session_state.get("selected_chat_id")
    if selected_chat_id:
        chat_detail_resp = requests.get(
            f"{API_BASE_URL}/chats/{selected_chat_id}", headers=headers
        )
        if chat_detail_resp.status_code == 200:
            chat_data = chat_detail_resp.json()
            chat_history = chat_data.get("message_chain", [])
            chat_name = chat_data.get("name", "New Chat")
        else:
            st.error("Failed to load chat conversation.")
            chat_history = []
            chat_name = "New Chat"

        # Display chat messages with bubble styling.
        for msg in chat_history:
            if msg.get("role") == "human":
                st.markdown(
                    """<div style="text-align: right; background: #dcf8c6; padding: 8px;
                    border-radius: 8px; margin: 4px 0;">
                    <strong>You:</strong> {}</div>""".format(
                        msg.get("content")
                    ),
                    unsafe_allow_html=True,
                )
            elif msg.get("role") == "ai":
                st.markdown(
                    """<div style="text-align: left; background: #f1f0f0; padding: 8px;
                    border-radius: 8px; margin: 4px 0;">
                    <strong>Assistant:</strong> {}</div>""".format(
                        msg.get("content")
                    ),
                    unsafe_allow_html=True,
                )

        st.markdown("---")
        new_message = st.text_input("Your Message", key="new_chat_message")
        if st.button("Send Message"):
            if new_message.strip() == "":
                st.warning("Please enter a message.")
            else:
                payload = {"question": new_message, "chat_history": chat_history}
                resp = requests.post(
                    f"{API_BASE_URL}/chats/chat/{selected_chat_id}",
                    headers=headers,
                    json=payload,
                )
                if resp.status_code == 200:
                    st.success("Message sent!")
                    if chat_name == "New Chat":
                        new_title = generate_chat_title(new_message)
                        update_resp = update_chat_title(
                            selected_chat_id, new_title, headers
                        )
                        if update_resp.status_code == 200:
                            st.success("Chat title updated!")
                    st.rerun()
                else:
                    st.error("Error sending message: " + resp.text)
    else:
        st.info("Select a chat from the sidebar to start a conversation.")


if __name__ == "__main__":
    main()
