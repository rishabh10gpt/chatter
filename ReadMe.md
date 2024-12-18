# Chatter WebSocket Application

A real-time chat application using **FastAPI** and **WebSockets** that allows users to connect with a random partner based on common tags, send messages, and disconnect.

## Features

- **WebSocket Connection**: Real-time communication between users.
- **Tag-Based Matching**: Users can add tags, and the app tries to match users with common tags.
- **Auto Reconnect**: Automatically reconnect when a partner disconnects.
- **Geo-location and Browser Info**: Logs user's location and browser information based on their IP.

## Tech Stack

- **Backend**: FastAPI, WebSockets, Python 3.10+
- **Frontend**: HTML, CSS, JavaScript
- **WebSocket Server**: Handles real-time communication between clients.


## Requirements

- **Python 3.10+**
- **FastAPI** for the backend API.
- **Uvicorn** for running the ASGI server.
- **requests** for IP geolocation fetching.

## Installation

1. Clone the repository to your local machine:

   ```bash
   git clone https://github.com/rishabh10gpt/chatter.git
   cd chatter
2. 
   ```bash
   pip install -r requirements.txt

3. 
    ```bash
    uvicorn app.main:app --reload

