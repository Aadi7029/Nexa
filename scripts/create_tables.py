# scripts/create_tables.py
import asyncio
import sys
from pathlib import Path
import os

# Ensure project root is on sys.path so absolute imports work when running
# this script directly (e.g. `python scripts/create_tables.py`).
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
# Ensure the current working directory is the repo root so tools like pydantic
# that look for an `.env` file will find it when this script is run from
# `scripts/` or other subdirectories.
os.chdir(repo_root)

from app.db.models import Base
from app.db.session import engine

async def create():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    asyncio.run(create())
