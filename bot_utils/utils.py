from discord import Interaction, app_commands

def guild_only():
    def predicate(interaction: Interaction) -> bool:
        if interaction.guild is None:
            raise app_commands.AppCommandError("Ta komenda nie jest dostępna w DM.")
        return True
    return app_commands.check(predicate)