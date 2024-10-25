import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'gT7E%eS2DBFX')
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/optinetsim')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', '=pMpR!JjZV!N')
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour
