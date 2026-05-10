import asyncio
from datetime import datetime
import io
from typing import Literal
import server_controls
import protocol
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

class ByteWriteBuffer:
    def __init__(self):
        self.buffer = b''

    def write_byte(self, byte: int):
        self.buffer += byte.to_bytes(1, 'big')

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

        handshake = ByteWriteBuffer()
        
        protocol.write_var_int(765, handshake) # Protocol version
        protocol.write_var_int(len(address), handshake)
        handshake.buffer += address.encode('utf-8')
        port_high = (port & 0xF0) >> 4
        port_low = port & 0xF
        handshake.buffer += port_high.to_bytes(1, 'big')
        handshake.buffer += port_low.to_bytes(1, 'big')
        protocol.write_var_int(1, handshake) # Intent of 1 to request status

        full_message = ByteWriteBuffer()
        protocol.write_var_int(len(handshake.buffer) + 1, full_message)
        protocol.write_var_int(0, full_message)
        full_message.buffer += handshake.buffer

        await server.sendall(full_message.buffer)
        await server.sendall(b'\x01\x00')
        print(f"sent: {full_message.buffer}")
        # await asyncio.sleep(1)

        response = await protocol.read_message(buffer)
        message_buffer = protocol.ByteBuffer(response.data)
        length = await protocol.read_var_int(message_buffer)
        string = ''
        while message_buffer.has_bytes():
            string += chr(await message_buffer.read_byte())

        string = trim_response(string)
        
        print(string)
        response: dict = json.loads(string)

        return ServerStatus(response.get('version'), response.get('players'), response.get('description'), response.get('favicon'), response.get('enforcesSecureChat'))
    except ConnectionRefusedError:
        return None

class ServerManager:
    def __init__(self, address: socket._Address, port: int, auto_shutdown_time: float, update_interval: float, error_state_wait_time: float):
        self.address = address
        self.port = port
        self.auto_shutdown_time = auto_shutdown_time
        self.update_interval = update_interval
        self.error_state_wait_time = error_state_wait_time
        self.state: Literal["Shutdown", "Starting", "Stopping", "Running"] = "Shutdown"
        self.last_player_seen: datetime = datetime.now()
        self.error_state: datetime | None = None

    async def __loop(self):
        status = await server_status(self.address, self.port)
        if status is None:
            instance_status = await server_controls.get_status()
            if instance_status == "Online":
                self.state = "Starting"
        else:
            self.state = "Running"

        while True:
            await asyncio.sleep(self.update_interval)

            if self.state == "Running":
                status = await server_status(self.address, self.port)

                if status is None:
                    instance_status = await server_controls.get_status()
                    if instance_status == "Offline":
                        self.state = "Shutdown"
                    elif self.error_state is None:
                        self.error_state = datetime.now()
                    elif (datetime.now() - self.error_state).seconds >= self.error_state_wait_time:
                        self.error_state = None
                        self.state = 'Shutdown'
                        await server_controls.reboot()
                else:
                    if status.players.online > 0:
                        self.last_player_seen = datetime.now()

                    if (datetime.now() - self.last_player_seen).seconds >= self.auto_shutdown_time:
                        self.state = "Stopping"
                        await server_controls.shutdown_server()
            elif self.state == "Starting":
                instance_status = await server_controls.get_status()

                if instance_status == "Offline":
                    if self.error_state is None:
                        self.error_state = datetime.now()
                    elif (datetime.now() - self.error_state).seconds >= self.error_state_wait_time:
                        print("Unexpected error state. Instance is unexpectedly offline. Exiting...")
                        exit(1)
                else:
                    status = await server_status(self.address, self.port)

                    if status is not None:
                        self.state = "Running"
            elif self.state == "Stopping":
                instance_status = await server_controls.get_status()

                if instance_status == "Online":
                    if self.error_state is None:
                        self.error_state = datetime.now()

                    if (datetime.now() - self.error_state).seconds >= self.error_state_wait_time:
                        self.error_state = None
                        await server_controls.shutdown_server()
                        print("Instance taking an unexpectedly long time to shutdown.")
                else:
                    self.state = "Shutdown"
    
    def run(self):
        asyncio.create_task(self.__loop())