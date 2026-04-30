import asyncio
from app.core.database import AsyncSessionFactory
from app.models.models import License
from sqlalchemy import select

async def main():
    async with AsyncSessionFactory() as db:
        r = await db.execute(select(License))
        for l in r.scalars():
            print(f"{l.key}: machine_id={l.machine_id}, active={l.active}")

asyncio.run(main())
