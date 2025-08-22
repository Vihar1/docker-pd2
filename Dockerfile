FROM ubuntu:22.04

# Prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Install Wine, VNC, and debugging tools
RUN dpkg --add-architecture i386 && \
    apt-get update && apt-get install -y \
    wine32 \
    winetricks \
    x11vnc \
    xvfb \
    x11-utils \
    xdotool \
    fluxbox \
    wget \
    curl \
    unzip \
    gdb \
    strace \
    ltrace \
    psmisc \
    net-tools \
    lsof \
    python3 \
    python3-pip \
    nano \
    vim \
    mousepad \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies for memory scanning and MCP server
RUN pip3 install psutil vncdotool pillow mcp pydantic anyio fastapi uvicorn requests

# Set up Wine environment
ENV WINEPREFIX=/root/.wine
ENV WINEARCH=win32
ENV WINEDEBUG=-all
ENV DISPLAY=:1

# Initialize Wine
RUN wine wineboot --init

# Create directories
RUN mkdir -p /game /screenshots /memory_dumps

# Create desktop entry for Diablo 2
RUN mkdir -p /root/Desktop /root/.local/share/applications && \
    echo '[Desktop Entry]' > /root/Desktop/Diablo2.desktop && \
    echo 'Version=1.0' >> /root/Desktop/Diablo2.desktop && \
    echo 'Type=Application' >> /root/Desktop/Diablo2.desktop && \
    echo 'Name=Project Diablo 2' >> /root/Desktop/Diablo2.desktop && \
    echo 'Comment=Launch Project Diablo 2 with 3dfx' >> /root/Desktop/Diablo2.desktop && \
    echo 'Exec=wine /game/pd2/Game.exe -ns -3dfx' >> /root/Desktop/Diablo2.desktop && \
    echo 'Icon=applications-games' >> /root/Desktop/Diablo2.desktop && \
    echo 'Terminal=false' >> /root/Desktop/Diablo2.desktop && \
    echo 'Categories=Game;' >> /root/Desktop/Diablo2.desktop && \
    chmod +x /root/Desktop/Diablo2.desktop && \
    cp /root/Desktop/Diablo2.desktop /root/.local/share/applications/

# Configure fluxbox menu
RUN mkdir -p /root/.fluxbox && \
    echo '[begin] (Fluxbox)' > /root/.fluxbox/menu && \
    echo '  [exec] (Project Diablo 2) {wine /game/pd2/Game.exe -ns -3dfx}' >> /root/.fluxbox/menu && \
    echo '  [exec] (Terminal) {x-terminal-emulator}' >> /root/.fluxbox/menu && \
    echo '  [separator]' >> /root/.fluxbox/menu && \
    echo '  [restart] (Restart)' >> /root/.fluxbox/menu && \
    echo '  [exit] (Exit)' >> /root/.fluxbox/menu && \
    echo '[end]' >> /root/.fluxbox/menu

# VNC and game startup script
COPY start_diablo2.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/start_diablo2.sh

# Copy monitoring script
COPY diablo2_monitor.py /usr/local/bin/
COPY diablo2_mcp_server.py /usr/local/bin/

# Copy Project Diablo 2 game files (you need to provide these)
COPY pd2/ /game/pd2/

# Expose ports:
# 5901 - VNC server for remote desktop access
# 8080 - Web VNC interface (optional)  
# 3000 - HTTP health check endpoint
# 8765 - MCP server (HTTP/SSE transport for Claude Desktop)
EXPOSE 5901 8080 3000 8765

WORKDIR /game/pd2

CMD ["/usr/local/bin/start_diablo2.sh"]