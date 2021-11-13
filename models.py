from enum import Enum, auto


class OperationStatus(Enum):
    INSERTED = auto()
    UPDATED = auto()
    SUCCESS = auto()
    NOTFOUND = auto()

    # Should I be sharing enum space for id lookups and dataset operation?
    INVALID_ID = auto()


class CommandResponse:
    def __init__(self, status, data=None):
        self.status = status
        self.data = data


class AlertRequest:
    def __init__(self, user_id, guild_id, requester_id, channel_id):
        self.user_id = user_id
        self.guild_id = guild_id
        self.requester_id = requester_id
        self.channel_id = channel_id


# You have to wonder if these two dataclasses are even needed if we're passing them from a tuple directly back to a tuple


class Subscription:
    def __init__(self, user_id, guild_id):
        self.user_id = user_id
        self.guild_id = guild_id


class GuildSubscriptionConfig:
    def __init__(self, guild_id, subscription_channel_id):
        self.guild_id = guild_id
        self.subscription_channel_id = subscription_channel_id
