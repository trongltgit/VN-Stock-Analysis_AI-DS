import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Keys (điền vào .env)
    GROQ_API_KEY = os.getenv("GROQ_API_KEY_STOCK", "")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY_STOCK", "")
    
    # Groq Models
    GROQ_MODEL = "deepseek-r1-distill-llama-70b"  # Free tier Groq
    
    # Gemini
    GEMINI_MODEL = "gemini-1.5-pro-latest"
    
    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB upload limit
    
    # Render Free Tier Optimization
    TEMP_DIR = "static/charts"
    MAX_TEMP_AGE = 3600  # Xóa file sau 1 giờ
    
    # Yahoo Finance
    YF_PERIOD = "2y"
    YF_INTERVAL = "1d"
    
    # Analysis Settings
    TECH_INDICATORS = ['SMA20', 'SMA50', 'RSI', 'MACD', 'BB', 'Volume']
    
    @staticmethod
    def init_app(app):
        pass