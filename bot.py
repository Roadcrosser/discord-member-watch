import datetime
import traceback
import sys

import disnake as discord

from disnake.ext import commands

from UserWatch import UserWatch
from models import OperationStatus
import util

from yaml import load

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

with open("config.yml", "r") as o:
    config = load(o.read(), Loader=Loader)


bot = commands.Bot(
    intents=discord.Intents(members=True, guilds=True, guild_messages=True)
)

bot.timestamp = None
bot.userwatch = UserWatch(config["DATABASE_FILEPATH"])


@bot.event
async def on_ready():
    print(f"Running on {bot.user.name}#{bot.user.discriminator} ({bot.user.id})")
    if not bot.timestamp:
        await bot.userwatch.initialize()

        bot.timestamp = (
            datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).timestamp()
        )


@bot.event
async def on_message(message):
    # Wait for bot initialization to complete before accepting inputs
    if not bot.timestamp:
        return

    # Ignore DMs
    if not isinstance(message.channel, discord.abc.GuildChannel):
        return

    # Ignore bot accounts
    if message.author.bot:
        return

    await bot.userwatch.handle_user_sighting(message.author, message.guild, message)


def has_manage_guild(ctx):
    return (
        bot.timestamp
        and ctx.guild
        and (
            ctx.guild.owner.id == ctx.user.id
            or ctx.guild.get_member(ctx.user.id).guild_permissions.manage_guild
        )
    )


def has_manage_roles(ctx):
    return (
        bot.timestamp
        and ctx.guild
        and (
            ctx.guild.owner.id == ctx.user.id
            or ctx.guild.get_member(ctx.user.id).guild_permissions.manage_roles
        )
    )


@bot.slash_command()
async def alert(ctx):
    pass


@alert.sub_command(
    name="add",
    # description="Request to be alerted when a specified user speaks."
)
@commands.check(has_manage_roles)
async def add_alert(
    ctx,
    user: str = commands.Param(
        # description="ID or @mention of the user to track."
    ),
):
    user_search = util.get_user(ctx, user)

    if user_search.status != OperationStatus.SUCCESS:
        await ctx.response.send_message(f"Error: {user_search.data}")
        return

    u = user_search.data

    res = await bot.userwatch.add_alert_request(
        u.id, ctx.guild.id, ctx.author.id, ctx.channel.id, ctx.id
    )

    response = f"Alright, I will notify you here {{}}the next time I see <@{u.id}> say something."
    previous_channel_msg = ""

    if res.status == OperationStatus.UPDATED:
        if res.data == ctx.channel.id:
            response = f"{{}}I am already monitoring <@{u.id}> for you here."
        else:
            previous_channel_msg = f"(instead of <#{res.data}>) "

    response = response.format(previous_channel_msg)

    await ctx.response.send_message(response)


@alert.sub_command(
    name="cancel",
    # description="Cancel a previous alert request."
)
@commands.check(has_manage_roles)
async def cancel_alert(
    ctx,
    user: str = commands.Param(
        # description="ID or @mention of the user to stop tracking"
    ),
):
    user_search = util.get_user(None, user)

    if user_search.status != OperationStatus.SUCCESS:
        await ctx.response.send_message(f"Error: {user_search.data}")
        return

    u = user_search.data

    res = await bot.userwatch.remove_alert_request(u, ctx.guild.id, ctx.author.id)

    response = f"I am not currently monitoring that user for you."

    if res.status == OperationStatus.SUCCESS:
        response = f"Alright, I will stop monitoring <@{u}> for you."

    await ctx.response.send_message(response)


@bot.slash_command()
async def subscription(ctx):
    pass


@subscription.sub_command(
    name="start",
    # description="Subscribe to a user's messages"
)
@commands.check(has_manage_guild)
async def add_subscription(
    ctx,
    user: str = commands.Param(
        # description="ID or @mention of the user to subscribe to"
    ),
):
    user_search = util.get_user(ctx, user)

    if user_search.status != OperationStatus.SUCCESS:
        await ctx.response.send_message(f"Error: {user_search.data}")
        return

    u = user_search.data

    res = await bot.userwatch.add_subscription(u.id, ctx.guild.id)

    subscription_channel = bot.userwatch.get_guild_subscription_channel(ctx.guild.id)

    destination = "the ether, or at least until a subscription channel is set up"
    if subscription_channel:
        destination = f"<#{subscription_channel}>"

    response = f"Alright, I will now forward messages from <@{u.id}> to {destination}."
    if res.status == OperationStatus.UPDATED:
        response = f"You are already subscribed to messages from <@{u.id}>."

    await ctx.response.send_message(response)


@subscription.sub_command(
    name="stop",
    # description="Unsubscribe from a user's messages"
)
@commands.check(has_manage_guild)
async def remove_subscription(
    ctx,
    user: str = commands.Param(
        # description="ID or @mention of the user to unsubscribe from"
    ),
):
    user_search = util.get_user(None, user)

    if user_search.status != OperationStatus.SUCCESS:
        await ctx.response.send_message(f"Error: {user_search.data}")
        return

    u = user_search.data

    res = await bot.userwatch.remove_subscription(u, ctx.guild.id)

    response = f"Alright, I will no longer forward messages from <@{u}>."
    if res.status == OperationStatus.NOTFOUND:
        response = f"I am not currently forwarding messages from that user."

    await ctx.response.send_message(response)


@subscription.sub_command(
    name="set",
    # description="Set a channel to forward subscriptions to"
)
@commands.check(has_manage_guild)
async def set_subscription_channel(
    ctx,
    channel: discord.TextChannel = commands.Param(
        # description="Select a channel to forward subscriptions to."
    ),
):

    res = await bot.userwatch.set_guild_subscription_channel(ctx.guild.id, channel.id)

    response = f"Alright, I will now forward messages from subscribed users to <#{channel.id}>{{}}."
    previous_channel_msg = ""

    if res.status == OperationStatus.UPDATED:
        if res.data == channel.id:
            response = (
                f"{{}}I am already forwarding messages from subscribed users there."
            )
        else:
            previous_channel_msg = f" (instead of <#{res.data}>)"

    response = response.format(previous_channel_msg)

    await ctx.response.send_message(response)


@add_alert.error
@cancel_alert.error
@add_subscription.error
@remove_subscription.error
@set_subscription_channel.error
async def process_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        await ctx.response.send_message(
            f"Error: Insufficient permissions.", ephemeral=True
        )
        return

    print(
        "".join(traceback.TracebackException.from_exception(error).format()),
        file=sys.stderr,
    )
    await ctx.response.send_message("An error occured. Please alert the maintainer.")


bot.run(config["TOKEN"])
