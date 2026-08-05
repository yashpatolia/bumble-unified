def relay_to_other_guilds(client, config, text: str) -> None:
    """Send `text` (already formatted with its /gc or /oc chat prefix) to
    every guild's Mineflayer bot except the one it originated from."""
    for key, other_state in client.guilds_state.items():
        if key != config.key and other_state.bot:
            other_state.bot.chat(text)
