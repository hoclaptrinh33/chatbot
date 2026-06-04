import asyncio
from app.core import get_database
from app.core.database import connect_to_mongo, mongodb

async def main():
    await connect_to_mongo()
    db = mongodb.db
    cnt = await db.sessions.count_documents({})
    auth = db.client['airc_auth_db']
    usr = await auth.users.count_documents({})
    print(f"Sessions: {cnt}, Users: {usr}")

if __name__ == "__main__":
    asyncio.run(main())
