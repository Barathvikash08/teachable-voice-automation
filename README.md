# Teachable Voice Automation 🎙️

A Python-based voice automation and productivity project that combines speech recognition, browser automation, a web dashboard, and workflow management to simplify everyday tasks.

## 🚀 Features

- **Voice Control:** Recognize spoken commands using speech recognition.
- **Browser Automation:** Open websites, search for content, and manage browser tabs.
- **Web Dashboard:** Submit commands through a browser-based interface and monitor backend status.
- **Productivity Timers:** Start timers with audio alerts and voice notifications.
- **Workflow Management:** Save and retrieve workflows using MongoDB Atlas.
- **Command History:** Retrieve previous automation activity.
- **REST API:** Manage workflows and automation commands through FastAPI endpoints.

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| Python | Core application logic |
| FastAPI | Backend API |
| MongoDB Atlas | Cloud database |
| PyMongo | MongoDB integration |
| SpeechRecognition | Voice input |
| Playwright | Browser automation |
| HTML, CSS, JavaScript | Dashboard interface |

## 📁 Project Structure

```text
tech-automation/
├── backend/
│   ├── main.py
│   ├── voice_control.py
│   ├── requirements.txt
│   └── test_mongo.py
├── frontend/
│   └── index.html
├── .gitignore
└── README.md
```

## ⚙️ Getting Started

### Prerequisites

- Python installed on Windows
- Microsoft Edge for browser automation
- A MongoDB Atlas account and database
- A working microphone for voice commands

### 1. Clone the repository

```bash
git clone https://github.com/Barathvikash08/teachable-voice-automation.git
cd teachable-voice-automation
```

### 2. Create a virtual environment

Run these commands from the project root in PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution, use an appropriate temporary execution-policy setting for the current session rather than changing the system-wide policy.

### 3. Install dependencies

```powershell
pip install -r backend/requirements.txt
```

### 4. Configure MongoDB

Create a `.env` file in the project root:

```text
MONGO_URI=your_mongodb_connection_string
```

Replace the placeholder with your own MongoDB Atlas connection string.

**Never commit your actual `.env` file or expose database credentials.** Configure your Atlas network access and database permissions appropriately.

### 5. Start the backend

Open a terminal from the project root:

```powershell
cd backend
python -m uvicorn main:app --reload --port 8000
```

The backend should be available at:

- API: http://127.0.0.1:8000/
- Interactive API documentation: http://127.0.0.1:8000/docs

### 6. Start the dashboard

Open a second terminal from the project root:

```powershell
python -m http.server 5500 --directory frontend
```

Visit http://127.0.0.1:5500/ in your browser.

### 7. Run voice control

Open a third terminal:

```powershell
cd backend
..\venv\Scripts\Activate.ps1
python voice_control.py
```

Allow microphone access where required and try a supported command.

## 🔐 Security

- Keep credentials in environment variables.
- Exclude `.env` files and virtual environments from version control.
- Never publish database passwords, API keys, or private connection strings.
- Use appropriate MongoDB Atlas network restrictions and database permissions.

## 🎯 Project Goals

This project explores practical applications of voice-controlled automation, REST API development, database integration, browser interaction, and productivity tooling.

## 🔮 Future Improvements

- Improve command recognition and error handling.
- Expand automated testing.
- Improve dashboard feedback and usability.
- Add clearer setup and troubleshooting documentation.
- Package the application for easier installation.

## 👨‍💻 Author

**Barath Vikash**

GitHub: [Barathvikash08](https://github.com/Barathvikash08)

---

*Built as a learning project to explore Python automation and full-stack
