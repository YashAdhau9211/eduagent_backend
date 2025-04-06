import streamlit as st
# Removed unused LangChain imports from here, agent handles them
# No need for concurrent.futures here anymore, agent handles it
from datetime import datetime
import uuid
import os # For checking persist dir existence maybe
import traceback # For detailed error logging

# Import the centralized agent logic
from agent import SubjectAgent
# Import utility and web scraping functions needed directly by the app (if any)
# from utils import ... # e.g., if checking persist_dir directly
# from web_scraper import google_search # No longer needed here, agent returns sources

# Define session state initialization for chats and agents
def initialize_session_state_app():
    # Basic UI state
    if 'file_uploader_key' not in st.session_state:
        st.session_state.file_uploader_key = 0 # May not be needed anymore

    # Agent Management
    if 'agents' not in st.session_state:
        st.session_state.agents = {
            "Computer Science": SubjectAgent("Computer Science"),
            "Math": SubjectAgent("Math"),
            "Physics": SubjectAgent("Physics")
            # Add more subjects as needed
        }
    if 'current_agent' not in st.session_state:
        # Default to one agent or None
        st.session_state.current_agent = st.session_state.agents.get("Computer Science")

    # Chat Management
    if 'chats' not in st.session_state:
        st.session_state.chats = {}
    if 'current_chat_id' not in st.session_state:
        create_new_chat(make_current=True) # Create a default chat on first run

    # Migrate old history if necessary (run once)
    if 'history' in st.session_state and st.session_state.history and not st.session_state.chats:
         print("Migrating old history to new chat structure...")
         # Ensure a default chat exists before migration attempt
         if not st.session_state.chats:
              create_new_chat(make_current=True)

         # Get the ID of the (now existing) current chat
         chat_id = st.session_state.current_chat_id
         if chat_id and chat_id in st.session_state.chats:
             st.session_state.chats[chat_id]["history"] = st.session_state.history
             del st.session_state['history'] # Remove old global history
         else:
             print("Warning: Could not migrate history, current chat ID invalid.")


# Function to create a new chat session
def create_new_chat(make_current=True):
    new_chat_id = str(uuid.uuid4())
    new_chat_name = f"Chat {len(st.session_state.chats) + 1}"
    st.session_state.chats[new_chat_id] = {
        "name": new_chat_name,
        "history": []
    }
    if make_current:
        st.session_state.current_chat_id = new_chat_id
    print(f"Created new chat: {new_chat_name} ({new_chat_id})")
    return new_chat_id

# Function to rename the current chat
def rename_current_chat(new_name):
    if 'current_chat_id' not in st.session_state or not st.session_state.current_chat_id:
         st.warning("No active chat selected to rename.")
         return

    current_chat_id = st.session_state.current_chat_id
    if current_chat_id in st.session_state.chats:
        st.session_state.chats[current_chat_id]["name"] = new_name
        st.success(f"Chat renamed to '{new_name}'")
    else:
        st.warning(f"Chat ID {current_chat_id} not found for renaming.")


# Function to delete a chat session
def delete_chat(chat_id):
    if chat_id in st.session_state.chats:
        deleted_name = st.session_state.chats[chat_id]["name"]
        del st.session_state.chats[chat_id]
        print(f"Deleted chat: {deleted_name} ({chat_id})")

        # If the deleted chat was the current one, select another or create a new one
        if 'current_chat_id' in st.session_state and chat_id == st.session_state.current_chat_id:
            if st.session_state.chats:
                # Select the first available chat (most recent based on reverse iteration later)
                st.session_state.current_chat_id = next(iter(reversed(st.session_state.chats.keys())))
                print(f"Switched to chat: {st.session_state.chats[st.session_state.current_chat_id]['name']}")
            else:
                # No chats left, create a new default one
                create_new_chat(make_current=True)
        st.rerun() # Force rerun to update sidebar display
    else:
        st.warning("Chat ID not found for deletion.")


# Display Sidebar for Agent Selection and Knowledge Base Management
def display_agent_sidebar():
    st.sidebar.markdown("## Subject Agent")

    # Ensure agents are initialized
    if 'agents' not in st.session_state or not st.session_state.agents:
        st.sidebar.error("Agents not initialized correctly.")
        return

    subject_list = list(st.session_state.agents.keys())
    current_subject = None
    selected_subject_index = 0 # Default to first subject

    # Safely get current agent's subject
    if 'current_agent' in st.session_state and st.session_state.current_agent:
         current_subject = st.session_state.current_agent.subject
         if current_subject in subject_list:
              selected_subject_index = subject_list.index(current_subject)

    selected_subject = st.sidebar.selectbox(
        "Select Subject",
        subject_list,
        index=selected_subject_index,
        key="subject_selector"
    )

    # Update current agent if selection changed or no agent is selected
    agent_changed = False
    if 'current_agent' not in st.session_state or not st.session_state.current_agent or selected_subject != st.session_state.current_agent.subject:
        st.session_state.current_agent = st.session_state.agents[selected_subject]
        print(f"Switched agent to: {selected_subject}")
        agent_changed = True # Flag that agent changed

    st.sidebar.markdown("---")

    # Display Knowledge Base section only if an agent is selected
    current_agent = st.session_state.get('current_agent') # Use .get for safety
    if current_agent:
        st.sidebar.markdown(f"### Knowledge Base ({current_agent.subject})")

        # Indicate KB status
        kb_status = "Not Created / Not Found"
        persist_dir = current_agent.persist_dir
        # Check if the directory exists and maybe contains Chroma files (basic check)
        try:
            if os.path.exists(persist_dir) and os.path.isdir(persist_dir) and any(f.endswith('.parquet') or f == 'chroma.sqlite3' for f in os.listdir(persist_dir)):
                 kb_status = "Exists"
        except Exception as e:
             print(f"Error checking persist directory {persist_dir}: {e}")
             kb_status = "Error checking status"


        st.sidebar.caption(f"Status: {kb_status} (Location: `{persist_dir}`)")

        # Use a unique key based on the agent to potentially reset uploader state on agent switch
        uploader_key = f"pdf_uploader_{current_agent.subject}"
        pdfs = st.sidebar.file_uploader(
            "Upload PDF documents to Create/Update KB",
            type="pdf",
            accept_multiple_files=True,
            key=uploader_key
        )

        if st.sidebar.button(f"Create/Update KB for {current_agent.subject}", key=f"create_kb_{current_agent.subject}"):
            if not pdfs:
                st.sidebar.warning("Please upload PDF documents first!")
            else:
                with st.spinner(f"Processing documents for {current_agent.subject}..."):
                    try:
                        # This method now handles processing and updating the agent's vector_store
                        current_agent.create_knowledge_base(pdfs)
                        st.sidebar.success(f"Knowledge base updated for {current_agent.subject}!")
                        # Rerun to update the status caption
                        st.rerun()
                    except Exception as e:
                        st.sidebar.error(f"Error creating KB: {e}")
                        print(traceback.format_exc()) # Log full error for debugging
    else:
        st.sidebar.warning("Select a subject agent to manage its knowledge base.")

    st.sidebar.markdown("---")
    # Instructions
    st.sidebar.markdown("### Instructions")
    st.sidebar.info("""
    1. Select a **Subject Agent**.
    2. Upload subject-specific PDFs & click **Create/Update KB**.
    3. Manage chats using the **Chats** section below.
    4. Ask questions in the main panel!
    """)

    # Rerun if agent changed to reflect changes immediately in UI
    if agent_changed:
         st.rerun()


# Display Sidebar for Chat Management
def display_chat_sidebar():
    st.sidebar.markdown("## Chats")

    if st.sidebar.button("➕ New Chat", key="new_chat_btn"):
        create_new_chat(make_current=True)
        st.rerun() # Update sidebar immediately

    st.sidebar.markdown("---")

    # Handle potential empty chat state
    if 'chats' not in st.session_state or not st.session_state.chats:
        st.sidebar.caption("No chats yet. Start by creating one!")
        return # Don't display chat list if empty

    # Use reverse iteration to show newest chats first
    chat_ids = list(reversed(st.session_state.chats.keys()))

    # Ensure current_chat_id is valid
    selected_chat_id = st.session_state.get('current_chat_id')
    if selected_chat_id not in st.session_state.chats:
         selected_chat_id = chat_ids[0] if chat_ids else None # Select most recent or None
         st.session_state.current_chat_id = selected_chat_id # Update state if invalid

    # Display chats - using buttons for delete functionality alongside
    for chat_id in chat_ids:
         # Check again if chat_id is still valid (could be deleted during loop/rerun)
         if chat_id not in st.session_state.chats:
              continue

         chat_data = st.session_state.chats[chat_id]
         col1, col2 = st.sidebar.columns([4, 1])

         # Use a unique key for each chat button
         button_key = f"select_chat_{chat_id}"
         is_current = chat_id == selected_chat_id

         # Display chat name - bold if current
         label = f"{'➡️ ' if is_current else ''}{chat_data['name']}"
         # Disable button if it's the current chat
         if col1.button(label, key=button_key, use_container_width=True, disabled=is_current):
             st.session_state.current_chat_id = chat_id
             print(f"Switched to chat: {chat_data['name']}")
             st.rerun() # Update main panel

         # Delete button
         delete_key = f"delete_chat_{chat_id}"
         if col2.button("🗑️", key=delete_key, help=f"Delete chat '{chat_data['name']}'"):
             delete_chat(chat_id)
             # Deletion handles rerun, exit loop iteration
             break # Exit loop as chat list has changed

    # Optional: Rename Chat (put below the list)
    st.sidebar.markdown("---")
    # Ensure selected_chat_id exists before attempting rename UI
    if selected_chat_id and selected_chat_id in st.session_state.chats:
        st.sidebar.markdown(f"**Rename Current Chat** ('{st.session_state.chats[selected_chat_id]['name']}')")
        new_name_key = f"rename_input_{selected_chat_id}"
        current_name = st.session_state.chats[selected_chat_id]['name']

        new_name = st.sidebar.text_input(
            "New name:",
            value=current_name,
            key=new_name_key
        )
        if st.sidebar.button("Save Name", key=f"save_rename_{selected_chat_id}"):
            # Check if name is not empty and actually changed
            if new_name and new_name != current_name:
                rename_current_chat(new_name)
                st.rerun()
            elif not new_name:
                 st.sidebar.warning("Chat name cannot be empty.")
            # No need for action if name hasn't changed


# Main Application Logic
def main():
    st.set_page_config(layout="wide", page_title="EduAgent.ai") # Set page title
    st.title("🎓 EduAgent.ai - Your Subject AI Tutor")

    # Initialize state variables for agents and chats
    initialize_session_state_app()

    # Display sidebars
    display_agent_sidebar()
    display_chat_sidebar()

    # Main panel
    st.markdown("---")

    # Get current agent and chat details safely
    current_agent = st.session_state.get('current_agent')
    current_chat_id = st.session_state.get('current_chat_id')

    # Check if agent is selected
    if not current_agent:
        st.warning("Please select a subject agent from the sidebar to begin.")
        return # Stop execution if no agent is selected

    # Check if a chat is selected / exists
    if not current_chat_id or current_chat_id not in st.session_state.chats:
         st.info("Create or select a chat from the sidebar.")
         # Attempt to recover if chat ID became invalid
         if st.session_state.chats:
              st.session_state.current_chat_id = next(iter(reversed(st.session_state.chats.keys()))) # Select most recent
              st.rerun()
         else: # No chats exist at all
             create_new_chat(make_current=True) # Create a fresh one
             st.rerun()
         return # Stop execution while state resets

    # We have a valid agent and chat ID now
    current_chat = st.session_state.chats[current_chat_id]
    chat_history = current_chat["history"]

    st.markdown(f"### Chat: {current_chat['name']} (Subject: {current_agent.subject})")

    # Display chat history (newest first) in a container
    history_container = st.container()
    with history_container:
        if chat_history:
             for entry in reversed(chat_history):
                  with st.chat_message("user"):
                       st.markdown(f"**Q:** {entry['question']}")
                  with st.chat_message("assistant"):
                       st.markdown(entry['answer']) # Display the final answer saved
                  # st.caption(f"_{entry.get('timestamp', '')}_") # Optional timestamp
                  st.markdown("---") # Separator between Q/A pairs
        else:
             st.caption("Chat history is empty. Ask your first question!")


    # Chat input area at the bottom
    st.markdown("---") # Separator before input
    question_key = f"question_input_{current_chat_id}" # Unique key per chat
    question = st.text_area(
        "Ask your question:",
        key=question_key,
        height=100,
        placeholder=f"Ask a question about {current_agent.subject}..."
    )

    if st.button("Get Answer", key=f"get_answer_btn_{current_chat_id}", type="primary"):
        if question:
            # Use a status indicator while processing
            status = st.status(f"Asking {current_agent.subject} agent... (This may take a moment)", expanded=True)

            try:
                # Call the agent's comprehensive method - This is the core call
                status.write("🧠 Thinking... Fetching information from all sources...")
                all_answers = current_agent.get_comprehensive_answer(question)

                # Explicitly update status based on actual flow (though agent logs more detail)
                status.write("✅ Information received, compiling final answer...")

                # *** Extract all answer components ***
                final_answer = all_answers.get("final", "Error: No final answer returned.")
                rag_answer = all_answers.get("rag", "RAG answer unavailable.")
                llm_answer = all_answers.get("llm", "LLM answer unavailable.")
                web_answer = all_answers.get("web", "Web answer unavailable.")
                sources = all_answers.get("sources", []) # Web URLs

                status.update(label="Answer generated!", state="complete", expanded=False) # Collapse status on success

                # *** Display results in tabs - MORE ROBUST DISPLAY ***
                tab_titles = ["Final Consolidated Answer", "Individual Source Answers", "Web Links Found"]
                tabs = st.tabs(tab_titles)

                # Tab 0: Final Answer
                with tabs[0]:
                    st.markdown("##### Consolidated Answer")
                    # Display final answer or a placeholder if it's empty/error
                    if final_answer and not ("Error" in final_answer or "failed" in final_answer.lower() or "empty" in final_answer.lower()):
                         st.markdown(final_answer)
                    else:
                         st.error(final_answer if final_answer else "*Could not generate a final answer.*")


                # Tab 1: Individual Answers (RAG, LLM, Web) - Explicit Handling
                with tabs[1]:
                    st.markdown(f"##### From Knowledge Base ({current_agent.subject} PDFs)")
                    # Check if the answer is meaningful before displaying, otherwise show placeholder
                    rag_unavailable_msgs = ["please create", "error initializing", "cannot get rag", "qa chain for", "failed to load", "unexpected response format", "an error occurred while retrieving", "do not seem to contain"]
                    if rag_answer and not any(msg in rag_answer.lower() for msg in rag_unavailable_msgs):
                        st.markdown(rag_answer)
                    else:
                        st.info(rag_answer if rag_answer else "*RAG source did not provide an answer.*")
                    st.markdown("---") # Separator

                    st.markdown("##### From Baseline LLM")
                    llm_unavailable_msgs = ["llm returned an empty", "an error occurred while contacting", "unavailable", "failed"]
                    if llm_answer and not any(msg in llm_answer.lower() for msg in llm_unavailable_msgs):
                        st.markdown(llm_answer)
                    else:
                        st.info(llm_answer if llm_answer else "*Baseline LLM did not provide an answer.*")
                    st.markdown("---") # Separator

                    st.markdown("##### From Web Search Synthesis")
                    web_unavailable_msgs = ["web search failed", "could not find relevant websites", "failed to scrape content", "could not extract meaningful content", "could not find a specific answer", "error synthesizing answer", "no websites provided", "unavailable"]
                    if web_answer and not any(msg in web_answer.lower() for msg in web_unavailable_msgs):
                        st.markdown(web_answer)
                    else:
                        st.info(web_answer if web_answer else "*Web synthesis did not provide an answer.*")


                # Tab 2: Web Links
                with tabs[2]:
                    st.markdown("##### Relevant Web Links Found")
                    valid_sources = isinstance(sources, list) and sources and not any("Error" in str(s) or "failed" in str(s) or "Missing" in str(s) for s in sources)
                    if valid_sources:
                        for i, url in enumerate(sources):
                            # Make links clickable
                            st.markdown(f"{i+1}. [{url}]({url})")
                    elif isinstance(sources, list) and sources:
                         # Show the error message if the list contains one
                         st.warning(f"Could not retrieve web links: {sources[0]}")
                    else:
                         # Handle case where sources might be None or empty list
                         st.info("No web links were found or retrieved for this question.")


                # Save to current chat's history ONLY if final answer is valid
                is_error_answer = "Error" in final_answer or "failed" in final_answer.lower() or "empty" in final_answer.lower() or "sorry, i could not" in final_answer.lower()
                if final_answer and not is_error_answer:
                    history_entry = {
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "question": question,
                        "answer": final_answer # Save only the final aggregated answer
                    }
                    # Make sure chat ID is still valid before appending
                    if current_chat_id in st.session_state.chats:
                        st.session_state.chats[current_chat_id]["history"].append(history_entry)
                        # Rerun to display the new history entry and potentially clear input
                        st.rerun()
                    else:
                         st.error("Failed to save history: Current chat session became invalid.")


            except Exception as e:
                st.error(f"An unexpected error occurred while processing your question: {e}")
                # Log the full traceback for debugging
                print(traceback.format_exc())
                if 'status' in locals(): # Check if status exists before updating
                    status.update(label="Processing failed.", state="error", expanded=True)

        else:
            st.warning("Please enter a question.")


if __name__ == "__main__":
    main()