from async_socket import AsyncSocket as Socket
import socket
import asyncio

from settings import SERVER_HOSTNAME, SERVER_PORT, PROXY_PORT, MINECRAFT_VERSION, AUTO_SHUTDOWN_TIME, STATUS_UPDATE_INTERVAL, ERROR_STATE_WAIT_TIME
from server_manager import ServerManager
import protocol
from protocol import PROTOCOL_VERSION

# from sys import exit
# import nbtlib

# data = nbtlib.String('{"text": "Server is starting..."}')

# buffer = BytesIO()
# data.write(buffer)

# print(buffer.getvalue().hex(' '))

# exit(0)

# raw_msg = b'\x00\x21{"text": "Server is starting..."}'
# print(len(raw_msg))

SERVER_STARTING_MESSAGE = b'\x23\x00\x21{"text": "Server is starting..."}'
SERVER_STOPPING_MESSAGE = b'\x39\x00\x37{"text": "Server is stopping. Please try again later."}'
f'''

'''

SERVER_STARTING_STATUS_MESSAGE = protocol.create_status_message(f'''
{{
    "version": {{
        "name": "{MINECRAFT_VERSION}",
        "protocol": {PROTOCOL_VERSION}
    }},
    "players": {{
        "max": 0,
        "online": 0
    }},
    "description": {{
        "text": "Server is currently starting up..."
    }},
    "enforcesSecureChat": false
}}
''')

SERVER_STOPPING_STATUS_MESSAGE = protocol.create_status_message(f'''
{{
    "version": {{
        "name": "{MINECRAFT_VERSION}",
        "protocol": {PROTOCOL_VERSION}
    }},
    "players": {{
        "max": 0,
        "online": 0
    }},
    "description": {{
        "text": "Server is currently shutting down. Please try again later."
    }},
    "enforcesSecureChat": false
}}
''')

async def server_connection(server: Socket, client: Socket, address):
    print(f"[{address}] - Server connection established.")
    while True:
        try:
            if await server.fileno() == -1:
                break

            data = await server.recv(8162)


            if len(data) > 0:
                await client.sendall(data)
            else:
                break
        except Exception as e:
            if e.errno == 88 or e.errno == 9 or (hasattr(e, 'winerror') and e.winerror == 10038): # Error caused by trying to use socket after it is closed
                break

            print(e)
    
    print(f"[{address}] - Server connection closed.")

async def client_connection(client: Socket, address, server_manager: ServerManager):
    print(f"[{address}] - Connected.")

    if server_manager.state == 'Running':
        print(f"[{address}] - Establishing game server connection...")
        server = Socket(socket.AF_INET, socket.SOCK_STREAM)
        await server.settimeout(1)
        await server.connect((SERVER_HOSTNAME, SERVER_PORT))
        await server.settimeout(None)

        asyncio.create_task(server_connection(server, client, address))

        while True:
            try:
                data = await client.recv(8162)

                if len(data) > 0:
                    if server is None:
                        await client.sendall(SERVER_STARTING_MESSAGE)
                        break

                    await server.sendall(data)
                else:
                    break
            except Exception as e:
                if e.errno == 88 or e.errno == 9 or (hasattr(e, 'winerror') and e.winerror == 10038): # Error caused by trying to use socket after it is closed
                    break

                print(e)
        
        await server.close()
    elif server_manager.state == 'Shutdown':
        await server_manager.start_server()
    elif server_manager.state == 'Stopping':
        socket_buffer = protocol.SocketBuffer(client)
        try:
            handshake = await protocol.read_handshake(socket_buffer)
        except:
            handshake = None
        
        if handshake.intent == 1: # Status request
            await protocol.read_message(socket_buffer) # recieve next message from client
            await client.sendall(SERVER_STOPPING_STATUS_MESSAGE)
        elif handshake.intent == 2: # Regular Connection
            await client.sendall(SERVER_STOPPING_MESSAGE)

    if server_manager.state == 'Starting':
        socket_buffer = protocol.SocketBuffer(client)
        try:
            handshake = await protocol.read_handshake(socket_buffer)
        except:
            handshake = None
        
        if handshake is not None and handshake.intent == 1: # Status request
            await protocol.read_message(socket_buffer) # recieve next message from client
            await client.sendall(SERVER_STARTING_STATUS_MESSAGE)
        elif handshake is not None and handshake.intent == 2: # Regular Connection
            await client.sendall(SERVER_STARTING_MESSAGE)

    print(f"[{address}] - Disconnected.")

async def main():
    server_manager = ServerManager(SERVER_HOSTNAME, SERVER_PORT, AUTO_SHUTDOWN_TIME, STATUS_UPDATE_INTERVAL, ERROR_STATE_WAIT_TIME)
    server_manager.run()

    print("Starting proxy server...")
    proxy = Socket(socket.AF_INET, socket.SOCK_STREAM)
    await proxy.bind(('0.0.0.0', PROXY_PORT))
    await proxy.listen()
    
    print(f"Listening on port {PROXY_PORT} and forwarding to {SERVER_HOSTNAME}:{SERVER_PORT}.")

    while True:
        try:
            # accept connections from outside
            (clientsocket, address) = await proxy.accept()
            # now do something with the clientsocket
            # in this case, we'll pretend this is a threaded server
            asyncio.create_task(client_connection(clientsocket, address[0], server_manager))
        except OSError as e:
            if e.errno == 88 or e.errno == 9 or (hasattr(e, 'winerror') and e.winerror == 10038): # Error caused by trying to use socket after it is closed
                break
            
            print(e)

