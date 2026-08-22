import asyncio
import certifi
from motor.motor_asyncio import AsyncIOMotorClient

async def test_mongo():
    uri = "mongodb+srv://edixiostudio_db_user:p4U2MZldySb07Kc9@cluster0.msmfdxr.mongodb.net/?appName=Cluster0"
    
    try:
        client = AsyncIOMotorClient(uri, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=5000)
        res = await client.admin.command('ping')
        print("SUCCESS! Connected to MongoDB Atlas with certifi! Ping result:", res)
        return True
    except Exception as e:
        print("Certifi connection failed:", e)
        return False

if __name__ == "__main__":
    asyncio.run(test_mongo())
