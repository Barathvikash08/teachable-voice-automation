# Teachable Voice Automation 🎙️

A Python-based voice automation project that lets users control browser actions and productivity timers through voice commands and a web dashboard.

## 🚀 Features

- **Voice Commands:** Recognizes spoken commands using speech recognition.
- **Browser Automation:** Opens websites, searches for content, and manages browser tabs.
- **Web Dashboard:** Provides an interface for entering commands and monitoring backend status.
- **Smart Timer:** Starts productivity timers with audio and voice notifications.
- **Workflow Management:** Saves and retrieves workflows using MongoDB.
- **Command History:** Displays previous automation activity.

## 🛠️ Tech Stack

- Python
- FastAPI
- MongoDB Atlas
- PyMongo
- SpeechRecognition
- Playwright
- HTML, CSS, and JavaScript

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

## ⚙️ Setup

### 1. Clone the repository

```bash
git clone https://github.com/Barathvikash08/teachable-voice-automation.git
cd teachable-voice-automation
```

### 2. Create and activate a virtual environment

On Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r backend/requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root and add your MongoDB connection string:

```text
MONGO_URI=your_mongodb_connection_string
```

Replace the placeholder with your own connection string. Never commit your actual `.env` file.

### 5. Start the backend

```powershell
cd backend
python -m uvicorn main:app --reload --port 8000
```

Open `http://127.0.0.1:8000/docs` to view the API documentation.

### 6. Start the dashboard

Open another terminal from the project root:

```powershell
python -m http.server 5500 --directory frontend
```

Open `http://127.0.0.1:5500/` in your browser.

### 7. Run voice control

In another terminal, navigate to `backend`, activate the virtual environment if needed, and run:

```powershell
python voice_control.py
```

Allow microphone access when prompted and try a supported voice command.

## 🔐 Security

- Keep credentials in environment variables.
- Do not commit `.env` files or secrets.
- Restrict database access using appropriate MongoDB Atlas network and database permissions.

## 🎯 Project Goal

This project explores voice-controlled desktop and browser automation, API development, database integration, and productivity tools using Python.

## 👨‍💻 Author

**Barath Vikash**

GitHub: [Barathvikash08](https://github.com/Barathvikash08)
