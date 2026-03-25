import discord

from components.config.config_manager import configInstance

def is_global_admin(interaction: discord.Interaction) -> bool:
    return interaction.user.id in configInstance.data.global_administrators