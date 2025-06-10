from flask import Flask
from flask_cors import CORS
from src.optinetsim_backend.app.config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Register blueprints or resources here
    from src.optinetsim_backend.app.routes import api_init_app
    app = api_init_app(app)

    # Enable CORS
    CORS(app)

    return app
