import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
load_dotenv()   


SLACK_TOKEN = os.environ["SLACK_BOT_TOKEN"]

client = WebClient(token=SLACK_TOKEN)


def send_dm(user_id, message):

    try:
        # Open DM channel
        response = client.conversations_open(users=user_id)

        channel_id = response["channel"]["id"]

        # Send message
        client.chat_postMessage(
            channel=channel_id,
            text=message
        )

        print("Message sent!")

    except SlackApiError as e:
        print("Error:", e.response["error"])


send_dm("U09F4B0V6LT", "Hello from my Python automation!")