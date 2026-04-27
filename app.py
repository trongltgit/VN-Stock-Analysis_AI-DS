from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import os
import json
from datetime import datetime, timedelta
import threading
import time

from config import Config
from agents.data_collector import DataCollector
from agents.tech_analyzer import TechnicalAnalyzer
from agents.gemini_analyzer import GeminiAnalyzer
from agents.deepseek_analyst import DeepSeekAnalyst

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# Initialize agents
collector = DataCollector()
tech_analyzer = TechnicalAnalyzer()
gemini = GeminiAnalyzer()
deepseek = DeepSeekAnalyst()

# Cleanup temp files periodically
def cleanup_temp_files():
    while True:
        time.sleep(3600)
        try:
            temp_dir = Config.TEMP_DIR
            if os.path.exists(temp_dir):
                for f in os.listdir(temp_dir):
                    filepath = os.path.join(temp_dir, f)
                    if os.path.getmtime(filepath) < time.time() - Config.MAX_TEMP_AGE:
                        os.remove(filepath)
        except Exception as e:
            print(f"Cleanup error: {e}")

cleanup_thread = threading.Thread(target=cleanup_temp_files, daemon=True)
cleanup_thread.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze_stock():
    """API phân tích chứng khoán/quỹ"""
    data = request.get_json()
    symbol = data.get('symbol', '').strip().upper()
    analysis_type = data.get('type', 'stock')
    
    if not symbol:
        return jsonify({'error': 'Vui lòng nhập mã chứng khoán'}), 400
    
    try:
        if analysis_type == 'fund':
            stock_data = collector.get_fund_data(symbol)
        else:
            stock_data = collector.get_stock_data(symbol)
        
        if not stock_data['success']:
            return jsonify({'error': f'Không tìm thấy mã {symbol}: {stock_data.get("error")}'}), 404
        
        df = stock_data['data']
        current_price = df['Close'].iloc[-1]
        
        chart_path, df_with_indicators = tech_analyzer.create_chart(df, symbol)
        tech_signals = tech_analyzer.generate_signals(df_with_indicators)
        
        fundamentals = collector.get_fundamental_data(symbol)
        gemini_analysis = gemini.analyze_fundamentals(fundamentals)
        
        news = collector.search_market_news(f"{symbol} stock", max_results=5)
        
        recommendation = deepseek.generate_investment_recommendation(
            symbol=symbol,
            fundamental_analysis=gemini_analysis,
            technical_signals=tech_signals,
            market_news=news,
            current_price=current_price
        )
        
        result = {
            'symbol': symbol,
            'current_price': round(current_price, 2),
            'currency': stock_data['info'].get('currency', 'VND'),
            'timestamp': datetime.now().isoformat(),
            'technical': {
                'chart_url': f'/charts/{os.path.basename(chart_path)}',
                'signals': tech_signals,
                'indicators': {
                    'rsi': round(df_with_indicators['RSI'].iloc[-1], 2),
                    'sma20': round(df_with_indicators['SMA20'].iloc[-1], 2),
                    'sma50': round(df_with_indicators['SMA50'].iloc[-1], 2),
                    'macd': round(df_with_indicators['MACD'].iloc[-1], 4),
                }
            },
            'fundamental': gemini_analysis,
            'recommendation': recommendation,
            'news': news[:3]
        }
        
        return jsonify(result)
        
    except Exception as e:
        import traceback
        print(f"ERROR in analyze_stock: {traceback.format_exc()}")
        return jsonify({'error': str(e), 'symbol': symbol}), 500

@app.route('/api/forex', methods=['POST'])
def analyze_forex():
    """API phân tích tỷ giá"""
    data = request.get_json()
    pair = data.get('pair', '').strip().upper()
    
    if not pair:
        return jsonify({'error': 'Vui lòng nhập cặp tiền tệ (VD: USD.VND)'}), 400
    
    try:
        forex_data = collector.get_forex_data(pair)
        
        if not forex_data['success']:
            return jsonify({'error': f'Không tìm thấy cặp {pair}'}), 404
        
        df = forex_data['data']
        current_rate = df['Close'].
