# RAG-WhiteForrest
A standalone project for document injection creating VectorDB with RAG based AI assistant
# Nova KI Assistant – Energy Transition

A privacy-focused AI assistant built for **municipal administrations** to help with energy transition, heat planning, and local document management.

The project was developed during the **Black Forest Hackathon** and is designed to run completely on a local machine, keeping sensitive municipal information within the local network.

## Features

- **AI Chat with RAG:** Ask questions and get answers based on uploaded municipal documents.
- **Document Upload:** Upload PDFs, guidelines, city plans, and other local documents.
- **Automatic Document Processing:** Extract information from PDFs, Word files, and Excel files.
- **Template Assistance:** Analyze and help complete administrative templates.
- **Source References:** Answers include references to the documents used to generate them.
- **Local & Private:** Uses locally running AI models, so sensitive information is not sent to external cloud services.

## Technology Used

### Backend
- Python 3.11+
- FastAPI
- LangChain
- LangGraph
- ChromaDB
- Uvicorn
- PyPDF / pdfplumber
- python-docx
- openpyxl

### Frontend
- React 19
- TypeScript
- Vite
- React Router
- Axios
- Lucide React

### AI
- Ollama for running AI models locally
- Mistral for conversations
- Nomic Embed Text for document embeddings

## How It Works

1. Municipal documents are uploaded to the system.
2. The documents are processed and divided into smaller sections.
3. The sections are converted into embeddings and stored in a local vector database.
4. When a user asks a question, the system searches the relevant documents.
5. The AI generates an answer using the retrieved information.
6. The answer includes document references so users can verify the information.

## Requirements

Before running the project, install:

- Windows
- Python 3.11 or newer
- Node.js 20 or newer
- Ollama

## Setup

### 1. Set Up Ollama

Start Ollama and download the required models:

```bash
ollama serve
ollama pull mistral
ollama pull nomic-embed-text
```

### 2. Start the Backend

Open a terminal and go to the backend folder:

```bash
cd municipal-ai-assistant/backend
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

Install the required Python packages:

```bash
pip install -r requirements.txt
```

Start the FastAPI server:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The backend will be available at:

`http://localhost:8000`

API documentation:

`http://localhost:8000/docs`

### 3. Start the Frontend

Open another terminal:

```bash
cd municipal-ai-assistant/frontend
```

Install the dependencies:

```bash
npm install
```

Start the frontend:

```bash
npm run dev
```

The application will normally be available at:

`http://localhost:5173`

## Configuration

The main backend configuration is available in:

```text
backend/config.py
```

You can also create a `.env` file:

```env
OLLAMA_BASE_URL=http://localhost:11434
CHAT_MODEL=mistral
EMBEDDING_MODEL=nomic-embed-text
```

## Project Structure

```text
BlackForestHackathon/
│
├── municipal-ai-assistant/
│   ├── backend/
│   │   ├── data/
│   │   ├── main.py
│   │   ├── agent.py
│   │   ├── ingestion.py
│   │   ├── rag_chain.py
│   │   └── requirements.txt
│   │
│   └── frontend/
│       ├── src/
│       ├── index.html
│       ├── package.json
│       └── vite.config.ts
│
└── setup_data.ps1
```

## Troubleshooting

If the application does not start:

- Make sure Ollama is running.
- Check that the required models are installed.
- Make sure the Python virtual environment is activated.
- Check that the backend is running on port `8000`.
- Make sure `npm install` completed successfully.
- Check that the frontend is running on port `5173`.

## Privacy

The application is designed with **privacy and local data processing** in mind. AI models and document processing run locally using Ollama, reducing the need to send sensitive municipal documents to external services.

## License

This project is released under the **MIT License**.








