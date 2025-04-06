import streamlit as st
from langchain.chains import RetrievalQA
from langchain_ollama import ChatOllama
from utils import process_documents, get_retriever
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate

# Custom prompt template
def get_custom_prompt():
    """Define and return the custom prompt template."""
    return ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(
            "You are an educational assistant designed to help students understand their textbooks. Follow these guidelines:\n"
            "1. Answer questions using only the information from the uploaded PDFs.\n"
            "2. Use simple, clear language suitable for an university student doing major in Computer Science.\n"
            "3. If the answer isn't in the documents, say: 'I cannot find relevant information in the provided documents.'\n"
            "4. Do not speculate, assume, or invent information.\n"
            "5. Maintain a professional tone and organize responses clearly (e.g., bullet points, step-by-step explanations).\n"
            "6. Encourage follow-up questions by asking if further clarification is needed.\n"
            "7. Provide examples to clarify concepts when helpful.\n"
            "8. Keep answers concise, focused, and exam-friendly."
        ),
        HumanMessagePromptTemplate.from_template(
            "Context:\n{context}\n\n"
            "Question: {question}\n\n"
            "Provide a precise and well-structured answer based on the context above. Ensure your response is easy to understand, includes examples where necessary, and is formatted in a way that students can use it for exams. If applicable, ask if the student needs further clarification."
        )
    ])

# Initialize QA Chain
def initialize_qa_chain():
    # First check if vector store exists
    if not st.session_state.vector_store:
        return None
        
    # If QA chain is not initialized but vector store exists, create it
    if not st.session_state.qa_chain and st.session_state.vector_store:
        try:
            llm = ChatOllama(model="deepseek-r1:1.5b", temperature=0.9)
            retriever = get_retriever()
            if not retriever:
                st.warning("Failed to initialize retriever")
                return None
                
            st.session_state.qa_chain = RetrievalQA.from_chain_type(
                llm,
                retriever=retriever,
                chain_type="stuff",
                chain_type_kwargs={"prompt": get_custom_prompt()}
            )
        except Exception as e:
            st.error(f"Error initializing QA chain: {str(e)}")
            return None
            
    return st.session_state.qa_chain

# Initialize the chatbot's memory (session states)
def initialize_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "vector_store" not in st.session_state:
        st.session_state.vector_store = None
    if "qa_chain" not in st.session_state:
        st.session_state.qa_chain = None
    if "history" not in st.session_state:
        st.session_state.history = []  # To store question-answer history

# Sidebar section
def display_sidebar():
    with st.sidebar:
        # Instructions
        st.markdown("### Instructions")
        st.info("""
        1. Upload PDF documents.
        2. Click 'Create Knowledge Base'.
        3. Once documents are processed, start chatting with the bot!
        """)
        
        # Streamlit file uploader widget with a unique key
        # pdfs = st.file_uploader("Upload PDF documents", type="pdf", accept_multiple_files=True, key="unique_agent_file_uploader")

        
        # Action Button with a unique key for creating the knowledge base
        # if st.button("Create Knowledge Base", key="rag_create_kb"):
        #     if not pdfs:
        #         st.warning("Please upload PDF documents first!")
        #         return

        #     try:
        #         with st.spinner("Creating knowledge base... This may take a moment."):
        #             vector_store = process_documents(pdfs)
        #             st.session_state.vector_store = vector_store
        #             st.session_state.qa_chain = None  # Reset QA chain when new documents are processed

        #         st.success("Knowledge base created!")  # Simple success message after completion

        #     except Exception as e:
        #         st.error(f"Error processing documents: {str(e)}")  # Show error if something goes wrong

# Chat interface section
def chat_interface():
    st.title("EduAgent.ai")
    st.markdown("Your personal textbook AI Agent powered by Deepseek 1.5B")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Handle user input
    if prompt := st.chat_input("Ask about your documents"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            
            with st.spinner("Fetching information..."):
                try:
                    # First check if vector store exists
                    if not st.session_state.vector_store:
                        full_response = "Please create a knowledge base by uploading PDF documents first."
                    else:
                        qa_chain = initialize_qa_chain()
                        
                        if not qa_chain:
                            full_response = "Error initializing QA chain. Please try recreating the knowledge base."
                        else:
                            response = qa_chain.invoke({"query": prompt})
                            full_response = response["result"]
                except Exception as e:
                    full_response = f"Error: {str(e)}"
            
            message_placeholder.markdown(full_response)
        
        st.session_state.messages.append({"role": "assistant", "content": full_response})

# Main function
def main():
    initialize_session_state()
    display_sidebar()
    chat_interface()

if __name__ == "__main__":
    main()
