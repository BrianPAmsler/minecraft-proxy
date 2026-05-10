from contextlib import suppress
import tomllib

SERVER_HOSTNAME = 'localhost'
SERVER_PORT = 25566
PROXY_PORT = 25565
AWS_INSTANCE_ID = ""

with open("settings.toml", 'rb') as file:
    settings = tomllib.load(file)

    with suppress(KeyError):
        SERVER_HOSTNAME = settings['Server']['hostname']
        SERVER_PORT = settings['Server']['port']
        PROXY_PORT = settings['Proxy']['port']
        AWS_INSTANCE_ID = settings['AWS']['instance-id']