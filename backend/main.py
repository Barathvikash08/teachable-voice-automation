
from datetime import datetime, timezone
import asyncio
import os
import subprocess

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from pymongo import AsyncMongoClient
import winsound

load_dotenv()

active_timers = set()

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

from voice_control import (
    start_edge,
    open_application,
    close_application,
    switch_tab,
    browser_navigation,
    control_volume,
    extract_minutes,
)

client = AsyncMongoClient(os.getenv("MONGO_URI"))

db = client["teachable_voice"]
workflows_collection = db["workflows"]
history_collection = db["command_history"]


class BrowserCommand(BaseModel):
    command: str


@app.get("/")
async def home():
    return {
        "message": "Teachable Voice Automation Backend is running!"
    }



@app.post("/browser/command")
async def browser_command(data: BrowserCommand):
    command = data.command.strip().lower()

    if not command:
        return {
            "success": False,
            "message": "Please enter a command.",
        }

    if not await run_in_threadpool(start_edge):
        return {
            "success": False,
            "message": "Could not start Microsoft Edge.",
        }

    handlers = (
        close_application,
        switch_tab,
        browser_navigation,
        control_volume,
        open_application,
    )

    for handler in handlers:
        handled = await run_in_threadpool(handler, command)

        if handled:
            return {
                "success": True,
                "message": f"Command handled: {command}",
            }

    return {
        "success": False,
        "message": (
            "Command not recognized. Try 'open youtube', "
            "'open github', 'open google', or "
            "'search google for Java tutorials'."
        ),
    }

@app.post("/workflow")
async def create_workflow(name: str, action: str, value: int):
    workflow = {
        "name": name,
        "action": action,
        "value": value,
    }

    await workflows_collection.insert_one(workflow)

    return {
        "message": "Workflow saved to MongoDB",
        "name": name,
        "action": action,
        "value": value,
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

        finished_at = datetime.now(timezone.utc)

        await history_collection.insert_one({
            "name": name,
            "action": "start_timer",
            "value": minutes,
            "status": "completed",
            "message": f"Timer '{name}' finished successfully",
            "timestamp": finished_at,
            "finished_at": finished_at.isoformat(),
        })

        winsound.Beep(1000, 1000)

        message = f"Hey! Your {name} timer has finished."

        speech_script = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object "
            "System.Speech.Synthesis.SpeechSynthesizer; "
            "$s.Speak($env:TIMER_MESSAGE)"
        )

        env = os.environ.copy()
        env["TIMER_MESSAGE"] = message

        subprocess.run(
            ["powershell", "-NoProfile", "-Command", speech_script],
            env=env,
            check=False,
        )

    except Exception as error:
        print(f"Timer error for '{name}': {error}")

        await history_collection.insert_one({
            "name": name,
            "status": "failed",
            "message": str(error),
            "timestamp": datetime.now(timezone.utc),
        })

    finally:
        active_timers.discard(name)


@app.post("/workflow/run")
async def run_workflow(name: str):
    workflow = await workflows_collection.find_one(
        {"name": name},
        sort=[("_id", -1)],
    )

    if not workflow:
        await history_collection.insert_one({
            "name": name,
            "status": "failed",
            "message": "Workflow not found",
            "timestamp": datetime.now(timezone.utc),
        })

        return {"message": "Workflow not found"}

    action = workflow.get("action")
    minutes = workflow.get("value")

    if action not in ("start_timer", "study_mode"):
        await history_collection.insert_one({
            "name": name,
            "action": action,
            "value": minutes,
            "status": "failed",
            "message": "Unknown action",
            "timestamp": datetime.now(timezone.utc),
        })

        return {"message": "Unknown action"}

    if (
        not isinstance(minutes, (int, float))
        or isinstance(minutes, bool)
        or minutes <= 0
    ):
        return {
            "message": "Timer duration must be greater than zero"
        }

    if name in active_timers:
        return {
            "message": f"Timer '{name}' is already running"
        }

    active_timers.add(name)
    asyncio.create_task(finish_timer(name, minutes))

    await history_collection.insert_one({
        "name": name,
        "action": action,
        "value": minutes,
        "status": "success",
        "message": f"{name} started for {minutes} minutes",
        "timestamp": datetime.now(timezone.utc),
    })

    return {
        "message": f"{name} started for {minutes} minutes",
        "action": action,
        "value": minutes,
    }


async def start_mode_timer(name: str):
    if name in active_timers:
        return {
            "success": True,
            "message": f"{name} is already running.",
        }

    await workflows_collection.update_one(
        {"name": name},
        {
            "$set": {
                "action": "start_timer",
                "value": 30,
            }
        },
        upsert=True,
    )

    result = await run_workflow(name)

    return {
        "success": "action" in result,
        "message": result.get(
            "message",
            "Timer command processed.",
        ),
    }


@app.post("/command/execute")
async def execute_command(data: BrowserCommand):
    command = data.command.strip().lower()

    if not command:
        return {
            "success": False,
            "message": "Please say or enter a command.",
        }

    try:
        # STUDY MODE
        if command in (
            "start study mode",
            "study mode",
            "begin study mode",
        ):
            if not await run_in_threadpool(start_edge):
                return {
                    "success": False,
                    "message": "Could not start Edge automation.",
                }

            opened = await run_in_threadpool(
                open_application, "open youtube"
            )

            if not opened:
                return {
                    "success": False,
                    "message": "Could not open YouTube.",
                }

            volume_result = await run_in_threadpool(
                control_volume, "set volume to 80%"
            )

            timer_result = await start_mode_timer("Study Mode")

            return {
                "success": timer_result["success"],
                "message": (
                    "Study Mode: YouTube opened. "
                    f"Volume command result: {volume_result}. "
                    f"{timer_result['message']}"
                ),
            }

        # CODE MODE: LEETCODE
        elif command in (
            "start code mode",
            "code mode",
            "start coding mode",
            "coding mode",
        ):
            if not await run_in_threadpool(start_edge):
                return {
                    "success": False,
                    "message": "Could not start Edge automation.",
                }

            opened = await run_in_threadpool(
                open_application, "open leetcode"
            )

            if not opened:
                return {
                    "success": False,
                    "message": (
                        "Could not open LeetCode. "
                        "Check the website mapping in voice_control.py."
                    ),
                }

            timer_result = await start_mode_timer("Code Mode")

            return {
                "success": timer_result["success"],
                "message": (
                    "Code Mode: LeetCode opened. "
                    f"{timer_result['message']} Volume unchanged."
                ),
            }

        # CUSTOM TIMER
        if "timer" in command:
            minutes = extract_minutes(command)

            if minutes is None or minutes <= 0:
                return {
                    "success": False,
                    "message": (
                        "Say a duration, for example: "
                        "start a timer for five minutes."
                    ),
                }

            name = f"Website Timer {minutes} minutes"

            await workflows_collection.update_one(
                {"name": name},
                {
                    "$set": {
                        "action": "start_timer",
                        "value": minutes,
                    }
                },
                upsert=True,
            )

            result = await run_workflow(name)

            return {
                "success": "action" in result,
                "message": result.get(
                    "message",
                    "Timer command processed.",
                ),
            }

        # EXISTING COMMAND HANDLERS
        if not await run_in_threadpool(start_edge):
            return {
                "success": False,
                "message": "Could not start Edge automation.",
            }

        handlers = (
            close_application,
            switch_tab,
            browser_navigation,
            control_volume,
            open_application,
        )

        for handler in handlers:
            handled = await run_in_threadpool(handler, command)

            if handled:
                return {
                    "success": True,
                    "message": f"Command handled: {command}",
                }

        return {
            "success": False,
            "message": (
                "Command not recognised. Try 'start study mode', "
                "'start code mode', 'open youtube', "
                "or 'start a timer for five minutes'."
            ),
        }

    except Exception as error:
        return {
            "success": False,
            "message": f"Command failed: {error}",
        }


@app.get("/history")
async def get_command_history():
    history = []

    async for item in (
        history_collection.find().sort("_id", -1).limit(50)
    ):
        item["_id"] = str(item["_id"])
        history.append(item)

    return {"history": history}


@app.get("/history/{name}")
async def get_workflow_history(name: str):
    history = []

    async for item in (
        history_collection.find({"name": name})
        .sort("_id", -1)
        .limit(50)
    ):
        item["_id"] = str(item["_id"])
        history.append(item)

    return {
        "name": name,
        "history": history,
    }
