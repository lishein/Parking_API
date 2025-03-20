from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import json
import os
import redis
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=int(os.getenv("REDIS_DB", 0)),
    decode_responses=True
)

async def fetch_data():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://data.lillemetropole.fr/data/ogcapi/collections/ilevia:vlille_temps_reel/items?f=json&limit=50"
        )
        data = response.json()

        transformed_data = {
            "velos": [
                {
                    "nom": station["nom"],
                    "adresse": station["adresse"],
                    "etat": station["etat"],
                    "nb_velos_dispo": station["nb_velos_dispo"],
                    "nb_places_dispo": station["nb_places_dispo"],
                    "x": station["x"],
                    "y": station["y"],
                    "date_modification": station["date_modification"]
                }
                for station in data["records"]
            ]
        }
        return transformed_data

@app.get("/api/stations")
async def get_stations():
    try:
        if cached_data := redis_client.get("stations"):
            return json.loads(cached_data)

        data = await fetch_data()
        redis_client.setex("stations", 120, json.dumps(data))
        return data

    except redis.RedisError as e:
        print(f"Redis error: {e}")
        return await fetch_data()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))