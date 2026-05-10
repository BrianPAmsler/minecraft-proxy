import asyncio
import io
import protocol
import socket
import json

class ServerManager:
    def __init__(self, address, port):
        self.address = address
        self.port = port

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
    server = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    server.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
    server.connect((address, port))
    server.setblocking(False)

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

    server.sendall(full_message.buffer)
    server.sendall(b'\x01\x00')
    print(f"sent: {full_message.buffer}")
    # await asyncio.sleep(1)

    response = await protocol.read_message(buffer)
    message_buffer = protocol.ByteBuffer(response.data)
    length = await protocol.read_var_int(message_buffer)
    string = ''
    while message_buffer.has_bytes():
        string += chr(await protocol.read_byte(message_buffer))

    string = trim_response(string)
    
    print(string)
    response: dict = json.loads(string)

    return ServerStatus(response.get('version'), response.get('players'), response.get('description'), response.get('favicon'), response.get('enforcesSecureChat'))