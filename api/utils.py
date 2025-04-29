# api/utils.py

import os
import tempfile
import traceback # For detailed error logging
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PDFPlumberLoader
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
import shutil # For potentially clearing the directory
from django.conf import settings # Import Django settings

def process_documents(pdf_paths_list, subject_persist_dir_name):
    """
    Loads, splits, and embeds PDF documents from a list of file paths
    into a Chroma vector store.

    Args:
        pdf_paths_list (list): List of strings, where each string is the full path to a PDF file
                               (typically temporary paths from file uploads).
        subject_persist_dir_name (str): The subject-specific directory NAME (e.g., 'chroma_db_math').

    Returns:
        Chroma: The created/updated vector store instance, or None on failure.
    """
    base_persist_path = settings.CHROMA_DB_ROOT_DIR
    persist_dir = os.path.join(base_persist_path, subject_persist_dir_name)

    print(f"Using persistence directory: {persist_dir}")
    os.makedirs(persist_dir, exist_ok=True) # Ensure directory exists

    if not pdf_paths_list:
        print("No PDF file paths provided to process.")
        return None

    documents = []
    print(f"Loading {len(pdf_paths_list)} PDF file(s) from provided paths...")

    for path in pdf_paths_list:
        file_basename = os.path.basename(path)
        try:
            if not path.lower().endswith('.pdf'):
                 print(f"Skipping non-PDF path: {file_basename}")
                 continue

            if not os.path.exists(path):
                print(f"Error: Temporary file path does not exist: {path}")
                continue

            loader = PDFPlumberLoader(path)
            loaded_docs = loader.load()
            if loaded_docs:
                 print(f"Successfully loaded {len(loaded_docs)} pages/documents from {file_basename}")
                 documents.extend(loaded_docs)
            else:
                 print(f"Warning: PDFPlumberLoader returned no documents for {file_basename}")
        except Exception as e:
            print(f"Error loading PDF {file_basename} from path {path}: {e}")
            traceback.print_exc()
            continue # Skip this problematic file


    if not documents:
         print("No content could be loaded from the provided PDF paths.")
         return None

    try:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1200,  # Consider making these configurable in settings.py
            chunk_overlap=150 # Consider making these configurable in settings.py
        )
        print("Splitting documents into chunks...")
        splits = text_splitter.split_documents(documents)
        print(f"Created {len(splits)} document chunks.")

        if not splits:
             print("Document splitting resulted in zero chunks.")
             return None

        embedding_model_name = getattr(settings, 'EMBEDDING_MODEL', 'nomic-embed-text')
        print(f"Initializing embeddings model: {embedding_model_name}...")
        embeddings = OllamaEmbeddings(model=embedding_model_name)

        print(f"Creating/updating vector store at: {persist_dir}")

        vector_store = Chroma.from_documents(
            documents=splits,
            embedding=embeddings,
            persist_directory=persist_dir
        )
        print("Vector store processing complete.")
        return vector_store # Return the Chroma instance

    except Exception as e:
        print(f"An error occurred during splitting, embedding, or vector store creation: {e}")
        traceback.print_exc()
        return None


def get_retriever(subject_persist_dir_name):
    """
    Initializes and returns a vector store retriever from a persisted directory,
    using the base path from Django settings.

    Args:
        subject_persist_dir_name (str): The subject-specific directory NAME (e.g., 'chroma_db_math').

    Returns:
        VectorStoreRetriever or None: Retriever instance or None if initialization fails or directory doesn't exist.
    """
    base_persist_path = settings.CHROMA_DB_ROOT_DIR
    persist_dir = os.path.join(base_persist_path, subject_persist_dir_name)

    if not os.path.exists(persist_dir) or not os.path.isdir(persist_dir):
        print(f"Persistence directory not found or is not a directory: {persist_dir}")
        return None
    if not any(f.endswith('.parquet') or f == 'chroma.sqlite3' for f in os.listdir(persist_dir)):
         print(f"Persistence directory exists but may be empty or invalid: {persist_dir}")

    try:
        embedding_model_name = getattr(settings, 'EMBEDDING_MODEL', 'nomic-embed-text')
        embeddings = OllamaEmbeddings(model=embedding_model_name)

        print(f"Attempting to load vector store from: {persist_dir}")
        vector_store = Chroma(
            persist_directory=persist_dir,
            embedding_function=embeddings
        )
        print(f"Successfully loaded vector store from: {persist_dir}")

        retriever_search_type = getattr(settings, 'RETRIEVER_SEARCH_TYPE', 'mmr')
        retriever_k = getattr(settings, 'RETRIEVER_K', 3)
        print(f"Creating retriever (type={retriever_search_type}, k={retriever_k})")
        return vector_store.as_retriever(search_type=retriever_search_type, search_kwargs={"k": retriever_k})

    except Exception as e:
        print(f"Error initializing vector store or retriever from {persist_dir}: {e}")
        traceback.print_exc()
        return None