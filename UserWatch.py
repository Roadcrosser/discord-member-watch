import util
from DBInterface import DBInterface
from models import OperationStatus, CommandResponse


class UserWatch:
    def __init__(self, db_fp):
        self.db = DBInterface(db_fp)
        self.alert_requests = {}
        self.subscriptions = set()
        self.guild_subscription_channels = {}

    async def initialize(self):
        watch_data = await self.db.initialize_database()

        alerts_initialized = 0

        for a in watch_data["alert_requests"]:

            self._add_alert_request(a.user_id, a.guild_id, a.requester_id, a.channel_id)

            alerts_initialized += 1

        self.subscriptions = set(
            (s.user_id, s.guild_id) for s in watch_data["subscriptions"]
        )
        subscriptions_initialized = len(self.subscriptions)

        self.guild_subscription_channels = dict(
            [
                (c.guild_id, c.subscription_channel_id)
                for c in watch_data["guild_subscription_configs"]
            ]
        )
        configs_initialized = len(self.guild_subscription_channels)

        print(
            f"Successfully initialized {alerts_initialized} alert requests, {subscriptions_initialized} subscriptions and {configs_initialized} guild configs."
        )

    def get_guild_subscription_channel(self, guild_id):
        return self.guild_subscription_channels.get(guild_id, None)

    def _add_alert_request(self, user_id, guild_id, requester_id, channel_id):
        user_guild_pair = (user_id, guild_id)

        if not user_guild_pair in self.alert_requests:
            self.alert_requests[user_guild_pair] = {}

        self.alert_requests[user_guild_pair][requester_id] = channel_id

    async def add_alert_request(self, user_id, guild_id, requester_id, channel_id):
        row = (user_id, guild_id, requester_id, channel_id)
        user_guild_pair = (user_id, guild_id)

        prev_channel = self.alert_requests.get(user_guild_pair, {}).get(
            requester_id, None
        )
        if prev_channel:
            self.alert_requests[user_guild_pair][requester_id] = channel_id
            await self.db.update_alert_request(*row)

            return CommandResponse(OperationStatus.UPDATED, prev_channel)

        else:
            self._add_alert_request(*row)
            await self.db.insert_alert_request(*row)

            return CommandResponse(OperationStatus.INSERTED)

    async def remove_alert_request(self, user_id, guild_id, requester_id):
        row = (user_id, guild_id, requester_id)
        user_guild_pair = (user_id, guild_id)

        if self.alert_requests.get(user_guild_pair, {}).pop(requester_id, None):
            await self.db.remove_alert_request(*row)

            # do some cleanup for unfollowed user/guild pairs
            if (
                user_guild_pair in self.alert_requests
                and not self.alert_requests[user_guild_pair]
            ):
                self.alert_requests.pop(user_guild_pair)

            return CommandResponse(OperationStatus.SUCCESS)

        return CommandResponse(OperationStatus.NOTFOUND)

    async def add_subscription(self, user_id, guild_id):
        user_guild_pair = (user_id, guild_id)
        if not user_guild_pair in self.subscriptions:
            self.subscriptions.add(user_guild_pair)
            await self.db.insert_subscription(*user_guild_pair)
            return CommandResponse(OperationStatus.INSERTED)

        return CommandResponse(OperationStatus.UPDATED)

    async def remove_subscription(self, user_id, guild_id):
        user_guild_pair = (user_id, guild_id)
        if user_guild_pair in self.subscriptions:
            self.subscriptions.remove(user_guild_pair)
            await self.db.remove_subscription(*user_guild_pair)
            return CommandResponse(OperationStatus.SUCCESS)

        return CommandResponse(OperationStatus.NOTFOUND)

    async def set_guild_subscription_channel(self, guild_id, channel_id):
        prev_channel = self.get_guild_subscription_channel(guild_id)

        ret = CommandResponse(OperationStatus.INSERTED)
        db_func = self.db.insert_guild_subscription_config
        if prev_channel:

            db_func = self.db.update_guild_subscription_config
            ret = CommandResponse(OperationStatus.UPDATED, prev_channel)

        self.guild_subscription_channels[guild_id] = channel_id
        await db_func(guild_id, channel_id)
        return ret

    async def handle_user_sighting(self, user, guild, message):
        user_guild_pair = (user.id, guild.id)

        alert_requests = self.alert_requests.get(user_guild_pair, {})

        alerts_to_send = []
        if alert_requests:
            raw_alerts = {}
            for u, c in alert_requests.items():
                if not c in raw_alerts:
                    raw_alerts[c] = set()

                raw_alerts[c].add(u)

            for c in raw_alerts:
                channel = guild.get_channel(c)
                if not util.channel_accessible(channel):
                    continue
                users = []
                for u in raw_alerts[c]:
                    member = guild.get_member(u)
                    if not member:
                        continue
                    if not channel.permissions_for(member).read_messages:
                        continue
                    users.append(member)

                if users:
                    alerts_to_send.append((channel, users))

        subscription_channel = None
        if user_guild_pair in self.subscriptions:
            channel = guild.get_channel(self.get_guild_subscription_channel(guild.id))
            if util.channel_accessible(channel):
                subscription_channel = channel

        embed = None
        if alert_requests or subscription_channel:
            embed = util.build_message_embed(message)

        if subscription_channel:
            await subscription_channel.send(embed=embed)

        for c, u in alerts_to_send:
            await c.send(" ".join(f"<@{d.id}>" for d in u), embed=embed)

        for u in list(alert_requests.keys()):
            await self.remove_alert_request(*user_guild_pair, u)
