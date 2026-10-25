#!/bin/bash
# start_diablo2.sh

echo "Starting Project Diablo 2 container..."

# Cleanup function for graceful shutdown
cleanup() {
    echo "Shutting down services..."
    kill $GAME_PID $VNC_PID $MONITOR_PID $MCP_PID $FLUXBOX_PID $XVFB_PID 2>/dev/null
    exit 0
}
trap cleanup SIGTERM SIGINT

# Start virtual display
Xvfb $DISPLAY -screen 0 1068x600x16 &
XVFB_PID=$!
sleep 3

# Start window manager
fluxbox &
FLUXBOX_PID=$!
sleep 2

# Start VNC server
x11vnc -display $DISPLAY -nopw -listen 0.0.0.0 -xkb -forever -shared -rfbport 5901 &
VNC_PID=$!
sleep 2

echo "VNC server started on port 5901"

# Start memory monitoring service
# python3 /usr/local/bin/diablo2_monitor.py &
# MONITOR_PID=$!

# Start MCP server for AI integration
# python3 /usr/local/bin/diablo2_mcp_server.py &
# MCP_PID=$!
# echo "MCP server started on port 8765"

# Configure Wine for Project Diablo 2
cd /root/.wine/drive_c
ln -sf /game/pd2 ./

# Install DirectX for Project Diablo 2
winetricks -q directx9

# Start Project Diablo 2 in full screen windowed mode
echo "Launching Project Diablo 2 in full screen windowed mode..."
cd /game/pd2/ProjectD2
wine Game.exe -ns -3dfx &
GAME_PID=$!

# Wait for window and position it for full screen windowed mode
# sleep 5
# for i in {1..10}; do
#     WINDOW_ID=$(xdotool search --name "Diablo II" 2>/dev/null | head -1)
#     if [ -n "$WINDOW_ID" ]; then
#         echo "Positioning game window for full screen windowed mode..."
#         xdotool windowsize $WINDOW_ID 1068 600 2>/dev/null
#         xdotool windowmove $WINDOW_ID 0 0 2>/dev/null
#         echo "Game window positioned at full screen (1068x600)"
#         break
#     fi
#     sleep 1
# done

# Keep container running and monitor processes
wait $GAME_PID
