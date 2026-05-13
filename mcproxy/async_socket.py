from __future__ import annotations

import asyncio
import functools
import signal
import socket
from typing import Any, Literal, overload
from sys import exit

type RetAddress = Any

class AsyncSocket:
    __active_connections: list[socket.socket] = []

    @overload
    def __init__(self, 
        family: socket.AddressFamily | int = -1,
        type: socket.SocketKind | int = -1,
        proto: int = -1,
        fileno: int | None = None): ...

    @overload
    def __init__(self, socket: socket.socket): ...

    def __init__(self, 
        family: socket.AddressFamily | int = -1,
        type: socket.SocketKind | int = -1,
        proto: int = -1,
        fileno: int | None = None):

        if isinstance(family, socket.socket):
            self.__socket = family
        else:
            self.__socket = socket.socket(family, type, proto, fileno)
        
        AsyncSocket.__active_connections.append(self.__socket)
    
    async def accept(self) -> tuple[AsyncSocket, RetAddress]:
        loop = asyncio.get_running_loop()
        sock, addr = await loop.run_in_executor(None, self.__socket.accept)

        return AsyncSocket(sock), addr
    
    async def bind(self, address: socket._Address):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.__socket.bind, address)
    
    async def close(self):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.__socket.close)
    
    async def connect(self, address: socket._Address):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.__socket.connect, address)
    
    async def detatch(self) -> int:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.__socket.detach)
    
    async def dup(self) -> AsyncSocket:
        loop = asyncio.get_running_loop()
        return AsyncSocket(await loop.run_in_executor(None, self.__socket.dup))
    
    async def fileno(self) -> int:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.__socket.fileno)
    
    async def get_inheritable(self) -> bool:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.__socket.get_inheritable)
    
    async def getpeername(self) -> RetAddress:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.__socket.getpeername)
    
    async def getsockname(self) -> RetAddress:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.__socket.getsockname)
    
    @overload
    async def getsockopt(self, level: int, optname: int) -> int: ...
    
    @overload
    async def getsockopt(self, level: int, optname: int, buflen: int) -> bytes: ...
    
    async def getsockopt(self, level: int, optname: int, buflen: int | None = None) -> bytes | int:
        loop = asyncio.get_running_loop()

        if buflen is None:
            return await loop.run_in_executor(None, self.__socket.getsockopt, level, optname)
        else:
            return await loop.run_in_executor(None, self.__socket.getsockopt, level, optname, buflen)
    
    async def gettimeout(self) -> float | None:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.__socket.gettimeout)
    
    async def listen(self, backlog: int = ...):
        loop = asyncio.get_running_loop()

        if backlog is ...:
            return await loop.run_in_executor(None, self.__socket.listen)
        else:
            return await loop.run_in_executor(None, self.__socket.listen, backlog)
    
    async def ioctl(self, control: int, option: int | tuple[int, int, int] | bool):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.__socket.ioctl, control, option)
    
    async def makefile(self, mode: Literal['b', 'rb', 'br', 'wb', 'bw', 'rwb', 'rbw', 'wrb', 'wbr', 'brw', 'bwr'],
        buffering: Literal[0],
        *,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None):

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, functools.partial(self.__socket.makefile, mode, buffering, encoding=encoding, errors=errors, newline=newline))
    
    async def recv(self,
        bufsize: int,
        flags: int = 0) -> bytes:

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.__socket.recv, bufsize, flags)
    
    async def recvfrom(self,
        bufsize: int,
        flags: int = 0):

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.__socket.recvfrom, bufsize, flags)
    
    async def recvfrom_into(self,
        buffer: socket.WriteableBuffer,
        nbytes: int = 0,
        flags: int = 0) -> tuple[int, RetAddress]:

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.__socket.recvfrom_into, buffer, nbytes, flags)
    
    async def recv_into(self,
        buffer: socket.WriteableBuffer,
        nbytes: int = 0,
        flags: int = 0) -> int:

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.__socket.recv_into, buffer, nbytes, flags)
    
    async def send(self, 
        data: socket.ReadableBuffer,
        flags: int = 0) -> int:

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.__socket.send, data, flags)
    
    async def sendall(self,
        data: socket.ReadableBuffer,
        flags: int = 0):

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.__socket.sendall, data, flags)
    
    @overload
    async def sendto(self,
        data: socket.ReadableBuffer,
        address: socket._Address) -> int: ...
    
    @overload
    async def sendto(self,
        data: socket.ReadableBuffer,
        flags: int,
        address: socket._Address) -> int: ...
    
    async def sendto(self, *args):
        loop = asyncio.get_running_loop()

        if len(args) == 2:
            data, address = args
            return await loop.run_in_executor(None, self.__socket.sendto, data, address)
        elif len(args) == 3:
            data, flags, address = args
            return await loop.run_in_executor(None, self.__socket.sendto, data, flags, address)
    
    async def sendfile(self,
        file: socket._SendableFile,
        offset: int = 0,
        count: int | None = None) -> int:

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.__socket.sendfile, file, offset, count)
    
    async def set_inheritable(self, inheritable: bool):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.__socket.set_inheritable, inheritable)
    
    async def settimeout(self, value: float | None):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.__socket.settimeout, value)
    
    @overload
    async def setsockopt(self,
        level: int,
        optname: int,
        value: int | socket.ReadableBuffer): ...
    
    @overload
    async def setsockopt(self,
        level: int,
        optname: int,
        value: None,
        optlen: int): ...
    
    async def setsockopt(self,
        level: int,
        optname: int,
        value: int | socket.ReadableBuffer | None,
        optlen: int | None = None):

        loop = asyncio.get_running_loop()

        if optlen is None:
            return await loop.run_in_executor(None, self.__socket.setsockopt, level, optname, value)
        else:
            return await loop.run_in_executor(None, self.__socket.setsockopt, level, optname, value, optlen)
    
    async def shutdown(self, how: int):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.__socket.shutdown, how)
    
    async def share(self, process_id: int):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.__socket.share, process_id)
    
    def close_all_connections():
        for sock in AsyncSocket.__active_connections:
            sock.shutdown(socket.SHUT_RD)
            sock.close()
        
        # exit(0)

signal.signal(signal.SIGINT, lambda a, b: AsyncSocket.close_all_connections())