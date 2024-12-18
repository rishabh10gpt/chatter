import logging
import requests
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from starlette.websockets import WebSocketState
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import random

app = FastAPI()

# Allow Cross-Origin Resource Sharing (CORS) to enable communication between different origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow requests from any origin
    allow_credentials=True,  # Allow cookies and credentials
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Configure logging to write to a file and display in the console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Log to console
        logging.FileHandler("websocket_server.log")  # Log to file
    ]
)

# Serve static files (JS, CSS, images) from the 'static' folder
app.mount("/static", StaticFiles(directory="static"), name="static")

# Use Jinja2Templates to render HTML files (e.g., index.html)
templates = Jinja2Templates(directory="templates")

# Route to serve index.html (you can modify this to include dynamic data if needed)
@app.get("/")
async def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Dictionary to store connected users
# Structure: {user_id: {"websocket": websocket, "tags": [], "ip": "", "geo": "", "browser_info": ""}}
connected_users = {}

# List to store users waiting for a match
# Structure: [(user_id, tags)]
waiting_users = []

# Dictionary to store the pairing of users
# Structure: {user_id: partner_id}
partner_map = {}


def get_geolocation(ip: str) -> dict:
    """Get geo-location information based on IP address."""
    try:
        response = requests.get(f'http://ipinfo.io/{ip}/json')
        data = response.json()
        return data
    except Exception as e:
        logging.error(f"Error fetching geolocation for IP {ip}: {e}")
        return {}


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    """
    WebSocket endpoint for managing user connections.
    
    Args:
        websocket (WebSocket): The WebSocket connection object.
        user_id (int): The ID of the user connecting to the WebSocket.
    """
    await websocket.accept()  # Accept the WebSocket connection
    
    # Extract the IP address from the WebSocket connection
    ip_address = websocket.client.host
    
    # Fetch geo-location data
    geo_data = get_geolocation(ip_address)
    city = geo_data.get('city', 'Unknown')
    region = geo_data.get('region', 'Unknown')
    country = geo_data.get('country', 'Unknown')
    
    # For the browser information, we need the client to send it
    # For example, user-agent as part of the initial message
    browser_info = ""  # Browser info should be provided by the client during connection
    
    # Save user information
    connected_users[user_id] = {
        "websocket": websocket,
        "tags": [],
        "ip": ip_address,
        "geo": {"city": city, "region": region, "country": country},
        "browser_info": browser_info
    }

    # Log user connection with IP, geo-location, and browser information
    logging.info(f"User {user_id} connected. IP: {ip_address}, Location: {city}, {region}, {country}, Browser: {browser_info}")

    await broadcast_online_count()

    try:
        while True:
            # Listen for incoming messages
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "connect":
                # Handle connection request with optional tags
                tags = data.get("tags", [])
                tags = [tag for tag in tags if tag != "isTrusted"]  # Filter out 'isTrusted' tag
                connected_users[user_id]["tags"] = tags
                logging.info(f"User {user_id} connecting with tags: {tags}")
                await connect_user(user_id, tags)
            elif action == "message":
                # Relay a message to the user's partner
                message = data.get("message")
                await send_message(user_id, message)
            elif action == "disconnect":
                # Handle user-initiated disconnection
                await handle_disconnect(user_id)
                break
    except WebSocketDisconnect:
        # Handle unexpected disconnection
        await handle_disconnect(user_id)


async def connect_user(user_id, user_tags):
    """
    Attempt to connect a user with a suitable partner based on common tags.
    
    Args:
        user_id (int): The ID of the user attempting to connect.
        user_tags (list): The list of tags provided by the user.
    """
    if user_id in partner_map:
        return

    matched_partner = None
    for (waiting_user_id, waiting_user_tags) in waiting_users:
        if not user_tags or not waiting_user_tags or set(user_tags).intersection(set(waiting_user_tags)):
            matched_partner = waiting_user_id
            waiting_users.remove((waiting_user_id, waiting_user_tags))
            break

    if matched_partner:
        partner_map[user_id] = matched_partner
        partner_map[matched_partner] = user_id

        common_tags = list(set(user_tags).intersection(set(connected_users[matched_partner]["tags"])))

        logging.info(f"User {user_id} connected with {matched_partner}. Common Tags: {common_tags}")

        await connected_users[user_id]["websocket"].send_json({
            "type": "connected",
            "partner_id": matched_partner,
            "tags": common_tags
        })
        await connected_users[matched_partner]["websocket"].send_json({
            "type": "connected",
            "partner_id": user_id,
            "tags": common_tags
        })
    else:
        waiting_users.append((user_id, user_tags))
        await connected_users[user_id]["websocket"].send_json({"type": "waiting"})


async def send_message(user_id, message):
    """
    Send a message from one user to their partner.

    Args:
        user_id (int): The ID of the user sending the message.
        message (str): The message content.
    """
    partner_id = partner_map.get(user_id)
    if partner_id and partner_id in connected_users:
        try:
            # Check if the partner's WebSocket is still open
            if connected_users[partner_id]["websocket"].client_state == WebSocketState.CONNECTED:
                logging.info(f"Message from {user_id} to {partner_id}: {message}")
                await connected_users[partner_id]["websocket"].send_json({
                    "type": "message",
                    "from": user_id,
                    "message": message
                })
        except Exception as e:
            # Handle any exceptions gracefully (e.g., WebSocket disconnected unexpectedly)
            print(f"Error sending message to user {partner_id}: {e}")


async def handle_disconnect(user_id):
    """
    Handle disconnection of a user, including notifying their partner and removing them from the system.

    Args:
        user_id (int): The ID of the user disconnecting.
    """
    # Notify the partner if one exists and WebSocket is still connected
    partner_id = partner_map.get(user_id)
    if partner_id and partner_id in connected_users:
        try:
            # Check if the partner's WebSocket is still open
            if connected_users[partner_id]["websocket"].client_state == WebSocketState.CONNECTED:
                logging.info(f"User {user_id} disconnected. Partner: {partner_id}")
                await connected_users[partner_id]["websocket"].send_json({
                    "type": "disconnected",
                    "message": "Partner disconnected."
                })
        except Exception as e:
            print(f"Error handling disconnect for user {user_id}: {e}")

        del partner_map[partner_id]

    # Remove the user from the waiting list
    waiting_users[:] = [(uid, tags) for uid, tags in waiting_users if uid != user_id]

    # Remove the user from the connected users and partner map
    if user_id in connected_users:
        del connected_users[user_id]
    if user_id in partner_map:
        del partner_map[user_id]

    # Broadcast the updated online count
    await broadcast_online_count()
    print(f"User {user_id} disconnected.")



async def broadcast_online_count():
    """
    Broadcast the current count of online users to all connected users.
    """
    online_count = len(connected_users)
    for user in connected_users.values():
        await user["websocket"].send_json({"type": "online_count", "count": online_count})


