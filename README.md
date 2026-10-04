# RAG-WhiteForrest
A standalone project for document injection creating VectorDB with RAG based AI assistant
Nova KI-Assistent - Energiewende (Black Forest Hackathon)
License Python Node React FastAPI

A fully local, privacy-first (GDPR-compliant) AI assistant designed for municipal administrations. Created as part of the Black Forest Hackathon, this tool supports city officials with the energy transition (Energiewende), heat planning, and local document management.

Key Features
Conversational AI with RAG: Chat with a document-backed AI assistant tailored to municipal data.
Local Document Ingestion: Upload and index local guidelines, PDFs, and city plans securely.
Template Automation: Automatically analyze and fill out administrative templates (PDF, DOCX, XLSX).
Source Citations: Answers are backed by source citations to ensure accuracy and trace-back capability.
100% Local & Privacy-First: Runs entirely on your local machine using Ollama, meaning no sensitive data ever leaves the municipal network.
Tech Stack
Backend

Python 3.11+
FastAPI & Uvicorn (REST API)
LangChain & LangGraph (LLM Orchestration & Agents)
ChromaDB (Local Vector Store)
PyPDF, pdfplumber, python-docx, openpyxl (Document Parsing)
Frontend

React 19 & Vite
TypeScript
React Router & Axios
Lucide React (Icons)
AI & Embeddings

Ollama (Local LLM Execution)
Models: mistral (Chat) and nomic-embed-text (Embeddings)
Prerequisites
Before starting, ensure you have the following installed on your machine (Windows is recommended/supported as per original setup):

Windows OS
Python 3.11+
Node.js 20+
Ollama installed and running
Installation & Setup
Step 1: Prepare Local LLM (Ollama)
The system relies on local models. Start the Ollama service and pull the required models:

# 1. Start Ollama (in a separate terminal)
ollama serve

# 2. Pull the required models
ollama pull mistral
ollama pull nomic-embed-text
Step 2: Start the Backend (FastAPI)
Open a new terminal and navigate to the backend directory:

cd municipal-ai-assistant/backend

# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the API server
uvicorn main:app --reload --host 0.0.0.0 --port 8000


Backend API URL: http://localhost:8000
Swagger Documentation: http://localhost:8000/docs
Step 3: Start the Frontend (React/Vite)
Open another terminal and navigate to the frontend directory:

cd municipal-ai-assistant/frontend

# Install node modules
npm install

# Start the development server
npm run dev

Frontend App: http://localhost:5173
Configuration
Backend configuration is managed in municipal-ai-assistant/backend/config.py.

Optionally, you can create a .env file in the municipal-ai-assistant/backend/ directory to override defaults:

OLLAMA_BASE_URL=http://localhost:11434
CHAT_MODEL=mistral
EMBEDDING_MODEL=nomic-embed-text
Repository Structure
BlackForestHackathon
 |- municipal-ai-assistant/
 |  |- backend/
 |  |  |- data/          # Uploads, templates, and chroma_db vectors
 |  |  |- main.py        # FastAPI application entry point
 |  |  |- agent.py       # LangGraph/LangChain agent definitions
 |  |  |- ingestion.py   # Document parsing and embedding logic
 |  |  |- rag_chain.py   # Retrieval-Augmented Generation logic
 |  |  |- requirements.txt
 |  |- frontend/
 |  |  |- src/           # React components, pages, and API hooks
 |  |  |- index.html
 |  |  |- package.json
 |  |  |- vite.config.ts
 |- setup_data.ps1     # Data initialization script
 |- README.md
Troubleshooting
If you encounter issues during startup:

Ensure Ollama is actively running in the background.

Verify the Python virtual environment (.venv) is activated when running the backend.

Check that the backend is successfully listening on port 8000.

Ensure npm install completed without errors in the frontend folder.
