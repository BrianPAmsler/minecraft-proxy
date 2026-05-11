from contextlib import suppress
import tomllib

SERVER_HOSTNAME = 'localhost'
SERVER_PORT = 25566
PROXY_PORT = 25565
MINECRAFT_VERSION = "1.11.2"
AWS_INSTANCE_ID = ""
AUTO_SHUTDOWN_TIME = 600
ERROR_STATE_WAIT_TIME = 300
STATUS_UPDATE_INTERVAL = 30

TEST_SERVER_START_COMMAND = ""
TEST_SERVER_DIRECTORY = ""

with open("settings.toml", 'rb') as file:
    settings = tomllib.load(file)

    with suppress(KeyError):
        SERVER_HOSTNAME = settings['Server']['hostname']
        SERVER_PORT = settings['Server']['port']
        MINECRAFT_VERSION = settings['Server']['minecraft-version']
        AWS_INSTANCE_ID = settings['Server']['aws-instance-id']
        AUTO_SHUTDOWN_TIME = settings['Server']['auto-shutdown-time']
        ERROR_STATE_WAIT_TIME = settings['Server']['error-state-wait-time']
        STATUS_UPDATE_INTERVAL = settings['Server']['status-update-interval']

        PROXY_PORT = settings['Proxy']['port']

        TEST_SERVER_START_COMMAND = settings['Testing']['server-start-command']
        TEST_SERVER_DIRECTORY = settings['Testing']['server-directory']