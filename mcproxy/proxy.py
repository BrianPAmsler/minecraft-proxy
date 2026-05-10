import json
from async_socket import AsyncSocket as Socket
import socket
import asyncio
import tomllib
from contextlib import suppress

import jsonpickle
import protocol
import server_manager

# from sys import exit
# import nbtlib

# data = nbtlib.String('{"text": "Server is starting..."}')

# buffer = BytesIO()
# data.write(buffer)

# print(buffer.getvalue().hex(' '))

# exit(0)

SERVER_HOSTNAME = 'localhost'
SERVER_PORT = 25566
PROXY_PORT = 25565

# raw_msg = b'\x00\x21{"text": "Server is starting..."}'
# print(len(raw_msg))

SERVER_STARTING_MESSAGE = b'\x23\x00\x21{"text": "Server is starting..."}'
# print(error_message)
# print(len(error_message))

starting = False

with open("settings.toml", 'rb') as file:
    settings = tomllib.load(file)

    with suppress(KeyError):
        SERVER_HOSTNAME = settings['Server']['hostname']
        SERVER_PORT = settings['Server']['port']
        PROXY_PORT = settings['Proxy']['port']

async def server_connection(server: Socket, client: Socket, address):
    print(f"[{address}] - Server connection established.")
    while True:
        if await server.fileno() == -1:
            break

        data = await server.recv(8162)


        if len(data) > 0:
            if len(data) < 100:
                print("server - " + str(data))

            await client.sendall(data)
        else:
            break
    
    print(f"[{address}] - Server connection closed.")

async def client_connection(client: Socket, address):
    print(f"[{address}] - Connected.")

    # buffer = mcprotocol.SocketBuffer(client)
    # handshake = await mcprotocol.read_handshake(buffer)

    # print(handshake.__dict__)

    # client.close()

    # return

    server = None
    if not starting:
        print(f"[{address}] - Establishing game server connection...")
        server = Socket(socket.AF_INET6, socket.SOCK_STREAM)
        await server.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        await server.connect((SERVER_HOSTNAME, SERVER_PORT))

        asyncio.create_task(server_connection(server, client, address))

    while True:
        data = await client.recv(8162)

        if len(data) > 0:
            if len(data) < 100:
                print("client - " + str(data))

            if server is None:
                await client.sendall(SERVER_STARTING_MESSAGE)
                break

            await server.sendall(data)
        else:
            break
    
    if server is not None:
        await server.close()

    print(f"[{address}] - Disconnected.")

async def main():
    # status = await server_manager.server_status(SERVER_HOSTNAME, SERVER_PORT)

    # print(jsonpickle.dumps(status, unpicklable=False))

    # return
    print("Starting proxy server...")
    proxy = Socket(socket.AF_INET6, socket.SOCK_STREAM)
    await proxy.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
    await proxy.bind(('::', PROXY_PORT))
    await proxy.listen()
    
    print(f"Listening on port {PROXY_PORT} and forwarding to {SERVER_HOSTNAME}:{SERVER_PORT}.")

    while True:
        try:
            # accept connections from outside
            (clientsocket, address) = await proxy.accept()
            # now do something with the clientsocket
            # in this case, we'll pretend this is a threaded server
            asyncio.create_task(client_connection(clientsocket, address[0]))
        except OSError as e:
            if e.winerror == 10038:
                break
            
            raise e

