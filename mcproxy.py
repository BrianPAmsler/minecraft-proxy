import socket
import asyncio
import tomllib
from contextlib import suppress

SERVER_HOSTNAME = 'localhost'
SERVER_PORT = 25566
PROXY_PORT = 25565

with open("settings.toml", 'rb') as file:
    settings = tomllib.load(file)

    with suppress(KeyError):
        SERVER_HOSTNAME = settings['Server']['hostname']
        SERVER_PORT = settings['Server']['port']
        PROXY_PORT = settings['Proxy']['port']

def recv_all(socket: socket.socket):
    data = b""
    while True:
        try:
            chunk = socket.recv(8162)

            if len(chunk) == 0:
                raise ConnectionAbortedError()

            data += chunk
        except BlockingIOError:
            break

    return data

async def server_connection(server: socket.socket, client: socket.socket, address):
    print(f"[{address}] - Server connection established.")
    while True:
        if server.fileno() == -1:
            break

        try:
            data = recv_all(server)

            if len(data) > 0:
                client.sendall(data)
        except ConnectionAbortedError:
            break
        except BlockingIOError:
            pass

        await asyncio.sleep(0)
    
    print(f"[{address}] - Server connection closed.")

async def client_connection(client: socket.socket, address):
    print(f"[{address}] - Connected.")

    print(f"[{address}] - Establishing game server connection...")
    server = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    server.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
    server.connect((SERVER_HOSTNAME, SERVER_PORT))
    server.setblocking(False)

    asyncio.create_task(server_connection(server, client, address))

    while True:
        try:
            data = recv_all(client)

            if len(data) > 0:
                server.sendall(data)
        except ConnectionAbortedError:
            break
        except BlockingIOError:
            pass

        await asyncio.sleep(0)
    
    server.close()
    print(f"[{address}] - Disconnected.")

async def main():
    print("Starting proxy server...")
    proxy = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    proxy.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
    proxy.bind(('::', PROXY_PORT))
    proxy.setblocking(False)
    proxy.listen()
    
    print(f"Listening on port {PROXY_PORT} and forwarding to {SERVER_HOSTNAME}:{SERVER_PORT}.")

    while True:
        try:
            # accept connections from outside
            (clientsocket, address) = proxy.accept()
            # now do something with the clientsocket
            # in this case, we'll pretend this is a threaded server
            asyncio.create_task(client_connection(clientsocket, address[0]))
        except BlockingIOError:
            pass
        
        await asyncio.sleep(0)

asyncio.run(main())