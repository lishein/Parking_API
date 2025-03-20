from flask import Flask, jsonify, redirect
from flask_cors import CORS
import httpx
import json
import os
import redis
import asyncio
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=int(os.getenv("REDIS_DB", 0)),
    decode_responses=True
)


async def fetch_data():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://data.lillemetropole.fr/geoserver/wfs?service=WFS&version=1.0.0&request=GetFeature&typeName=mel_mobilite_et_transport:parking&outputFormat=application/json"
        )
        data = response.json()

        transformed_data = {
            "parkings": [
                {
                    "nom": parking["properties"].get("nom", "N/A"),
                    "adresse": parking["properties"].get("adresse", "N/A"),
                    "nbr_libre": parking["properties"].get("nbr_libre", 0),
                    "longitude": parking["geometry"]["coordinates"][0],
                    "latitude": parking["geometry"]["coordinates"][1]
                }
                for parking in data.get("features", [])
            ]
        }
        return transformed_data


@app.route('/')
def index():
    return redirect('/parkings')


@app.route('/parkings')
def get_parkings():
    try:
        if cached_data := redis_client.get("parkings"):
            return jsonify(json.loads(cached_data))

        data = asyncio.run(fetch_data())
        redis_client.setex("stations", 120, json.dumps(data))
        return jsonify(data)

    except redis.RedisError as e:
        print(f"Redis error: {e}")
        return jsonify(asyncio.run(fetch_data()))

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)