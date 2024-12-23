import os
from datetime import datetime, timezone, timedelta
import aiohttp
from bson import ObjectId
from dotenv import load_dotenv
from config.config import session_collection
from model.session_model import SessionModel

load_dotenv()


class Oauth:
    client_id = os.environ.get('DISCORD_CLIENT_ID')
    client_secret = os.environ.get('DISCORD_CLIENT_SECRET')
    redirect_uri = 'http://127.0.0.1:5000/login'
    scope = 'identify%20email%20guilds'
    discord_login_url = f'https://discord.com/oauth2/authorize?client_id={client_id}&response_type=code&redirect_uri=http%3A%2F%2F127.0.0.1%3A5000%2Flogin&scope=identify+guilds+email'
    discord_token_url = 'https://discord.com/api/oauth2/token'
    discord_api_url = 'https://discord.com/api'
    session: aiohttp.ClientSession | None
    auth = aiohttp.BasicAuth(str(client_id), client_secret)

    async def setup(self):
        self.session = aiohttp.ClientSession()

    async def get_user(self, token):
        header = {"Authorization": f"Bearer {token}"}
        async with self.session.get(self.discord_api_url + '/users/@me', headers=header) as response:
            return await response.json()

    async def get_guilds(self, token):
        header = {"Authorization": f"Bearer {token}"}
        async with self.session.get(self.discord_api_url + '/users/@me/guilds', headers=header) as response:
            return await response.json()

    async def get_token_response(self, code=None, refresh_token=None):
        if not refresh_token:
            data = {
                'client_id': Oauth.client_id,
                'client_secret': Oauth.client_secret,
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': Oauth.redirect_uri,
                'scope': Oauth.scope
            }
        else:
            data = {
                'client_id': Oauth.client_id,
                'client_secret': Oauth.client_secret,
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token
            }

        response = await self.session.post(self.discord_api_url + '/oauth2/token', data=data)
        json_response = await response.json()

        access_token = json_response.get('access_token')
        refresh_token = json_response.get('refresh_token')
        expires_in = json_response.get('expires_in')

        if not access_token or not refresh_token:
            return None

        return access_token, refresh_token, expires_in

    async def revoke_token(self, token):
        async with self.session.post(
                self.discord_api_url + '/oauth2/token/revoke',
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={"token": token},
                auth=self.auth
        ) as response:
            response.raise_for_status()

    async def reload(self, session_id, refresh_token):
        response = await self.get_token_response(refresh_token=refresh_token)
        if not response:
            return False

        token, refresh_token, expires_in = response
        session_collection.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {
                'token': token,
                'refresh_token': refresh_token,
                'token_expires_at': datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            }},
        )
        return True

api = Oauth()