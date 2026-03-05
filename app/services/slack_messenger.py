import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


class SlackMessenger:

    def __init__(self, token: str):
        self.client = WebClient(token=token)
        self.dm_cache = {}  # user_id -> channel_id

    def get_user_id(self, email: str) -> str:
        """Resolve email to Slack user ID"""
        try:
            resp = self.client.users_lookupByEmail(email=email)
            return resp["user"]["id"]
        except SlackApiError as e:
            raise Exception(f"Could not find Slack user for {email}: {e.response['error']}")

    def get_dm_channel(self, user_id: str) -> str:
        """Open or retrieve DM channel"""
        if user_id in self.dm_cache:
            return self.dm_cache[user_id]

        try:
            resp = self.client.conversations_open(users=user_id)
            channel_id = resp["channel"]["id"]

            self.dm_cache[user_id] = channel_id
            return channel_id

        except SlackApiError as e:
            raise Exception(f"Failed to open DM with {user_id}: {e.response['error']}")

    def send_dm(self, email: str, message: str):
        """Send DM using email"""
        user_id = self.get_user_id(email)
        channel_id = self.get_dm_channel(user_id)

        try:
            self.client.chat_postMessage(
                channel=channel_id,
                text=message
            )
        except SlackApiError as e:
            raise Exception(f"Failed to send message: {e.response['error']}")