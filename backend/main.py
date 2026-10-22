from fastapi import FastAPI
from pymongo import AsyncMongoClient
from dotenv import load_dotenv
import os
import asyncio
from datetime import datetime, timezone
import winsound
import subprocess
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

active_timers = set()

load_dotenv()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from voice_control import start_edge, open_application, close_application


class BrowserCommand(BaseModel):
    command: str


@app.post("/browser/command")
def browser_command(data: BrowserCommand):
    command = data.command.strip().lower()

    if not command:
        return {"success": False, "message": "Please enter a command."}

    if not start_edge():
        return {
            "success": False,
            "message": "Could not start Microsoft Edge."
        }

    if close_application(command):
        return {"success": True, "message": f"Executed: {command}"}

    if open_application(command):
        return {"success": True, "message": f"Executed: {command}"}

    return {
        "success": False,
        "message": "Command not recognized. Try 'open youtube' or 'search google for Java tutorials'."
    }


client = AsyncMongoClient(os.getenv("MONGO_URI"))

db = client["teachable_voice"]
workflows_collection = db["workflows"]
history_collection = db["command_history"]


@app.get("/")
async def home():
    return {"message": "Teachable Voice Automation Backend is running!"}


@app.post("/workflow")
async def create_workflow(name: str, action: str, value: int):
    workflow = {
        "name": name,
        "action": action,
        "value": value
    }

    await workflows_collection.insert_one(workflow)

    return {
        "message": "Workflow saved to MongoDB",
        "name": name,
        "action": action,
        "value": value
    }


@app.get("/workflow")
async def get_workflows():
    workflows = []

    async for workflow in workflows_collection.find():
        workflow["_id"] = str(workflow["_id"])
        workflows.append(workflow)

    return workflows




async def finish_timer(name: str, minutes: int):
    try:
        print(f"Timer '{name}' started for {minutes} minutes")

        await asyncio.sleep(minutes * 60)

        finished_at = datetime.now(timezone.utc).isoformat()
        print(f"Timer '{name}' finished at {finished_at}")

        await history_collection.insert_one({
            "name": name,
            "action": "start_timer",
            "value": minutes,
            "status": "completed",
            "message": f"Timer '{name}' finished successfully",
            "timestamp": datetime.now(timezone.utc),
            "finished_at": finished_at
        })

        winsound.Beep(1000, 1000)

        message = f"Hey! Your {name} timer has finished."
        speech_script = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$s.Speak($env:TIMER_MESSAGE)"
        )

        env = os.environ.copy()
        env["TIMER_MESSAGE"] = message

        subprocess.run(
            ["powershell", "-NoProfile", "-Command", speech_script],
            env=env,
            check=False
        )

    finally:
        active_timers.discard(name)


@app.post("/workflow/run")
async def run_workflow(name: str):
    workflow = await workflows_collection.find_one(
    {"name": name},
    sort=[("_id", -1)]
    )

    if not workflow:
        await history_collection.insert_one({
            "name": name,
            "status": "failed",
            "message": "Workflow not found",
            "timestamp": datetime.utcnow()
        })
        return {"message": "Workflow not found"}

    action = workflow.get("action")
    value = workflow.get("value")

    if action == "start_timer":
        minutes = value

        if name in active_timers:
            return {
                "message": f"Timer '{name}' is already running"
            }

        if not isinstance(minutes, (int, float)) or minutes <= 0:
            await history_collection.insert_one({
                "name": name,
                "action": action,
                "value": minutes,
                "status": "failed",
                "message": "Timer duration must be greater than zero",
                "timestamp": datetime.utcnow()
            })
            return {"message": "Timer duration must be greater than zero"}

        active_timers.add(name)
        asyncio.create_task(finish_timer(name, minutes))

        await history_collection.insert_one({
            "name": name,
            "action": action,
            "value": minutes,
            "status": "success",
            "message": f"Timer started for {minutes} minutes",
            "timestamp": datetime.utcnow()
        })

        return {
            "message": f"Timer started for {minutes} minutes",
            "action": "start_timer",
            "value": minutes
        }

    if action == "study_mode":
        minutes = value if isinstance(value, (int, float)) else 45

        if minutes <= 0:
            return {"message": "Study duration must be greater than zero"}

        if name in active_timers:
            return {"message": f"Timer '{name}' is already running"}

        active_timers.add(name)
        asyncio.create_task(finish_timer(name, minutes))

        await history_collection.insert_one({
            "name": name,
            "action": action,
            "value": minutes,
            "status": "success",
            "message": f"Study mode started with a {minutes}-minute timer",
            "timestamp": datetime.utcnow()
        })

        return {
            "message": f"Study mode started with a {minutes}-minute timer",
            "action": "study_mode",
            "value": minutes
        }

    await history_collection.insert_one({
        "name": name,
        "action": action,
        "value": value,
        "status": "failed",
        "message": "Unknown action",
        "timestamp": datetime.utcnow()
    })

    return {"message": "Unknown action"}

@app.get("/history")
async def get_command_history():
    history = []

    async for item in history_collection.find().sort("_id", -1).limit(50):
        item["_id"] = str(item["_id"])
        history.append(item)

    return {"history": history}

@app.get("/history/{name}")
async def get_workflow_history(name: str):
    history = []

    async for item in history_collection.find(
        {"name": name}
    ).sort("_id", -1).limit(50):
        item["_id"] = str(item["_id"])
        history.append(item)

    return {
        "name": name,
        "history": history
    }

