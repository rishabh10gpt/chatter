let socket;
let userID = Math.floor(Math.random() * 1000000);
let partnerID = null;
let reconnectTimerInterval;
let isConnected = false;  // Declare isConnected

document.getElementById("userId").innerText = `Your User ID: ${userID}`;

const connectBtn = document.getElementById("connectBtn");
const disconnectBtn = document.getElementById("disconnectBtn");
const cancelConnectBtn = document.getElementById("cancelConnectBtn");
const loader = document.getElementById("loader");
const chatWindow = document.getElementById("chatWindow");
const messageInput = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");
const autoConnectCheckbox = document.getElementById("autoConnect");
const reconnectTimer = document.getElementById("reconnectTimer");
const timerCount = document.getElementById("timerCount");

connectBtn.addEventListener("click", initializeConnection);

disconnectBtn.addEventListener("click", () => {
    const confirmDisconnect = confirm("Are you sure you want to disconnect?");
    if (confirmDisconnect) {
        if (socket) {
            socket.send(JSON.stringify({ action: "disconnect" }));
            socket.close();
            clearReconnectTimer();
            toggleConnectedState(false);
        }
    }
});

sendBtn.addEventListener("click", () => {
    const message = messageInput.value;
    if (message && socket && socket.readyState === WebSocket.OPEN) {
        displayMessage(`You: ${message}`);
        socket.send(JSON.stringify({ action: "message", message: message }));
        messageInput.value = "";
    } else {
        console.log("WebSocket is not open. Message not sent.");
    }
});

cancelConnectBtn.addEventListener("click", () => {
    if (socket) {
        socket.close(); // Close the WebSocket if it's in the "connecting" state
        socket = null;  // Reset the socket object
        clearReconnectTimer(); // Stop any ongoing reconnect timer
        document.getElementById("status").innerText = "Connection canceled.";
        toggleConnectingState(false); // Reset the UI to the initial state
    }
});

function initializeConnection(tags = []) {
    if (isConnected) {
        console.log("Already connected to a partner.");
        return;  // Prevent multiple connections
    }

    console.log("Initializing new connection...");
    socket = new WebSocket(`ws://localhost:8000/ws/${userID}`);
    toggleConnectingState(true);
    clearChatWindow();

    socket.onopen = () => {
        console.log("WebSocket connected.");
        socket.send(JSON.stringify({ action: "connect", tags: tags }));
        document.getElementById("status").innerText = "Connecting...";
    };

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === "connected") {
            partnerID = data.partner_id;
            const commonTags = data.tags || [];

            document.getElementById("status").innerText = `Connected to User ID: ${partnerID}`;
            if (commonTags.length > 0) {
                const tagsElement = document.getElementById("commonTags");
                tagsElement.innerText = `Common Tags: ${commonTags.join(", ")}`;
                tagsElement.classList.remove("d-none");
            }

            toggleConnectedState(true);
            toggleConnectingState(false);
            isConnected = true;  // Set connection state to true
        } else if (data.type === "waiting") {
            document.getElementById("status").innerText = "Waiting for a partner...";
            document.getElementById("commonTags").classList.add("d-none");
        } else if (data.type === "message") {
            displayMessage(`Partner: ${data.message}`);
        } else if (data.type === "online_count") {
            document.getElementById("onlineCount").innerText = `Online Users: ${data.count}`;
        } else if (data.type === "disconnected") {
            console.log("Partner disconnected.");
            document.getElementById("status").innerText = "Partner disconnected. Please reconnect.";
            document.getElementById("commonTags").classList.add("d-none");
            toggleConnectedState(false);

            // Set isConnected to false on partner disconnect
            isConnected = false;

            if (autoConnectCheckbox.checked) {
                handleAutoReconnect(); // Trigger auto-reconnect on disconnection
            }
        }
    };

    socket.onclose = () => {
        console.log("WebSocket closed.");
        document.getElementById("status").innerText = "Disconnected from server.";
        toggleConnectedState(false);
        toggleConnectingState(false);
        isConnected = false;  // Update connection state

        if (autoConnectCheckbox.checked) {
            handleAutoReconnect(); // Trigger auto-reconnect on connection close
        }
    };

    socket.onerror = (error) => {
        console.error("WebSocket Error: ", error);
        document.getElementById("status").innerText = "WebSocket error.";
    };
}

function displayMessage(message) {
    chatWindow.innerHTML += `<p class="retro-font">${message}</p>`;
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

function clearChatWindow() {
    chatWindow.innerHTML = "";
}

function toggleConnectedState(connected) {
    connectBtn.classList.toggle("d-none", connected);
    disconnectBtn.classList.toggle("d-none", !connected);
    messageInput.disabled = !connected;
    sendBtn.disabled = !connected;
}

function toggleConnectingState(connecting) {
    connectBtn.disabled = connecting;
    cancelConnectBtn.classList.toggle("d-none", !connecting);
    loader.style.display = connecting ? "block" : "none";
}

function handleAutoReconnect() {
    if (!autoConnectCheckbox.checked) return; // Only reconnect if checkbox is checked

    let countdown = 3; // Start countdown from 3
    reconnectTimer.classList.remove("d-none");
    timerCount.innerText = countdown;

    if (reconnectTimerInterval) {
        clearInterval(reconnectTimerInterval); // Clear any existing timer
    }

    reconnectTimerInterval = setInterval(() => {
        countdown -= 1;
        timerCount.innerText = countdown;

        if (countdown <= 0) {
            clearInterval(reconnectTimerInterval);
            reconnectTimer.classList.add("d-none");

            // Re-enable the Connect button and try reconnecting
            connectBtn.disabled = false;
            connectBtn.classList.remove("d-none");
            document.getElementById("status").innerText = "Attempting to reconnect...";  // Show reconnect status

            // Check if initializeConnection is called correctly after countdown
            const tagInput = document.getElementById("tag").value.trim();
            const tags = tagInput ? tagInput.split(",").map(tag => tag.trim()) : [];
            console.log("Reconnecting with tags: ", tags); // Debug log
            initializeConnection(tags); // Attempt to reconnect with tags
        }
    }, 1000);
}

function clearReconnectTimer() {
    clearInterval(reconnectTimerInterval); // Stop any ongoing reconnect timer
    reconnectTimer.classList.add("d-none"); // Hide the reconnect timer
}

