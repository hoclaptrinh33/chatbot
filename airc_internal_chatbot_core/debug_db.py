
import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient

# STANDALONE DEBUG SCRIPT
# Try env var (inside docker) or fallback to internal hostname
MONGO_URL = os.getenv("MONGODB_URL", "mongodb://mongodb:27017")
DB_NAME = os.getenv("MONGODB_DB_NAME", "airc_chatbot")

async def main():
    print(f"Connecting to {MONGO_URL} [{DB_NAME}]...")
    client = None
    db = None
    try:
        client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=3000)
        db = client[DB_NAME]
        await client.server_info()
        print("Connected to MongoDB!")
    except Exception as e:
        print(f"Failed to connect to {MONGO_URL}: {e}")
        # Build 2nd fallback for localhost if running on host
        print("Trying localhost...")
        MONGO_URL_LOCAL = "mongodb://localhost:27017"
        try:
           client = AsyncIOMotorClient(MONGO_URL_LOCAL, serverSelectionTimeoutMS=3000)
           db = client[DB_NAME]
           await client.server_info()
           print("Connected to Localhost MongoDB!")
        except Exception as e2:
           print(f"Failed localhost too: {e2}")
           return
        
    # 0. List Databases
    dbs = await client.list_database_names()
    print(f"Available Databases: {dbs}")
    
    # 1. Check Datasets in current DB
    print(f"\nChecking DB '{DB_NAME}'...")
    datasets = await db["datasets"].find({}).to_list(None)
    print(f"Found {len(datasets)} datasets:")
    
    dataset = None
    for d in datasets:
        print(f" - {d.get('name')} (ID: {d.get('_id')})")
        if d.get('name') == "datamining":
            dataset = d # Found it

    if not dataset:
        print("Dataset 'datamining' not found")
        dataset = await db["datasets"].find_one({}) # Get any
        if dataset:
            print(f"Using dataset '{dataset['name']}' instead")
        else:
            return

    ds_id = str(dataset["_id"])
    print(f"Dataset ID: {ds_id}")
    
    # 2. List Enabled Files
    print(f"\nListing enabled files for dataset {dataset['name']}...")
    files = await db["dataset_files"].find({"dataset_id": ds_id, "is_enabled": True}).to_list(None)
    print(f"Enabled Files: {len(files)}")
    for f in files:
        fname = f.get('name', 'UNKNOWN_NAME')
        fid = f.get('_id', 'UNKNOWN_ID')
        print(f" - {fname} (ID: {fid})")
    
    # 3. Check Chunks for first file
    if files:
        f0 = files[0]
        fname = f0.get('name', 'UNKNOWN_NAME')
        fid = str(f0.get('_id'))
        print(f"\nChecking chunks for file {fname} ({fid})...")
        chunks = await db["chunks"].find({"dataset_file_id": fid}).limit(5).to_list(None)
        print(f"Found {len(chunks)} chunks.")
        for c in chunks:
            print(f"--- Chunk {c.get('chunk_index')} ---")
            text = c.get('text', '')
            print(f"Text ({len(text)} chars): {text[:100]}...")
            
    # 4. Test Regex
    query = "Đề cương"
    print(f"\nTesting Regex Search for '{query}'...")
    import re
    safe = re.escape(query)
    count = await db["chunks"].count_documents({
        "dataset_id": ds_id,
        "text": {"$regex": safe, "$options": "i"}
    })
    print(f"Regex Matches: {count}")

if __name__ == "__main__":
    asyncio.run(main())
