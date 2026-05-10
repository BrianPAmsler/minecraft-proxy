from typing import Literal
import boto3

from settings import AWS_INSTANCE_ID

__ec2 = boto3.client('ec2')

async def shutdown_server():
    __ec2.stop_instances(InstanceIds=[AWS_INSTANCE_ID])

async def start_server():
    __ec2.start_instances(InstanceIds=[AWS_INSTANCE_ID])

async def get_status() -> Literal["Online", "Offline"]:
    response = __ec2.describe_instance_status(
        InstanceIds=[
            'i-1234567890abcdef0',
        ],
    )

    status = response['InstanceStatuses'][0]['InstanceState']['Name']

    # For the purposes of this program, any state that isn't fully stopped is considered 'Online'
    if status == 'pending' or status == 'stopped' or status == 'terminated':
        return 'Offline'
    else:
        return 'Online'

async def reboot():
    __ec2.reboot_instances(InstanceIds=[AWS_INSTANCE_ID])