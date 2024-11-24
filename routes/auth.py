import requests
import os
from dotenv import load_dotenv

load_dotenv()


class Oauth:
    client_id = os.environ.get('DISCORD_CLIENT_ID')
    client_secret = os.environ.get('DISCORD_CLIENT_SECRET')
    redirect_uri = 'http://127.0.0.1:5000/login'
    scope = 'identify%20email%20guilds'
    discord_login_url = f'https://discord.com/oauth2/authorize?client_id={client_id}&response_type=code&redirect_uri=http%3A%2F%2F127.0.0.1%3A5000%2Flogin&scope=identify+guilds+email'
    discord_token_url = 'https://discord.com/api/oauth2/token'
    discord_api_url = 'https://discord.com/api'

    @staticmethod
    def get_access_token(code):
        data = {
            'client_id': Oauth.client_id,
            'client_secret': Oauth.client_secret,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': Oauth.redirect_uri,
            'scope': Oauth.scope
        }

        response = requests.post(url=Oauth.discord_token_url, data=data).json()
        return response.get('access_token')

    @staticmethod
    def get_user_json(access_token):
        url = f'{Oauth.discord_api_url}/users/@me'
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        user_object = requests.get(url=url, headers=headers).json()
        return user_object