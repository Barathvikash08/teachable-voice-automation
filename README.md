# Teachable Voice Automation

A Python-based voice automation project that lets users control browser actions, launch supported applications, manage timers, and run saved workflows using voice commands or a web dashboard.

## Features

- **Voice commands:** Recognizes spoken commands through a microphone.
- **Browser automation:** Opens websites, searches Google and YouTube, and manages browser tabs.
- **Smart timer:** Runs timers in the background and provides an audible and spoken alert when they finish.
- **Study Mode:** Starts a study workflow with supported browser actions and volume adjustment.
- **Web dashboard:** Provides a simple interface to send browser commands.
- **Workflow API:** Uses FastAPI to save and execute workflows.
- **MongoDB integration:** Stores workflows and records execution history.

## Tech Stack

- Python
- FastAPI and Uvicorn
- MongoDB Atlas with PyMongo
- SpeechRecognition
- Playwright
- Requests
- Pycaw
- HTML, CSS and JavaScript

## Requirements

- Windows 10 or Windows 11
- Python 3.10 or newer
- Microsoft Edge
- A working microphone for voice commands
- A MongoDB Atlas database and connection URI

## Project Structure

```text
tech-automation/
├── backend/
│   ├── main.py
│   ├── voice_control.py
│   ├── test_mongo.py
│   └── requirements.txt
├── frontend/
│   └── index.html
├── .gitignore
└── README.md
```

## Setup

### 1. Clone the repository

```powershell
git clone YOUR_GITHUB_REPOSITORY_URL
cd tech-automation
```

Replace `YOUR_GITHUB_REPOSITORY_URL` with your repository's actual URL.

### 2. Create and activate a virtual environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, open a PowerShell terminal and use this temporary, terminal-session-only workaround:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r backend\requirements.txt
```

If microphone support fails because PyAudio cannot install on your system, resolve that dependency before testing voice recognition.

### 4. Configure environment variables

Create a `.env` file inside the `backend` directory and add your own MongoDB connection URI:

```text
MONGO_URI=YOUR_MONGODB_CONNECTION_URI
```

Replace the placeholder with your actual URI. Never commit `.env` or publish database credentials.

Make sure your MongoDB Atlas network access and database permissions are configured appropriately.

## Running the Project

Keep each service running in its own VS Code terminal.

### Terminal 1: Start the backend

```powershell
cd backend
python -m uvicorn main:app --reload --port 8000
```

API documentation:

http://127.0.0.1:8000/docs

### Terminal 2: Start the dashboard

From the project root:

```powershell
python -m http.server 5500 --directory frontend
```

Open the dashboard:

http://127.0.0.1:5500/

### Terminal 3: Start voice control

Activate the project's virtual environment, then run:

```powershell
cd backend
python voice_control.py
```

Run the voice assistant only after the backend is available.

## Example Commands

Commands depend on the features currently configured in the project. Examples include:

- "Search Java tutorials on YouTube"
- "Open YouTube"
- "Switch tab"
- "Start a timer for one minute"
- "Start study mode"
- "Stop listening"

## API Endpoints

The FastAPI application includes endpoints for:

- Checking backend status
- Saving and listing workflows
- Executing workflows
- Viewing execution history

Visit `/docs` on the local backend to inspect the current API routes and request formats.

## Security Notes

- Never commit `.env`, MongoDB URIs, passwords, API keys, or other secrets.
- Keep `venv/` and Python cache files out of version control.
- Use a restricted MongoDB database account rather than unnecessarily broad permissions.
- Review all files before pushing the repository to GitHub.

## Current Status

The project has working voice-command, browser-control, timer, Study Mode, dashboard, and workflow features that have been tested locally. Further improvements can focus on error handling, automated tests, documentation, and cross-system compatibility.

## Author

Developed as a personal Python automation project.