from flask import Blueprint, render_template, request, session
from .auth import Oauth


main = Blueprint('main', __name__)

@main.route('/')
async def home():
    return render_template('index.html', discord_url=Oauth.discord_login_url)

@main.route('/login')
async def login():
    code = request.args.get("code")

    access_token = Oauth.get_access_token(code)
    session["token"] = access_token

    user = Oauth.get_user_json(access_token)
    user_name, user_id = user.get('username'), user.get('id')

    return f"Success, {user_name}, {user_id}"