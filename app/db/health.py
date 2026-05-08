from sqlalchemy import text

from app.db.session import AsyncSessionLocal


async def check_db() -> bool:
    """Ping the database with SELECT 1. Returns True if reachable, False otherwise."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
