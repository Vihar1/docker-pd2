# diablo2_mcp_server.py

import asyncio
import json
import threading
import http.server
import socketserver
from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types
from diablo2_monitor import Diablo2Monitor, Diablo2MemoryScanner, Diablo2VNCCapture

# Global server instance
server = Server("diablo2-observer")

# Initialize monitoring components
monitor = Diablo2Monitor()
memory_scanner = Diablo2MemoryScanner()
vnc_capture = Diablo2VNCCapture()

# Network-accessible MCP server configuration
MCP_HTTP_PORT = 8765

class MCPHttpHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler for MCP-compatible API"""
    
    def do_GET(self):
        if self.path == '/health':
            self.send_json_response({
                'status': 'ok',
                'mcp_server': 'running',
                'game_process': 'connected' if (memory_scanner.process and memory_scanner.process.is_running()) else 'disconnected',
                'vnc_connection': 'connected' if vnc_capture.client else 'disconnected'
            })
        
        elif self.path == '/resources':
            # List available MCP resources
            self.send_json_response({
                'resources': [
                    {
                        'uri': 'diablo2://gamestate',
                        'name': 'Project Diablo 2 Game State',
                        'description': 'Current game state including player stats, position, and mode',
                        'mimeType': 'application/json'
                    },
                    {
                        'uri': 'diablo2://screenshot',
                        'name': 'Project Diablo 2 Screenshot',
                        'description': 'Current screenshot from the game',
                        'mimeType': 'image/png'
                    }
                ]
            })
        
        elif self.path == '/gamestate':
            # Get current game state
            try:
                if not memory_scanner.process or not memory_scanner.process.is_running():
                    self.send_json_response({
                        "error": "Game process not connected",
                        "status": "searching",
                        "message": "MCP server is searching for Diablo 2 process..."
                    })
                    return
                    
                state = memory_scanner.get_game_state()
                self.send_json_response({
                    'connected': True,
                    'player_name': state.player_name,
                    'character_level': state.character_level,
                    'hp': f"{state.current_hp}/{state.max_hp}",
                    'mana': f"{state.current_mana}/{state.max_mana}",
                    'experience': state.experience,
                    'gold': state.gold,
                    'position': f"({state.position_x}, {state.position_y})",
                    'area': state.current_area,
                    'mode': state.game_mode
                })
            except Exception as e:
                self.send_json_response({
                    "error": f"Failed to read game state: {str(e)}",
                    "connected": False
                })
        
        elif self.path == '/screenshot':
            # Get game screenshot
            try:
                screenshot = vnc_capture.capture_screenshot()
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'screenshot': f"data:image/png;base64,{screenshot}"
                }).encode())
            except Exception as e:
                self.send_json_response({
                    "error": f"Failed to capture screenshot: {str(e)}"
                })
        
        elif self.path == '/tools':
            # List available tools
            self.send_json_response({
                'tools': [
                    {
                        'name': 'scan_for_items',
                        'description': 'Scan memory for items in the game'
                    },
                    {
                        'name': 'monitor_health', 
                        'description': 'Monitor player health and alert if low'
                    },
                    {
                        'name': 'get_player_stats',
                        'description': 'Get comprehensive player statistics'
                    }
                ]
            })
        
        elif self.path.startswith('/tools/'):
            # Execute a tool
            tool_name = self.path.split('/')[-1]
            self.execute_tool(tool_name)
        
        else:
            self.send_json_response({
                'name': 'Diablo 2 MCP Server',
                'version': '1.0.0',
                'description': 'Network-accessible MCP server for Diablo 2 monitoring',
                'endpoints': [
                    '/health - Server health status',
                    '/resources - List available resources',
                    '/gamestate - Current game state',
                    '/screenshot - Game screenshot', 
                    '/tools - List available tools',
                    '/tools/{tool_name} - Execute a tool'
                ]
            })
    
    def execute_tool(self, tool_name):
        """Execute a named tool"""
        try:
            if tool_name == 'scan_for_items':
                items = memory_scanner.scan_for_items()
                result = f"Found {len(items)} potential items in memory:\n" + \
                        "\n".join([f"Address: {item['address']}, Data: {item['data']}" 
                                  for item in items[:10]])
            
            elif tool_name == 'monitor_health':
                state = memory_scanner.get_game_state()
                if state.current_hp > 0 and state.max_hp > 0:
                    health_percent = (state.current_hp / state.max_hp) * 100
                    if health_percent < 25:
                        result = f"⚠️  LOW HEALTH WARNING: {state.current_hp}/{state.max_hp} ({health_percent:.1f}%)"
                    else:
                        result = f"✅ Health OK: {state.current_hp}/{state.max_hp} ({health_percent:.1f}%)"
                else:
                    result = "❓ Cannot read health data"
            
            elif tool_name == 'get_player_stats':
                state = memory_scanner.get_game_state()
                process_info = memory_scanner.process.memory_info() if memory_scanner.process else None
                memory_usage = f"{process_info.rss / 1024 / 1024:.1f} MB" if process_info else "N/A"
                result = f"""🎮 Project Diablo 2 Player Stats
========================
👤 Player: {state.player_name}
📊 Level: {state.character_level}
❤️  Health: {state.current_hp}/{state.max_hp}
🔮 Mana: {state.current_mana}/{state.max_mana}
⭐ Experience: {state.experience:,}
💰 Gold: {state.gold:,}
📍 Position: ({state.position_x}, {state.position_y})
🗺️  Area: {state.current_area}
🎯 Mode: {state.game_mode}
💾 Memory Usage: {memory_usage}
"""
            
            else:
                result = f"Unknown tool: {tool_name}"
            
            self.send_json_response({'result': result})
        
        except Exception as e:
            self.send_json_response({'error': f"Error executing tool '{tool_name}': {str(e)}"})
    
    def send_json_response(self, data):
        """Send a JSON response"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())
    
    def log_message(self, format, *args):
        # Suppress HTTP server logs unless it's an error
        if "Error" in format:
            super().log_message(format, *args)

def start_health_server():
    """Start HTTP server for health checks (legacy endpoint)"""
    try:
        with socketserver.TCPServer(("", 3000), http.server.SimpleHTTPRequestHandler) as httpd:
            print("🏥 Health check server running on port 3000")
            httpd.serve_forever()
    except Exception as e:
        print(f"Failed to start health server: {e}")

def start_mcp_http_server():
    """Start the main MCP HTTP server for Claude Desktop"""
    try:
        with socketserver.TCPServer(("", MCP_HTTP_PORT), MCPHttpHandler) as httpd:
            print(f"🌐 MCP HTTP Server running on port {MCP_HTTP_PORT}")
            print(f"📡 Access endpoints at: http://your-server-ip:{MCP_HTTP_PORT}/")
            httpd.serve_forever()
    except Exception as e:
        print(f"Failed to start MCP HTTP server: {e}")

@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """List available resources"""
    return [
        types.Resource(
            uri="diablo2://gamestate",
            name="Project Diablo 2 Game State",
            description="Current game state including player stats, position, and mode",
            mimeType="application/json",
        ),
        types.Resource(
            uri="diablo2://screenshot",
            name="Project Diablo 2 Screenshot", 
            description="Current screenshot from the game",
            mimeType="image/png",
        ),
    ]

@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Read a specific resource"""
    if uri == "diablo2://gamestate":
        try:
            state = memory_scanner.get_game_state()
            return json.dumps({
                'player_name': state.player_name,
                'character_level': state.character_level,
                'hp': f"{state.current_hp}/{state.max_hp}",
                'mana': f"{state.current_mana}/{state.max_mana}",
                'experience': state.experience,
                'gold': state.gold,
                'position': f"({state.position_x}, {state.position_y})",
                'area': state.current_area,
                'mode': state.game_mode
            }, indent=2)
        except Exception as e:
            return json.dumps({"error": f"Failed to read game state: {str(e)}"}, indent=2)
    
    elif uri == "diablo2://screenshot":
        try:
            screenshot = vnc_capture.capture_screenshot()
            return f"data:image/png;base64,{screenshot}"
        except Exception as e:
            return f"Failed to capture screenshot: {str(e)}"
    
    else:
        raise ValueError(f"Unknown resource: {uri}")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools"""
    return [
        types.Tool(
            name="scan_for_items",
            description="Scan memory for items in the game",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            },
        ),
        types.Tool(
            name="monitor_health",
            description="Monitor player health and alert if low",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            },
        ),
        types.Tool(
            name="get_player_stats",
            description="Get comprehensive player statistics",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            },
        ),
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None = None) -> list[types.TextContent]:
    """Execute a tool"""
    try:
        if name == "scan_for_items":
            items = memory_scanner.scan_for_items()
            result = f"Found {len(items)} potential items in memory:\n" + \
                    "\n".join([f"Address: {item['address']}, Data: {item['data']}" 
                              for item in items[:10]])
        
        elif name == "monitor_health":
            state = memory_scanner.get_game_state()
            if state.current_hp > 0 and state.max_hp > 0:
                health_percent = (state.current_hp / state.max_hp) * 100
                if health_percent < 25:
                    result = f"⚠️  LOW HEALTH WARNING: {state.current_hp}/{state.max_hp} ({health_percent:.1f}%)"
                else:
                    result = f"✅ Health OK: {state.current_hp}/{state.max_hp} ({health_percent:.1f}%)"
            else:
                result = "❓ Cannot read health data"
        
        elif name == "get_player_stats":
            state = memory_scanner.get_game_state()
            process_info = memory_scanner.process.memory_info() if memory_scanner.process else None
            memory_usage = f"{process_info.rss / 1024 / 1024:.1f} MB" if process_info else "N/A"
            result = f"""🎮 Project Diablo 2 Player Stats
========================
👤 Player: {state.player_name}
📊 Level: {state.character_level}
❤️  Health: {state.current_hp}/{state.max_hp}
🔮 Mana: {state.current_mana}/{state.max_mana}
⭐ Experience: {state.experience:,}
💰 Gold: {state.gold:,}
📍 Position: ({state.position_x}, {state.position_y})
🗺️  Area: {state.current_area}
🎯 Mode: {state.game_mode}
💾 Memory Usage: {memory_usage}
"""
        
        else:
            raise ValueError(f"Unknown tool: {name}")
        
        return [types.TextContent(type="text", text=result)]
    
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error executing tool '{name}': {str(e)}")]

async def main():
    """Initialize and run the MCP server"""
    print("🚀 Starting Diablo 2 MCP Server...")
    
    # Start health check server in background thread
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    
    # Wait a bit for the game container to start up
    print("⏳ Waiting for game container to initialize...")
    await asyncio.sleep(5)
    
    # Initialize connections with container-aware logic
    max_retries = 5
    retry_delay = 10
    
    for attempt in range(max_retries):
        try:
            print(f"🔍 Attempting to find game process (attempt {attempt + 1}/{max_retries})...")
            
            # Try to attach to process (now should work with shared process namespace)
            if memory_scanner.attach_to_process():
                print("✅ Successfully attached to Diablo 2 process")
                break
            else:
                print(f"❌ No Diablo 2 process found")
                if attempt < max_retries - 1:
                    print(f"⏳ Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    
        except Exception as e:
            print(f"❌ Error during process attachment: {e}")
            if attempt < max_retries - 1:
                print(f"⏳ Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
    
    # Try to connect to VNC
    try:
        print("🔗 Connecting to VNC server...")
        if vnc_capture.connect():
            print("✅ Connected to VNC server")
        else:
            print("⚠️  VNC connection failed (screenshots will not work)")
    except Exception as e:
        print(f"⚠️  VNC connection failed: {e}")
    
    print("🎯 MCP Server ready for connections")
    print(f"📡 Claude Desktop can access via HTTP at: http://your-server-ip:{MCP_HTTP_PORT}/")
    
    # Start the MCP HTTP server (this will block)
    start_mcp_http_server()

if __name__ == "__main__":
    # Run the main function
    asyncio.run(main())