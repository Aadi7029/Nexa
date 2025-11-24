# test_conn.py
import asyncio
import asyncpg
from urllib.parse import urlparse

async def main():
    url = "postgresql+asyncpg://user:roshan@passwd123:5432/dbname"  # << replace this with your resolved URL (use raw password)
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://","postgresql://")
    p = urlparse(url)
    try:
        conn = await asyncpg.connect(host=p.hostname, port=p.port or 5432,
                                     user=p.username, password=p.password, database=p.path.lstrip('/'))
        print("CONNECTED OK")
        await conn.close()
    except Exception as e:
        print("CONNECT ERROR:", type(e).__name__, str(e))

asyncio.run(main())
