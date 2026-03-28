import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "bot_database.db")
