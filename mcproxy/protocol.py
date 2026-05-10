import asyncio
from async_socket import AsyncSocket as Socket

SEGMENT_BITS = 0x7F
CONTINUE_BIT = 0x80

class SocketBuffer:
    def __init__(self, socket: Socket):
        self.socket = socket
        self.buffer = b''
        self.position = 0
    
    async def read_byte(self) -> int:
        if self.position >= len(self.buffer):
            self.position = 0
            self.buffer = await self.socket.recv(8162)
            
            if not self.buffer:
                raise ConnectionAbortedError
        
        byte = self.buffer[self.position]
        self.position += 1

        return byte

async def read_var_int(buffer: SocketBuffer) -> int:
    value = 0
    position = 0
    currentByte = None

    while True:
        currentByte = await buffer.read_byte()
        value |= (currentByte & SEGMENT_BITS) << position

        if (currentByte & CONTINUE_BIT) == 0:
            break

        position += 7

        if position >= 32:
            raise Exception("VarInt is too big")
    

    return value

class WritableBuffer:
    def write_byte(byte: int): ...

def write_var_int(value: int, buffer: WritableBuffer):
    while True:
        if (value & ~SEGMENT_BITS) == 0:
            buffer.write_byte(value)
            return

        buffer.write_byte((value & SEGMENT_BITS) | CONTINUE_BIT)

        # unsigned right shift
        value = (value & 0xFFFFFFFF) >> 7

class ByteBuffer:
    def __init__(self, bytes: bytes):
        self.buffer = bytes
        self.position = 0
    
    async def read_byte(self) -> int:
        if self.position >= len(self.buffer):
            raise OverflowError("No bytes left in buffer.")
        
        byte = self.buffer[self.position]
        self.position += 1

        return byte
    
    def has_bytes(self) -> bool:
        return self.position < len(self.buffer)

class Handshake:
    def __init__(self, version: int, address: str, port: int, intent: int):
        self.version = version
        self.address = address
        self.port = port
        self.intent = intent

async def read_handshake(buffer: SocketBuffer) -> Handshake:
    message = await read_message(buffer)
    buffer = ByteBuffer(message.data)

    if message.packet_id != 0:
        print(message.__dict__)
        raise ValueError("Incorrect packet id.")
    
    version = await read_var_int(buffer)

    length = await read_var_int(buffer)
    address = b''
    while len(address) < length:
        address += buffer.read_byte().to_bytes(1, 'big')
    address = address.decode('utf-8')

    port_high = buffer.read_byte()
    port_low = buffer.read_byte()
    port = port_high << 8 | port_low

    intent = await read_var_int(buffer)

    return Handshake(version, address, port, intent)

class Message:
    def __init__(self, length: int, packet_id: int, data: bytes):
        self.length = length
        self.packet_id = packet_id
        self.data = data

async def read_message(buffer: SocketBuffer) -> Message:
    length = await read_var_int(buffer)

    data = b''
    while len(data) < length:
        data += (await buffer.read_byte()).to_bytes(1, 'big')

    message_buffer = ByteBuffer(data)

    packet_id = await read_var_int(message_buffer)

    data = b''
    while message_buffer.has_bytes():
        data += (await message_buffer.read_byte()).to_bytes(1, 'big')
    
    return Message(length, packet_id, data)
