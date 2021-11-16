from disnake.ext.commands.core import Command
from models import OperationStatus, CommandResponse
import textwrap
import disnake as discord


def channel_accessible(channel):
    return (
        channel
        and channel.permissions_for(channel.guild.me).send_messages
        and channel.permissions_for(channel.guild.me).embed_links
    )


def textify_embed(embed, limit=40, padding=0, pad_first_line=True):
    text_proc = []
    title = ""
    if embed.title:
        title += embed.title
        if embed.url:
            title += " - "
    if embed.url:
        title += embed.url
    if not title and embed.author:
        title = embed.author.name
    if title:
        text_proc += [title, ""]
    if embed.description:
        text_proc += [embed.description, ""]
    if embed.thumbnail:
        text_proc += ["Thumbnail: " + embed.thumbnail.url, ""]
    for f in embed.fields:
        text_proc += [
            f.name
            + (
                ":"
                if not f.name.endswith(("!", ")", "}", "-", ":", ".", "?", "%", "$"))
                else ""
            ),
            *f.value.split("\n"),
            "",
        ]
    if embed.image:
        text_proc += ["Image: " + embed.image.url, ""]
    if embed.footer:
        text_proc += [embed.footer.text, ""]

    text_proc = [textwrap.wrap(t, width=limit) for t in text_proc]

    texts = []

    for tt in text_proc:
        if not tt:
            tt = [""]
        for t in tt:
            texts += [t + " " * (limit - len(t))]

    ret = " " * (padding * pad_first_line) + "╓─" + "─" * limit + "─╮"

    for t in texts[:-1]:
        ret += "\n" + " " * padding + "║ " + t + " │"

    ret += "\n" + " " * padding + "╙─" + "─" * limit + "─╯"

    return ret


def build_jump_view(guild, channel, message_ids):
    view = discord.ui.View()

    for m in message_ids:
        if m:
            view.add_item(
                discord.ui.Button(
                    label="\u200b",
                    url=f"https://discord.com/channels/{guild.id}/{channel.id}/{m}",
                )
            )

    return view


def build_message_embed(message):
    embed = (
        discord.Embed(
            title="\🔗",
            url=message.jump_url,
            description=message.content,
            color=message.author.color,
            timestamp=message.created_at,
        )
        .set_author(
            name=f"{message.author.name}#{message.author.discriminator}",
            icon_url=message.author.display_avatar.replace(
                size=1024,
                format="png",
            ).url,
        )
        .set_footer(text=f"#{message.channel.name} • {message.author.id}")
    )

    for e in message.embeds:
        if e.type == "rich":
            embed.add_field(
                name="Embed",
                value="```\n{}\n```".format(textify_embed(e, limit=35)),
            )
    for a in message.attachments:
        embed.add_field(name="Attachment", value=a.url)

    return embed


def get_user(ctx, user):
    try:
        u = int(user.strip("<@!>"))
    except:
        return CommandResponse(OperationStatus.INVALID_ID, "Invalid user.")

    # ctx not passed if we are not resolving the member
    if ctx:
        u = ctx.guild.get_member(u)
        if not u:
            return CommandResponse(
                OperationStatus.NOTFOUND, "No user with that ID in the server."
            )
        if u.bot:
            return CommandResponse(
                OperationStatus.NOTFOUND, "Please specify a Human instead of a robot."
            )

    return CommandResponse(OperationStatus.SUCCESS, u)
