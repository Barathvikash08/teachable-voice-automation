import asyncio
import os
from dotenv import load_dotenv
from pymongo import AsyncMongoClient
import asyncio
from datetime import datetime, timezone

load_dotenv()

async def main():
    client = AsyncMongoClient(
        os.getenv("MONGO_URI"),
        serverSelectionTimeoutMS=10000
    )
    try:
        await client.admin.command("ping")
        print("MongoDB connection successful!")
    except Exception as e:
        print("MongoDB connection failed:")
        print(e)
    finally:
        await client.close()

asyncio.run(main())