from .main import main

def init_routes(app):
    app.register_blueprint(main)
