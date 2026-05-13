import asyncio
from datetime import datetime
from typing import Literal
import server_controls
import protocol
from protocol import PROTOCOL_VERSION
import socket
from async_socket import AsyncSocket as Socket
import json
from sys import exit

class Version:
    def __init__(self, name: str, protocol: int):
        self.name = name
        self.protocol = protocol

class PlayerSample:
    def __init__(self, name: str, id: str):
        self.name = name
        self.id = id

class Players:
    def __init__(self, max: int, online: int, sample: list[PlayerSample]=None):
        self.max = max
        self.online = online
        # Default to empty list if sample is missing, then map to objects
        sample_list = sample if sample is not None else []
        self.sample = [PlayerSample(**p) for p in sample_list]

class ServerStatus:
    def __init__(self, version: Version, players: Players, description: str, favicon: str, enforcesSecureChat: bool):
        # Map each nested dictionary to its specific class
        self.version = Version(**version)
        self.players = Players(**players)
        self.description = description
        self.favicon = favicon
        self.enforces_secure_chat = enforcesSecureChat

def trim_response(response: str) -> str:
    depth = 0
    i = 0
    while i == 0 or depth > 0 and i < len(response):
        if response[i] == '{':
            depth += 1
        elif response[i] == '}':
            depth -= 1

        i += 1

    return response[:i]

async def server_status(address: str, port: int) -> ServerStatus:
    try :
        server = Socket(socket.AF_INET6, socket.SOCK_STREAM)
        await server.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        await server.connect((address, port))

        buffer = protocol.SocketBuffer(server)

        handshake = protocol.ByteWriteBuffer()
        
        protocol.write_var_int(PROTOCOL_VERSION, handshake)
        protocol.write_var_int(len(address), handshake)
        handshake.buffer += address.encode('utf-8')
        port_high = (port & 0xF0) >> 4
        port_low = port & 0xF
        handshake.buffer += port_high.to_bytes(1, 'big')
        handshake.buffer += port_low.to_bytes(1, 'big')
        protocol.write_var_int(1, handshake) # Intent of 1 to request status

        full_message = protocol.ByteWriteBuffer()
        protocol.write_var_int(len(handshake.buffer) + 1, full_message)
        protocol.write_var_int(0, full_message)
        full_message.buffer += handshake.buffer

        await server.sendall(full_message.buffer)
        await server.sendall(b'\x01\x00')

        response = await protocol.read_message(buffer)
        message_buffer = protocol.ByteBuffer(response.data)
        length = await protocol.read_var_int(message_buffer)
        string = ''
        while message_buffer.has_bytes():
            string += chr(await message_buffer.read_byte())

        string = trim_response(string)

        response: dict = json.loads(string)

        return ServerStatus(response.get('version'), response.get('players'), response.get('description'), response.get('favicon'), response.get('enforcesSecureChat'))
    except (ConnectionRefusedError, ConnectionAbortedError):
        return None

class ServerManager:
    def __init__(self, address, port: int, auto_shutdown_time: float, update_interval: float, error_state_wait_time: float):
        self.address = address
        self.port = port
        self.auto_shutdown_time = auto_shutdown_time
        self.update_interval = update_interval
        self.error_state_wait_time = error_state_wait_time
        self.state: Literal["Shutdown", "Starting", "Stopping", "Running"] = "Shutdown"
        self.last_player_seen: datetime = datetime.now()
        self.error_state: datetime | None = None

    async def start_server(self):
        await server_controls.start_server()
        self.state = 'Starting'

    async def __loop(self):
        status = await server_status(self.address, self.port)
        if status is None:
            instance_status = await server_controls.get_status()
            if instance_status == "Online":
                self.state = "Starting"
        else:
            self.state = "Running"

        while True:
            try:
                await asyncio.sleep(self.update_interval)

                status = await server_status(self.address, self.port)
                instance_status = await server_controls.get_status()

                if self.state == "Running":

                    if status is None:
                        if instance_status == "Offline":
                            self.state = "Shutdown"
                        elif self.error_state is None:
                            self.error_state = datetime.now()
                        elif (datetime.now() - self.error_state).seconds >= self.error_state_wait_time:
                            self.error_state = None
                            self.state = 'Starting'
                            print('Server unexpectedly offline. Rebooting instance...')
                            await server_controls.reboot()
                    else:
                        if status.players.online > 0:
                            self.last_player_seen = datetime.now()

                        if (datetime.now() - self.last_player_seen).seconds >= self.auto_shutdown_time:
                            self.state = "Stopping"
                            await server_controls.shutdown_server()
                elif self.state == "Starting":
                    if instance_status == "Offline":
                        if self.error_state is None:
                            self.error_state = datetime.now()
                        elif (datetime.now() - self.error_state).seconds >= self.error_state_wait_time:
                            print("Unexpected error state. Instance is unexpectedly offline. Exiting...")
                            Socket.close_all_connections()
                            exit(1)
                    else:
                        if status is not None:
                            self.state = "Running"
                            self.last_player_seen = datetime.now()
                elif self.state == "Stopping":
                    if instance_status == "Online":
                        if self.error_state is None:
                            self.error_state = datetime.now()

                        if (datetime.now() - self.error_state).seconds >= self.error_state_wait_time:
                            self.error_state = None
                            await server_controls.shutdown_server()
                            print("Instance taking an unexpectedly long time to shutdown.")
                    else:
                        self.state = "Shutdown"
            except Exception as e:
                if e.errno == 88 or e.errno == 9 or (hasattr(e, 'winerror') and e.winerror == 10038): # Error caused by trying to use socket after it is closed
                    break
                
                print(e)
    
    def run(self):
        asyncio.create_task(self.__loop())