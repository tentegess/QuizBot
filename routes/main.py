from flask import Blueprint, render_template
from .auth import Oauth


main = Blueprint('main', __name__)

@main.route('/')
def home():
    return render_template('index.html', discord_url=Oauth.discord_login_url)

@main.route('/login')
def login():
    return render_template('login.html')