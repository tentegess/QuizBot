import requests
import os


class Oauth:
    client_id = os.getenv('DISCORD_CLIENT_ID')
    client_secret = os.getenv('DISCORD_CLIENT_SECRET')
    redirect_uri = 'https://127.0.0.1:5000/login'
    scope = 'identify%20email%20guilds'
    discord_login_url = 'https://discord.com/oauth2/authorize?client_id=1308514751026036847&response_type=code&redirect_uri=http%3A%2F%2F127.0.0.1%3A5000%2Flogin&scope=identify+guilds+email'
    discord_token_url = 'https://discord.com/api/oauth2/token'
    discord_api_url = 'https://discord.com/api'