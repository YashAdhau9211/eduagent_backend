# EduAgent.ai - Backend (Django/DRF)

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-4.x-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Django REST framework](https://img.shields.io/badge/DRF-3.x-A30000?logo=django)](https://www.django-rest-framework.org/)
[![Langchain](https://img.shields.io/badge/Langchain-^0.1-blue)](https://python.langchain.com/)
[![Ollama](https://img.shields.io/badge/Ollama-grey?logo=ollama)](https://ollama.ai/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-vector--store-orange)](https://www.trychroma.com/)
[![Simple JWT](https://img.shields.io/badge/dj--rest--auth_/_simplejwt-JWT_Auth-brightgreen)](https://django-rest-framework-simplejwt.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

This repository contains the Django/DRF backend API for EduAgent.ai, an AI-powered tutoring platform.

**Frontend Repo:** [Link to the EduAgent.ai Frontend GitHub repository]

## Overview

EduAgent.ai allows users to interact with subject-specific AI agents. This backend provides the API endpoints necessary for the [EduAgent.ai Frontend](https://github.com/YashAdhau9211/eduagent-frontend) to function. Its core responsibilities include:

*   **User Authentication:** Handling user registration and login using JWT (JSON Web Tokens).
*   **API Endpoints:** Providing RESTful endpoints for managing subjects, chat sessions, chat messages, and knowledge bases.
*   **AI Orchestration:** Managing subject-specific AI agents (`SubjectAgent`).
*   **Knowledge Base Management:** Processing uploaded PDF documents (text extraction, chunking, embedding using Ollama) and storing/retrieving them from a ChromaDB vector store for Retrieval-Augmented Generation (RAG).
*   **Multi-Source Answer Generation:** Coordinating calls to:
    1.  RAG pipeline (using Langchain and ChromaDB).
    2.  Direct query to a local LLM (via Ollama).
    3.  Web search (using Google Custom Search API), scraping relevant content, and summarizing it using Ollama.
*   **Answer Synthesis:** Aggregating the results from the three sources using an LLM (Ollama) to produce a final, coherent answer.
*   **Data Persistence:** Storing user, chat, and message data in a database (SQLite for development).

## Features

*   **RESTful API:** Built with Django REST Framework.
*   **Asynchronous:** Uses ASGI (Uvicorn) for handling potentially long-running AI tasks concurrently.
*   **JWT Authentication:** Secure user login/registration using `dj-rest-auth` and `djangorestframework-simplejwt`.
*   **Subject Specialization:** Instantiates separate `SubjectAgent` objects, each managing its own prompts and ChromaDB vector store.
*   **PDF-based RAG:**
    *   Accepts PDF uploads via API.
    *   Uses `PDFPlumberLoader` for text extraction.
    *   Uses `RecursiveCharacterTextSplitter` for chunking.
    *   Uses `OllamaEmbeddings` (e.g., `nomic-embed-text`) for vectorization.
    *   Persists embeddings in subject-specific ChromaDB collections.
    *   Uses Langchain `RetrievalQA` chain for document-based question answering.
*   **Multi-Source Querying:** Fetches answers from RAG, direct LLM (Ollama), and summarized web search results.
*   **Answer Aggregation:** Uses an LLM (Ollama) to synthesize multiple answer sources into a final response. Cleans `<think>` tags from output.
*   **Chat Session Management:** CRUD operations for chat sessions, associated with the authenticated user.
*   **CORS configured:** Allows requests from the frontend development server.

## Tech Stack

*   **Python:** 3.10+
*   **Django:** 4.x
*   **Django REST Framework (DRF):** For building the API.
*   **Uvicorn:** ASGI server.
*   **Langchain:** Core framework for RAG pipeline, document handling.
*   **Ollama (`ollama` library):** Interface with local LLMs and embedding models.
*   **ChromaDB (`chromadb-client`):** Vector database for RAG.
*   **PDFPlumber:** PDF parsing library.
*   **Requests:** HTTP library for web scraping and API calls.
*   **BeautifulSoup4:** HTML parsing for web scraping.
*   **`djangorestframework-simplejwt`:** JWT implementation for DRF.
*   **`dj-rest-auth`:** Authentication endpoints (login, register, etc.).
*   **`django-allauth`:** Dependency for `dj-rest-auth`.
*   **`django-cors-headers`:** Cross-Origin Resource Sharing middleware.
*   **SQLite:** Default database for development. (PostgreSQL recommended for production)

## Project Structure
Use code with caution.
Markdown
```bash
eduagent_project/ # Django Project Root
├── eduagent_project/ # Main project config (settings.py, urls.py)
├── api/ # Core application logic
│ ├── migrations/
│ ├── init.py
│ ├── admin.py
│ ├── agent.py # SubjectAgent class
│ ├── agent_manager.py # Handles agent instances
│ ├── apps.py
│ ├── models.py # Database models (ChatSession, ChatMessage)
│ ├── serializers.py # DRF serializers
│ ├── tests.py
│ ├── urls.py # API endpoint routing (/api/)
│ ├── utils.py # PDF processing, retriever loading
│ ├── views.py # DRF API Views
│ └── web_scraper.py # Web search and scraping functions
├── chroma_db/ # Default root for ChromaDB stores (configurable)
├── db.sqlite3 # Development database
├── manage.py # Django management script
├── requirements.txt # Python dependencies
└── README.md # This file
```

## API Endpoints

Key endpoints include:
*   `/api/subjects/` (GET): List available subjects. (Public)
*   `/api/subjects/{subject}/kb/` (POST): Upload PDFs (key: `files`). (Authenticated)
*   `/api/chats/` (GET, POST): List user's chats, Create a new chat. (Authenticated)
*   `/api/chats/{chat_id}/` (GET, PATCH, DELETE): Retrieve/Update/Delete a specific chat. (Authenticated)
*   `/api/query/` (POST): Submit a question to a chat. (Authenticated)
*   `/auth/login/` (POST): User login. (Public)
*   `/auth/register/` (POST): User registration. (Public)
*   `/auth/user/` (GET): Get current user details. (Authenticated)
*   `/auth/logout/` (POST): User logout (optional backend action). (Authenticated)
*   `/auth/token/refresh/` (POST): Refresh JWT access token (optional). (Public)

*(Refer to DRF's Browsable API at `http://127.0.0.1:8000/api/` or `http://127.0.0.1:8000/auth/` for details when running).*

## Getting Started

**Prerequisites:**

*   Python 3.10 or later.
*   Pip (Python package installer).
*   Ollama installed and running locally with the required models (e.g., `ollama pull deepseek-r1:1.5b`, `ollama pull nomic-embed-text`). Verify Ollama serves on its default port (usually 11434).
*   Google Custom Search API Key and Search Engine ID (optional, for web search feature). Store these securely (e.g., environment variables, `.env` file).

**Installation & Setup:**

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd eduagent-backend
    ```
2.  **Create and activate a virtual environment (Recommended):**
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configure Environment Variables:**
    *   Create a `.env` file in the project root (`eduagent_project/`).
    *   Add necessary secrets and configurations (refer to `settings.py` comments for required variables like `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `GOOGLE_CSE_ID`, `GOOGLE_API_KEY`, `CORS_ALLOWED_ORIGINS`). Ensure `settings.py` reads these.
        ```dotenv
        # Example .env content
        SECRET_KEY='your-very-strong-django-secret-key'
        DEBUG=True
        ALLOWED_HOSTS=127.0.0.1,localhost
        DATABASE_URL=sqlite:///db.sqlite3
        # OLLAMA_BASE_URL=http://localhost:11434 # If not default
        GOOGLE_CSE_ID='YOUR_CSE_ID'
        GOOGLE_API_KEY='YOUR_GOOGLE_API_KEY'
        CORS_ALLOWED_ORIGINS='http://localhost:3000,http://localhost:5173'
        # CHROMA_DB_ROOT_DIR='./chroma_db' # If different location needed
        ```
5.  **Apply Database Migrations:**
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```
6.  **Create Superuser (Optional, for Admin access):**
    ```bash
    python manage.py createsuperuser
    ```
7.  **Run the Development Server:**
    ```bash
    # Ensure Ollama is running separately
    uvicorn eduagent_project.asgi:application --reload --port 8000
    ```
    The API should now be available at `http://127.0.0.1:8000/`.

## Contributing

Contributions are welcome! Please follow standard fork-and-pull-request procedures. Ensure code adheres to basic PEP 8 standards and includes tests where applicable.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.