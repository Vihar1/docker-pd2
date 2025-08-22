#!/usr/bin/env python3
# diablo2_monitor.py

import os
import sys
import time
import json
import struct
import psutil
import base64
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Windows-specific imports for memory reading
LINUX_AVAILABLE = True
if sys.platform == 'win32':
    try:
        import ctypes
        from ctypes import wintypes, windll
        import pymem
        import pymem.process
        WINDOWS_AVAILABLE = True
    except ImportError:
        WINDOWS_AVAILABLE = False
        LINUX_AVAILABLE = True
else:
    WINDOWS_AVAILABLE = False
    LINUX_AVAILABLE = True

@dataclass
class D2GameState:
    player_name: str = ""
    character_level: int = 0
    current_hp: int = 0
    max_hp: int = 0
    current_mana: int = 0
    max_mana: int = 0
    experience: int = 0
    gold: int = 0
    position_x: int = 0
    position_y: int = 0
    current_area: str = ""
    game_mode: str = ""  # menu, in_game, loading, etc.

class Diablo2MemoryScanner:
    def __init__(self):
        self.game_pid = None
        self.process = None
        self.base_address = None
        self.d2game_base = None
        self.pymem_handle = None
        
        # Cheat Engine table offsets from D2GAME.dll+1107B8 base pointer
        self.base_pointer_offset = 0x1107B8  # D2GAME.dll+1107B8
        self.player_data_offsets = {
            'update_counter': 0x48C,    # 4 bytes
            'current_hp': 0x490,        # 2 bytes - Life
            'current_mana': 0x492,      # 2 bytes - Mana  
            'stamina': 0x494,           # 2 bytes - Stamina
            'character_class': 0x496,   # 1 byte - Class
            'character_level': 0x497,   # 1 byte - Level
            'position_y': 0x498,        # 2 bytes - y_coord
            'position_x': 0x49A,        # 2 bytes - x_coord
            'coord_flags': 0x49C,       # 2 bytes - Coordinate flags
            'unknown_word': 0x49E,      # 2 bytes - Unknown word
            'cached_mana': 0x4A0,       # 2 bytes - Cached mana for sync
            'last_exp': 0x4A2,          # 2 bytes - Last experience points
        }
        
        # Runtime addresses (will be calculated)
        self.player_data_base = None  # Pointer from D2GAME.dll+1107B8
    
    def find_diablo2_process(self) -> Optional[int]:
        """Find the Diablo 2 process running under Wine"""
        # First pass: Look for exact Game.exe or Diablo II.exe processes
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'exe']):
            try:
                proc_info = proc.info
                proc_name = (proc_info.get('name') or '').lower()
                cmdline = proc_info.get('cmdline') or []
                exe_path = (proc_info.get('exe') or '').lower()
                
                # Priority 1: Exact executable name matches
                if proc_name in ['game.exe', 'diablo ii.exe']:
                    print(f"Found Diablo process by name: PID={proc_info['pid']}, name={proc_name}")
                    return proc_info['pid']
                
                # Priority 2: Executable path contains game.exe
                if 'game.exe' in exe_path:
                    print(f"Found Diablo process by exe path: PID={proc_info['pid']}, exe={exe_path}")
                    return proc_info['pid']
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, AttributeError):
                continue
        
        # Second pass: Look for Wine processes with game files (less specific)
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'exe']):
            try:
                proc_info = proc.info
                proc_name = (proc_info.get('name') or '').lower()
                cmdline = proc_info.get('cmdline') or []
                
                # Check wine processes with our game files in command line
                if 'wine' in proc_name and cmdline:
                    for cmd in cmdline:
                        if cmd and 'game.exe' in (cmd or '').lower():
                            print(f"Found Wine process running game: PID={proc_info['pid']}, cmdline={cmdline}")
                            return proc_info['pid']
                            
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, AttributeError):
                continue
        return None
    
    def attach_to_process(self) -> bool:
        """Attach to the Diablo 2 process"""
        print("🔍 Scanning for Diablo 2 process...")
        
        # First, let's see all processes for debugging
        print("📋 All running processes:")
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_info = proc.info
                    name = (proc_info.get('name') or 'unknown')[:30]
                    pid = proc_info.get('pid', 'unknown')
                    cmdline = proc_info.get('cmdline', [])
                    if cmdline:
                        cmd_str = ' '.join(str(c) for c in cmdline[:3])[:50]
                        print(f"  PID {pid}: {name} - {cmd_str}")
                    else:
                        print(f"  PID {pid}: {name}")
                except:
                    continue
        except Exception as e:
            print(f"Error listing processes: {e}")
        
        self.game_pid = self.find_diablo2_process()
        if not self.game_pid:
            print("❌ Diablo 2 process not found")
            return False
        
        try:
            self.process = psutil.Process(self.game_pid)
            self.find_base_address()
            print(f"✅ Attached to Diablo 2 process (PID: {self.game_pid})")
            return True
        except Exception as e:
            print(f"❌ Failed to attach to process: {e}")
            return False
    
    def find_base_address(self):
        """Find the base address of the game executable and D2GAME.dll"""
        if sys.platform == 'win32' and WINDOWS_AVAILABLE:
            return self._find_base_address_windows()
        elif LINUX_AVAILABLE:
            return self._find_base_address_linux()
        else:
            print("❌ No memory access method available")
            return False

    def _find_base_address_windows(self):
        """Find D2GAME.dll base and calculate player data pointer"""
        max_retries = 10
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                print(f"🪟 Windows mode: Scanning memory... (Attempt {retry_count + 1}/{max_retries})")
                
                # Open process with pymem
                self.pymem_handle = pymem.Pymem()
                self.pymem_handle.open_process_from_id(self.game_pid)
                
                # Find D2GAME.dll module
                d2game_module = None
                for module in self.pymem_handle.list_modules():
                    if 'd2game.dll' in module.name.lower():
                        d2game_module = module
                        self.d2game_base = module.lpBaseOfDll
                        print(f"✅ D2GAME.dll base: 0x{self.d2game_base:08X}")
                        break
                
                if not d2game_module:
                    print("❌ D2GAME.dll module not found")
                    if retry_count < max_retries - 1:
                        print("⏳ Game may not be fully loaded yet, retrying in 3 seconds...")
                        time.sleep(3)
                        retry_count += 1
                        continue
                    return False
                
                # Calculate base pointer address: D2GAME.dll + 0x1107B8
                base_pointer_addr = self.d2game_base + self.base_pointer_offset
                print(f"📍 Base pointer address: 0x{base_pointer_addr:08X}")
                
                # Read the pointer value to get player data base
                try:
                    self.player_data_base = self.pymem_handle.read_uint(base_pointer_addr)
                    print(f"🎯 Player data base: 0x{self.player_data_base:08X}")
                    
                    # Check if pointer is null (game not fully loaded)
                    if self.player_data_base == 0:
                        print("❌ Player data base is null - game not fully loaded yet")
                        if retry_count < max_retries - 1:
                            print("⏳ Retrying in 3 seconds...")
                            time.sleep(3)
                            retry_count += 1
                            continue
                        return False
                    
                    # Validate by reading a known value (HP)
                    hp_addr = self.player_data_base + self.player_data_offsets['current_hp']
                    hp_value = self.pymem_handle.read_ushort(hp_addr)  # 2 bytes
                    print(f"✅ HP validation: {hp_value} at 0x{hp_addr:08X}")
                    
                    if hp_value > 0 and hp_value < 10000:  # Reasonable HP range
                        return True
                    else:
                        print(f"❌ HP value {hp_value} seems invalid, retrying...")
                    
                except Exception as e:
                    print(f"❌ Failed to read player data pointer: {e}")
                    
            except Exception as e:
                print(f"❌ Pymem initialization failed: {e}")
            
            # Retry logic
            if retry_count < max_retries - 1:
                print(f"⏳ Game may not be fully loaded yet, retrying in 3 seconds... ({retry_count + 1}/{max_retries})")
                time.sleep(3)
                retry_count += 1
            else:
                print("❌ Max retries reached - giving up")
                return False
                
        return False

    def _find_base_address_linux(self):
        """Find base address using Linux /proc filesystem (for containers)"""
        try:
            # Try Linux proc method first (for container environment)
            with open(f"/proc/{self.game_pid}/maps", 'r') as f:
                for line in f:
                    if any(game_file in line.lower() for game_file in ['game.exe', 'diablo', '.exe']):
                        addr_range = line.split()[0]
                        self.base_address = int(addr_range.split('-')[0], 16)
                        print(f"Base address found via /proc/maps: 0x{self.base_address:08x}")
                        break
                        
            # Find D2GAME.dll base address
            with open(f"/proc/{self.game_pid}/maps", 'r') as f:
                for line in f:
                    if 'd2game.dll' in line.lower():
                        addr_range = line.split()[0]
                        self.d2game_base = int(addr_range.split('-')[0], 16)
                        print(f"D2GAME.dll base address found: 0x{self.d2game_base:08x}")
                        # Calculate current_hp offset: Based on expected address 0x0A690490
                        # Direct calculation based on known working values
        except Exception as e:
            print(f"❌ Failed to initialize D2GAME.dll detection: {e}")
            return False

    def _find_base_address_linux(self):
        """Find D2GAME.dll base in Wine using /proc/maps"""
        max_retries = 10
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                print(f"🐧 Linux/Wine mode: Scanning memory maps... (Attempt {retry_count + 1}/{max_retries})")
                
                # Find D2GAME.dll in Wine process memory maps
                d2game_base = None
                with open(f"/proc/{self.game_pid}/maps", 'r') as f:
                    for line in f:
                        # Look for D2GAME.dll loaded by Wine
                        if 'd2game.dll' in line.lower():
                            addr_range = line.split()[0]
                            d2game_base = int(addr_range.split('-')[0], 16)
                            print(f"✅ D2GAME.dll found at: 0x{d2game_base:08X}")
                            break
                
                if not d2game_base:
                    print("❌ D2GAME.dll not found in Wine process maps")
                    if retry_count < max_retries - 1:
                        print("⏳ Game may not be fully loaded yet, retrying in 3 seconds...")
                        time.sleep(3)
                        retry_count += 1
                        continue
                    return False
                
                self.d2game_base = d2game_base
                
                # Calculate base pointer address: D2GAME.dll + 0x1107B8
                base_pointer_addr = self.d2game_base + self.base_pointer_offset
                print(f"📍 Base pointer address: 0x{base_pointer_addr:08X}")
                
                # Read the pointer value using Linux /proc/mem
                try:
                    with open(f"/proc/{self.game_pid}/mem", 'rb') as mem_file:
                        mem_file.seek(base_pointer_addr)
                        pointer_bytes = mem_file.read(4)  # Read 4 bytes for pointer
                        
                        if len(pointer_bytes) == 4:
                            self.player_data_base = struct.unpack('<I', pointer_bytes)[0]
                            print(f"🎯 Player data base: 0x{self.player_data_base:08X}")
                            
                            # Check if pointer is null (game not fully loaded)
                            if self.player_data_base == 0:
                                print("❌ Player data base is null - game not fully loaded yet")
                                if retry_count < max_retries - 1:
                                    print("⏳ Retrying in 3 seconds...")
                                    time.sleep(3)
                                    retry_count += 1
                                    continue
                                return False
                            
                            # Validate by reading HP
                            hp_addr = self.player_data_base + self.player_data_offsets['current_hp']
                            mem_file.seek(hp_addr)
                            hp_bytes = mem_file.read(2)  # HP is 2 bytes
                            
                            if len(hp_bytes) == 2:
                                hp_value = struct.unpack('<H', hp_bytes)[0]  # unsigned short
                                print(f"✅ HP validation: {hp_value} at 0x{hp_addr:08X}")
                                if hp_value > 0 and hp_value < 10000:  # Reasonable HP range
                                    return True
                                else:
                                    print(f"❌ HP value {hp_value} seems invalid, retrying...")
                            else:
                                print("❌ Failed to read HP for validation")
                        else:
                            print("❌ Failed to read base pointer")
                            
                except (OSError, IOError) as e:
                    print(f"❌ Failed to read process memory: {e}")
                    print("💡 Try running with elevated privileges or ptrace permissions")
                    
            except Exception as e:
                print(f"❌ Failed to initialize Linux memory access: {e}")
            
            # Retry logic
            if retry_count < max_retries - 1:
                print(f"⏳ Game may not be fully loaded yet, retrying in 3 seconds... ({retry_count + 1}/{max_retries})")
                time.sleep(3)
                retry_count += 1
            else:
                print("❌ Max retries reached - giving up")
                return False
                
        return False

    def read_memory(self, address: int, size: int) -> bytes:
        """Read memory from the process - cross-platform"""
        if sys.platform == 'win32' and WINDOWS_AVAILABLE:
            return self._read_memory_windows(address, size)
        else:
            return self._read_memory_linux(address, size)
    
    def _read_memory_windows(self, address: int, size: int) -> bytes:
        """Read memory using pymem"""
        try:
            if self.pymem_handle:
                return self.pymem_handle.read_bytes(address, size)
            else:
                # Fallback to direct Windows API
                PROCESS_VM_READ = 0x0010
                handle = windll.kernel32.OpenProcess(PROCESS_VM_READ, False, self.game_pid)
                if not handle:
                    return b'\x00' * size
                
                buffer = ctypes.create_string_buffer(size)
                bytes_read = ctypes.c_size_t(0)
                
                success = windll.kernel32.ReadProcessMemory(
                    handle,
                    ctypes.c_void_p(address),
                    buffer,
                    size,
                    ctypes.byref(bytes_read)
                )
                
                windll.kernel32.CloseHandle(handle)
                
                if success and bytes_read.value == size:
                    return buffer.raw
                else:
                    return b'\x00' * size
                
        except Exception as e:
            print(f"Windows memory read failed at 0x{address:08x}: {e}")
            return b'\x00' * size
    
    def _read_memory_linux(self, address: int, size: int) -> bytes:
        """Read memory using Linux /proc/PID/mem"""
        try:
            with open(f"/proc/{self.game_pid}/mem", 'rb') as f:
                f.seek(address)
                return f.read(size)
        except Exception as e:
            print(f"Memory read failed at 0x{address:08x}: {e}")
            return b'\x00' * size
    
    def read_player_data(self, data_type: str) -> int:
        """Read player data using Cheat Engine offsets with retry logic"""
        if not self.player_data_base or data_type not in self.player_data_offsets:
            return 0
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                address = self.player_data_base + self.player_data_offsets[data_type]
                
                if sys.platform == 'win32' and WINDOWS_AVAILABLE and self.pymem_handle:
                    # Windows with pymem
                    if data_type == 'update_counter':
                        result = self.pymem_handle.read_uint(address)  # 4 bytes
                    elif data_type in ['character_class', 'character_level']:
                        result = self.pymem_handle.read_uchar(address)  # 1 byte
                    else:
                        result = self.pymem_handle.read_ushort(address)  # 2 bytes
                else:
                    # Linux with /proc/mem
                    result = self._read_player_data_linux(address, data_type)
                
                # Return result on successful read
                return result
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"Failed to read {data_type} (attempt {attempt + 1}/{max_retries}): {e}")
                    time.sleep(0.1)  # Short delay before retry
                    continue
                else:
                    print(f"Failed to read {data_type} after {max_retries} attempts: {e}")
                    return 0
        
        return 0

    def _read_player_data_linux(self, address: int, data_type: str) -> int:
        """Read player data on Linux using /proc/mem"""
        try:
            with open(f"/proc/{self.game_pid}/mem", 'rb') as mem_file:
                mem_file.seek(address)
                
                if data_type == 'update_counter':
                    # 4 bytes unsigned int
                    data = mem_file.read(4)
                    return struct.unpack('<I', data)[0] if len(data) == 4 else 0
                elif data_type in ['character_class', 'character_level']:
                    # 1 byte unsigned char
                    data = mem_file.read(1)
                    return struct.unpack('<B', data)[0] if len(data) == 1 else 0
                else:
                    # 2 bytes unsigned short
                    data = mem_file.read(2)
                    return struct.unpack('<H', data)[0] if len(data) == 2 else 0
                    
        except (OSError, IOError) as e:
            print(f"Linux memory read failed for {data_type}: {e}")
            return 0

    def read_int32(self, offset: int) -> int:
        """Legacy function - kept for compatibility"""
        return 0
    
    def read_string(self, offset: int, max_length: int = 256) -> str:
        """Legacy function - kept for compatibility"""
        return ""
        if not self.base_address:
            return ""
        
        address = self.base_address + offset
        data = self.read_memory(address, max_length)
        try:
            # Find null terminator
            null_pos = data.find(b'\x00')
            if null_pos != -1:
                data = data[:null_pos]
            return data.decode('utf-8', errors='ignore')
        except:
            return ""
    
    def get_game_state(self) -> D2GameState:
        """Extract current game state using Cheat Engine offsets"""
        if not self.process or not self.process.is_running():
            return D2GameState()
        
        if not self.player_data_base:
            print("❌ Player data base not available - attempting to reinitialize...")
            # Try to reinitialize base address
            if self.find_base_address():
                print("✅ Base address reinitialized successfully")
            else:
                print("❌ Failed to reinitialize base address")
                return D2GameState()
        
        state = D2GameState()
        
        try:
            # Read values using Cheat Engine offsets
            state.current_hp = self.read_player_data('current_hp')
            state.current_mana = self.read_player_data('current_mana')
            state.character_level = self.read_player_data('character_level')
            state.position_x = self.read_player_data('position_x')
            state.position_y = self.read_player_data('position_y')
            
            # Additional data available from the table
            stamina = self.read_player_data('stamina')
            char_class = self.read_player_data('character_class')
            update_counter = self.read_player_data('update_counter')
            
            # Check if we're getting valid data
            if state.current_hp == 0 and state.character_level == 0 and state.current_mana == 0:
                print("❌ All player data is zero - game may not be fully loaded")
                state.game_mode = "loading"
            elif state.current_hp > 0 and state.character_level > 0:
                state.game_mode = "in_game"
                print(f"📊 HP: {state.current_hp}, Mana: {state.current_mana}, Level: {state.character_level}")
                print(f"📍 Position: ({state.position_x}, {state.position_y}), Class: {char_class}")
            else:
                state.game_mode = "menu"
                
        except Exception as e:
            print(f"❌ Error reading game state: {e}")
            state.game_mode = "error"
        
        return state
    
    def scan_for_items(self) -> List[Dict[str, Any]]:
        """Scan memory for item data"""
        items = []
        
        # Item signature pattern (example)
        item_pattern = b'\x01\x02\x03\x04'  # This would be actual item signature
        
        try:
            with open(f"/proc/{self.game_pid}/maps", 'r') as f:
                for line in f:
                    if 'rw-p' in line:  # Read-write memory regions
                        parts = line.split()
                        addr_range = parts[0].split('-')
                        start_addr = int(addr_range[0], 16)
                        end_addr = int(addr_range[1], 16)
                        size = min(end_addr - start_addr, 1024 * 1024)  # Limit to 1MB chunks
                        
                        data = self.read_memory(start_addr, size)
                        offset = 0
                        while True:
                            pos = data.find(item_pattern, offset)
                            if pos == -1:
                                break
                            
                            # Extract item data (simplified)
                            item_addr = start_addr + pos
                            item_data = self.read_memory(item_addr, 64)
                            
                            items.append({
                                'address': hex(item_addr),
                                'data': item_data[:16].hex(),
                                'type': 'unknown'
                            })
                            
                            offset = pos + 1
                            if len(items) > 100:  # Limit results
                                break
                        
                        if len(items) > 100:
                            break
                            
        except Exception as e:
            print(f"Error scanning for items: {e}")
        
        return items

class Diablo2VNCCapture:
    def __init__(self, host=None, port=None):
        # Use environment variables for Docker container setup, fallback to defaults
        self.host = host or os.getenv('VNC_HOST', 'localhost')
        self.port = port or int(os.getenv('VNC_PORT', '5901'))
        self.client = None
        print(f"VNC Capture configured for {self.host}:{self.port}")
    
    def connect(self):
        """Connect to VNC server"""
        try:
            import vncdotool.api as vnc
            # Try different VNC connection methods
            connection_strings = [
                f'{self.host}::{self.port}',
                f'{self.host}:{self.port}',
                f'{self.host}:{self.port-1}',  # Try display :0 if :1 fails
            ]
            
            for conn_str in connection_strings:
                try:
                    print(f"Trying VNC connection: {conn_str}")
                    self.client = vnc.connect(conn_str)
                    print(f"Connected to VNC server at {conn_str}")
                    return True
                except Exception as e:
                    print(f"VNC connection failed for {conn_str}: {e}")
                    continue
                    
            return False
        except Exception as e:
            print(f"VNC connection failed: {e}")
            return False
    
    def capture_screenshot(self) -> str:
        """Capture game screenshot"""
        if not self.client:
            return ""
        
        try:
            timestamp = int(time.time())
            screenshot_path = f'/screenshots/diablo2_{timestamp}.png'
            self.client.captureScreen(screenshot_path)
            
            with open(screenshot_path, 'rb') as img_file:
                img_data = base64.b64encode(img_file.read()).decode()
            
            return img_data
        except Exception as e:
            print(f"Screenshot capture failed: {e}")
            return ""

class Diablo2Monitor:
    def __init__(self):
        self.memory_scanner = Diablo2MemoryScanner()
        self.vnc_capture = Diablo2VNCCapture()
        self.monitoring = False
    
    def start_monitoring(self):
        """Start the monitoring loop"""
        print("Starting Diablo 2 monitoring...")
        
        # Wait for game to start
        while not self.memory_scanner.attach_to_process():
            print("Waiting for Diablo 2 to start...")
            time.sleep(5)
        
        # Connect to VNC
        self.vnc_capture.connect()
        
        self.monitoring = True
        self.monitor_loop()
    
    def monitor_loop(self):
        """Main monitoring loop"""
        memory_read_failures = 0
        max_memory_failures = 5
        
        while self.monitoring:
            try:
                # Get game state
                game_state = self.memory_scanner.get_game_state()
                
                # Check if we're having consistent memory read issues
                if game_state.game_mode in ["error", "loading"]:
                    memory_read_failures += 1
                    if memory_read_failures >= max_memory_failures:
                        print(f"❌ Too many consecutive memory read failures ({memory_read_failures})")
                        print("⏳ Attempting to reinitialize memory scanner...")
                        
                        # Try to reinitialize the memory scanner
                        if self.memory_scanner.attach_to_process():
                            print("✅ Memory scanner reinitialized successfully")
                            memory_read_failures = 0
                        else:
                            print("❌ Failed to reinitialize memory scanner, waiting...")
                            time.sleep(5)
                            continue
                else:
                    # Reset failure counter on successful reads
                    memory_read_failures = 0
                
                # Capture screenshot
                screenshot = self.vnc_capture.capture_screenshot()
                
                # Scan for items occasionally
                items = []
                if int(time.time()) % 30 == 0:  # Every 30 seconds
                    items = self.memory_scanner.scan_for_items()
                
                # Create monitoring report
                report = {
                    'timestamp': time.time(),
                    'game_state': {
                        'player_name': game_state.player_name,
                        'character_level': game_state.character_level,
                        'hp': f"{game_state.current_hp}/{game_state.max_hp}",
                        'mana': f"{game_state.current_mana}/{game_state.max_mana}",
                        'experience': game_state.experience,
                        'gold': game_state.gold,
                        'position': f"({game_state.position_x}, {game_state.position_y})",
                        'area': game_state.current_area,
                        'mode': game_state.game_mode
                    },
                    'screenshot': screenshot[:100] + "..." if screenshot else "",  # Truncate for logging
                    'items_found': len(items),
                    'process_info': {
                        'pid': self.memory_scanner.game_pid,
                        'memory_usage': self.memory_scanner.process.memory_info().rss / 1024 / 1024,  # MB
                        'cpu_percent': self.memory_scanner.process.cpu_percent()
                    }
                }
                
                # Save report
                try:
                    report_path = f'/memory_dumps/report_{int(time.time())}.json'
                    with open(report_path, 'w') as f:
                        json.dump(report, f, indent=2)
                except Exception as e:
                    print(f"Warning: Could not save report: {e}")
                
                # Print status with more details for troubleshooting
                status_msg = (f"[{time.strftime('%H:%M:%S')}] "
                             f"Player: {game_state.player_name} "
                             f"Level: {game_state.character_level} "
                             f"HP: {game_state.current_hp}/{game_state.max_hp} "
                             f"Mode: {game_state.game_mode}")
                
                if memory_read_failures > 0:
                    status_msg += f" (Failures: {memory_read_failures}/{max_memory_failures})"
                    
                print(status_msg)
                
            except Exception as e:
                print(f"Monitoring error: {e}")
                memory_read_failures += 1
            
            # Adjust sleep time based on game state
            if game_state and game_state.game_mode == "loading":
                time.sleep(3)  # Sleep longer when game is loading
            else:
                time.sleep(1)  # Monitor every second normally

if __name__ == "__main__":
    monitor = Diablo2Monitor()
    monitor.start_monitoring()