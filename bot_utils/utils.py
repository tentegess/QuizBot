from discord import Interaction, app_commands
import logging

def guild_only():
    def predicate(interaction: Interaction) -> bool:
        if interaction.guild is None:
            raise app_commands.CheckFailure("Ta komenda nie jest dostępna w DM.")
        return True
    return app_commands.check(predicate)


def set_logger():
    logger = logging.getLogger('discord')
    logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler(filename="./discord.log", encoding="utf-8", mode='w')
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)

    console_hanlder = logging.StreamHandler()
    console_hanlder.setLevel(logging.INFO)
    logger.addHandler(console_hanlder)

    return logger, console_hanlder