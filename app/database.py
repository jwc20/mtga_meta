import aiosqlite
import logging
from typing import Annotated

from fastapi import Depends

from app.config import db_path, schema_path

logger = logging.getLogger(__name__)

async def get_db():
    conn = await aiosqlite.connect(db_path, check_same_thread=False)
    conn.row_factory = aiosqlite.Row
    return conn


async def get_db_conn():
    conn = await get_db()
    try:
        yield conn
    finally:
        await conn.close()


DBConnDep = Annotated[aiosqlite.Connection, Depends(get_db_conn)]


async def init_db():
    conn = await get_db()
    logger.info("Initializing database from schema.sql")
    cursor = await conn.cursor()
    try:
        with open(schema_path, "r") as f:
            await cursor.executescript(f.read())
        await conn.commit()
        logger.info("Database initialized from schema.sql")
        await conn.close()
    except Exception as e:
        print(f"Warning: Could not initialize database from schema.sql: {e}")