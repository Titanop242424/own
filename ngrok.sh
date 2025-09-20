#!/bin/bash

# Stop any existing server / ngrok
pkill -f "api.py"
pkill -f "ngrok"

# Start the API server on port 8080
echo "[+] Starting API server on port 8080..."
nohup python3 api_server.py > api_server.log 2>&1 &

# Download ngrok if not present
if [ ! -f ./ngrok ]; then
    echo "[+] Downloading ngrok..."
    curl -sSL https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-amd64.zip -o ngrok.zip
    unzip ngrok.zip
    rm ngrok.zip
    chmod +x ./ngrok
fi

# Set your ngrok auth token
NGROK_TOKEN="32y0SmLCgwFT33VSnkgyOSN7kP1_5bK56UvT7VUX5e9jdAtM"
if [[ "$NGROK_TOKEN" == "32y0SmLCgwFT33VSnkgyOSN7kP1_5bK56UvT7VUX5e9jdAtM" ]]; then
    echo "[!] You must set your ngrok auth token in the script."
    exit 1
fi

./ngrok authtoken "$NGROK_TOKEN"

# Start tunneling port 8080
echo "[+] Starting ngrok tunnel on port 8080..."
nohup ./ngrok http 8080 > ngrok.log 2>&1 &

# Wait for tunnel creation
sleep 5

# Fetch the public URL that ngrok created
NGROK_URL=$(curl --silent http://localhost:4040/api/tunnels | grep -o 'https://[0-9a-z]*\.ngrok.io' | head -n1)

if [ -n "$NGROK_URL" ]; then
    echo "[✓] Ngrok public URL: $NGROK_URL"
    echo "[!] Use this URL in bot.py and soul.py: $NGROK_URL"
else
    echo "[✗] Failed to get ngrok URL"
fi
