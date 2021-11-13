import aiosqlite

from models import AlertRequest, Subscription, GuildSubscriptionConfig


class DBInterface:
    def __init__(self, db_fp):
        self.conn = lambda: aiosqlite.connect(db_fp)

    async def initialize_database(self):
        # Create tables if first start and return all channels to monitor
        async with self.conn() as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS alert_requests(
                    user_id INTEGER,
                    guild_id INTEGER,
                    requester_id INTEGER,
                    channel_id INTEGER,
                    PRIMARY KEY (user_id, guild_id, requester_id)                 
                );
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS subscriptions(
                    user_id INTEGER,
                    guild_id INTEGER,
                    PRIMARY KEY (user_id, guild_id)                 
                );
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS guild_subscription_configs(
                    guild_id INTEGER PRIMARY KEY,
                    subscription_channel_id INTEGER
                );
                """
            )
            await db.commit()

            ret = {}

            for i, u in [
                ("alert_requests", AlertRequest),
                ("subscriptions", Subscription),
                ("guild_subscription_configs", GuildSubscriptionConfig),
            ]:
                # Should I be worrying about injection here? Should I forego the loop and just manually run each query?
                async with db.execute(f"SELECT * FROM {i};") as cursor:
                    row = await cursor.fetchall()

                ret[i] = [u(*r) for r in row]

        return ret

    async def insert_alert_request(self, user_id, guild_id, requester_id, channel_id):
        async with self.conn() as db:
            await db.execute(
                """
                INSERT INTO alert_requests(user_id, guild_id, requester_id, channel_id) VALUES (?, ?, ?, ?);
                """,
                (user_id, guild_id, requester_id, channel_id),
            )
            await db.commit()

    async def update_alert_request(self, user_id, guild_id, requester_id, channel_id):
        async with self.conn() as db:
            await db.execute(
                """
                UPDATE
                    alert_requests
                SET
                    channel_id = ?
                WHERE
                    user_id = ? AND
                    guild_id = ? AND
                    requester_id = ?
                """,
                (user_id, guild_id, requester_id, channel_id),
            )
            await db.commit()

    async def remove_alert_request(self, user_id, guild_id, requester_id):
        async with self.conn() as db:
            await db.execute(
                """
                DELETE FROM
                    alert_requests
                WHERE
                    user_id = ? AND
                    guild_id = ? AND
                    requester_id = ?
                """,
                (user_id, guild_id, requester_id),
            )
            await db.commit()

    async def insert_subscription(self, user_id, guild_id):
        async with self.conn() as db:
            await db.execute(
                """
                INSERT INTO subscriptions(user_id, guild_id) VALUES (?, ?);
                """,
                (user_id, guild_id),
            )
            await db.commit()

    async def remove_subscription(self, user_id, guild_id):
        async with self.conn() as db:
            await db.execute(
                """
                DELETE FROM
                    subscriptions
                WHERE
                    user_id = ? AND
                    guild_id = ?;
                """,
                (user_id, guild_id),
            )
            await db.commit()

    async def insert_guild_subscription_config(self, guild_id, subscription_channel_id):
        async with self.conn() as db:
            await db.execute(
                """
                INSERT INTO guild_subscription_configs(guild_id, subscription_channel_id) VALUES (?, ?);
                """,
                (guild_id, subscription_channel_id),
            )
            await db.commit()

    async def update_guild_subscription_config(self, guild_id, subscription_channel_id):
        async with self.conn() as db:
            await db.execute(
                """
                UPDATE
                    guild_subscription_configs
                SET
                    subscription_channel_id = ?
                WHERE
                    guild_id = ?;
                """,
                (subscription_channel_id, guild_id),
            )
            await db.commit()
