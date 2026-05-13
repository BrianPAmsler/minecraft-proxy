import asyncio
import subprocess
from typing import Literal
import boto3

from settings import AWS_INSTANCE_ID, TEST_SERVER_START_COMMAND, TEST_SERVER_DIRECTORY, AWS_REGION

__ec2 = None
try:
    __ec2 = boto3.client('ec2', region_name=AWS_REGION)
except Exception as e:
    print(e)

__test_server_process = None

async def __test_shutdown():
    global __test_server_process

    print("shutdown")

    if __test_server_process is None:
        return
    
    __test_server_process.stdin.write('stop\n')
    __test_server_process.stdin.flush()

async def shutdown_server():
    if __ec2 is None:
        return await __test_shutdown()
    
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, lambda: __ec2.stop_instances(InstanceIds=[AWS_INSTANCE_ID]))


async def __test_start():
    global __test_server_process

    print("start")

    if __test_server_process is not None:
        print("Server already running.")
        return

    __test_server_process = subprocess.Popen(
        TEST_SERVER_START_COMMAND,
        # stdout=subprocess.PIPE,
        # stderr=subprocess.PIPE, 
        stdin=subprocess.PIPE,
        text=True,
        cwd=TEST_SERVER_DIRECTORY,
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )

async def start_server():
    if __ec2 is None:
        return await __test_start()
    
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, lambda: __ec2.start_instances(InstanceIds=[AWS_INSTANCE_ID]))

async def __test_status():
    global __test_server_process


    if __test_server_process is not None and __test_server_process.poll() is not None:
        __test_server_process = None

    if __test_server_process is not None:
        status = 'Online'
    else:
        status = 'Offline'

    print(f"status = {status}")

    return status

async def get_status() -> Literal["Online", "Offline"]:
    if __ec2 is None:
        return await __test_status()
    
    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(None, lambda: __ec2.describe_instance_status(InstanceIds=[AWS_INSTANCE_ID]))

    status = response['InstanceStatuses'][0]['InstanceState']['Name']

    # For the purposes of this program, any state that isn't fully stopped is considered 'Online'
    if status == 'pending' or status == 'stopped' or status == 'terminated':
        return 'Offline'
    else:
        return 'Online'

async def __test_reboot():
    global __test_server_process

    print("reboot")

    loop = asyncio.get_running_loop()
    
    __test_server_process.stdin.write('stop\n')
    __test_server_process.stdin.flush()

    await loop.run_in_executor(None, __test_server_process.wait)
    __test_server_process = None

    __test_start()

async def reboot():
    if __ec2 is None:
        return await __test_reboot()
    
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, lambda: __ec2.reboot_instances(InstanceIds=[AWS_INSTANCE_ID]))