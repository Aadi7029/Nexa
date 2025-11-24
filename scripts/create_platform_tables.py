# scripts/create_platform_tables.py
import asyncio
import sys
from pathlib import Path
import os

# Ensure project root is on sys.path and working directory is the repo root so
# absolute imports and .env loading work when running this script from
# `scripts/` or other subfolders.
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
os.chdir(repo_root)

from app.db.models import Base
from app.db.session import engine

async def create():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    asyncio.run(create())
