# 🏛️ Nova KI-Assistent – Energiewende

Ein vollständig lokaler KI-Assistent für kommunale Verwaltungen zur Unterstützung
bei der Energiewende, Wärmeplanung und lokalen Dokumenten.

## Was das Projekt macht

- Chat mit dokumentbasierter Unterstützung
- Dokumente lokal hochladen und indizieren
- Vorlagen (PDF/DOCX/XLSX) analysieren und ausfüllen
- Antworten mit Quellenangaben liefern
- Alles lokal und DSGVO-freundlich

## Voraussetzungen

- Windows
- Python 3.11+
- Node.js 20+
- Ollama installiert

## Schritt 1: Ollama vorbereiten

1. Starte Ollama:

```powershell
ollama serve
```

2. Lade Modelle herunter:

```powershell
ollama pull mistral
ollama pull nomic-embed-text
```

## Schritt 2: Backend starten

```powershell
cd municipal-ai-assistant/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- Backend: `http://localhost:8000`
- API-Dokumentation: `http://localhost:8000/docs`

## Schritt 3: Frontend starten

```powershell
cd municipal-ai-assistant/frontend
npm install
npm run dev
```

- Frontend: `http://localhost:5173`

## Optionale Setup-Schritte

### Hackathon-Daten installieren

Wenn Sie die vorhandenen Hackathon-Dokumente kopieren möchten, führen Sie im Workspace-Root aus:

```powershell
cd d:\BlackForestHackathon
.\setup_data.ps1
```

Das Skript kopiert Dokumente in:
- `municipal-ai-assistant/backend/data/knowledge_base`
- `municipal-ai-assistant/backend/data/additional_documents`
- `municipal-ai-assistant/backend/data/templates`

## Verzeichnisstruktur

```
municipal-ai-assistant/backend/data/
├── knowledge_base/
├── additional_documents/
├── templates/
├── uploads/
├── filled_templates/
└── chroma_db/
```

## Konfiguration

Die Backend-Konfiguration befindet sich in `municipal-ai-assistant/backend/config.py`.

Optional können Sie eine Datei `municipal-ai-assistant/backend/.env` anlegen:

```env
OLLAMA_BASE_URL=http://localhost:11434
CHAT_MODEL=mistral
EMBEDDING_MODEL=nomic-embed-text
```

## Hinweise

- Ollama muss vor dem Backend laufen.
- Der Backend-Server muss auf `http://localhost:8000` erreichbar sein.
- Unterstützte Dokumenttypen: PDF, DOCX, XLSX, XLS.

## Kurzbefehle

```powershell
# Backend
cd municipal-ai-assistant/backend
.venv\Scripts\activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd municipal-ai-assistant/frontend
npm install
npm run dev
```

## Support

Falls es beim Starten Probleme gibt, prüfen Sie:
- dass Ollama läuft
- ob die Python-Umgebung aktiviert ist
- ob `npm install` erfolgreich war
- ob der Browser auf `http://localhost:5173` zugreift
