import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY_STOCK", "")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY_STOCK", "")
    GROQ_MODEL = "deepseek-r1-distill-llama-70b"
    GEMINI_MODEL = "gemini-1.5-pro-latest"
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    TEMP_DIR = "static/charts"
    MAX_TEMP_AGE = 3600
    YF_PERIOD = "2y"
    YF_INTERVAL = "1d"
    TECH_INDICATORS = ['SMA20', 'SMA50', 'RSI', 'MACD', 'BB', 'Volume']
    
    @staticmethod
    def init_app(app):
        pass
