import discord
from discord.ext import commands

from components.config.config_manager import configInstance


def is_global_admin(interaction: discord.Interaction) -> bool:
    return interaction.user.id in configInstance.data.global_administrators


def is_global_admin_text(ctx: commands.Context) -> bool:
    return ctx.author.id in configInstance.data.global_administrators
