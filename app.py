from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse
import sqlite3
import os
import logging
from slack_sdk import WebClient
from mangum import Mangum

# Configure global logging
logging.basicConfig(
    level=logging.INFO,  # Set to DEBUG for more detailed logs
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)  # Use module-level logger

# Initialize FastAPI and other globals
app = FastAPI()
DATABASE_FILE = 'ottoneu_player_url.db'

SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
if not SLACK_BOT_TOKEN:
    logger.warning("SLACK_BOT_TOKEN is not set!")
slack_client = WebClient(token=SLACK_BOT_TOKEN)


def get_player_url(name):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    query = f"SELECT * FROM ottoneu_players where name LIKE ('%{name}%') LIMIT 8"
    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()

    return [{"name": row[0], 'pos': row[1], "url": row[2]} for row in results]


@app.post("/slack/player_url")
async def handle_slash_command(
        text: str = Form(...),
        channel_id: str = Form(...),
):
    print(f"Handling Slash Command - Text: {text}, Channel: {channel_id}")

    try:
        players = get_player_url(text)
        if not players:
            print("No players found.")
            return JSONResponse(content={"text": "No players found."})

        formatted_players = "\n".join(
            # [f"{player['name']} - {player['pos']} <{player['url']}>" for player in players]
            [f"<{player['url']}|{player['name']} - {player['pos']}>" for player in players]
        )
        print(f"Sending to Slack: {formatted_players}")

        return {"response_type": "in_channel", "text": formatted_players}

    except Exception as e:
        print(f"Error: {str(e)}")
        return JSONResponse(content={"text": f"Error: {str(e)}"})


# Middleware to log requests and responses
@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"Received {request.method} request to {request.url}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response


# Add an application startup log
@app.on_event("startup")
async def startup_event():
    logger.info("FastAPI application started.")


handler = Mangum(app)
