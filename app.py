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
        current_rate = df['Close'].iloc[-1]
        
        chart_path, df_indicators = tech_analyzer.create_forex_chart(df, pair)
        signals = tech_analyzer.generate_signals(df_indicators)
        
        news = collector.search_market_news(
            f"{pair.split('.')[0]} {pair.split('.')[1]} exchange rate", 
            max_results=5
        )
        
        forex_analysis = deepseek.analyze_forex(
            pair=pair,
            technical_data={
                'current_rate': current_rate,
                'sma20': df_indicators['SMA20'].iloc[-1],
                'rsi': df_indicators['RSI'].iloc[-1],
                'trend': signals['trend']
            },
            macro_news=news
        )
        
        return jsonify({
            'pair': pair,
            'current_rate': round(current_rate, 4),
            'chart_url': f'/charts/{os.path.basename(chart_path)}',
            'technical_signals': signals,
            'analysis': forex_analysis,
            'news': news[:3]
        })
        
    except Exception as e:
        import traceback
        print(f"ERROR in analyze_forex: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@app.route('/charts/<path:filename>')
def serve_chart(filename):
    """Phục vụ file biểu đồ tạm"""
    return send_file(os.path.join(Config.TEMP_DIR, filename))

@app.route('/api/market-overview', methods=['GET'])
def market_overview():
    """Tổng quan thị trường VN"""
    indices = ['^VNINDEX', '^HNXINDEX', '^UPCOMINDEX']
    result = {}
    
    for idx in indices:
        try:
            data = collector.get_stock_data(idx, period="5d", interval="1d")
            if data['success']:
                df = data['data']
                result[idx] = {
                    'current': round(df['Close'].iloc[-1], 2),
                    'change': round(df['Close'].iloc[-1] - df['Close'].iloc[-2], 2),
                    'change_pct': round((df['Close'].iloc[-1] / df['Close'].iloc[-2] - 1) * 100, 2),
                    'volume': int(df['Volume'].iloc[-1])
                }
        except:
            continue
    
    return jsonify(result)

# ========== ALERT SYSTEM ==========
from agents.alert_system import PriceAlertSystem

alert_system = PriceAlertSystem(check_interval=60)
alert_system.start()

@app.route('/api/alerts', methods=['POST'])
def create_alert():
    """Tạo cảnh báo giá mới"""
    data = request.get_json()
    symbol = data.get('symbol', '').upper()
    target = data.get('target_price', 0)
    chat_id = data.get('chat_id', 0)
    condition = data.get('condition', 'above')
    
    if not all([symbol, target, chat_id]):
        return jsonify({'error': 'Thiếu thông tin'}), 400
    
    def alert_callback(**kwargs):
        print(f"ALERT TRIGGERED: {kwargs['symbol']} at {kwargs['current_price']}")
    
    alert_id = alert_system.add_alert(
        symbol=symbol,
        chat_id=chat_id,
        target_price=float(target),
        condition=condition,
        callback=alert_callback
    )
    
    return jsonify({
        'success': True,
        'alert_id': alert_id,
        'message': f'Đã tạo cảnh báo {symbol} tại {float(target):,.0f}'
    })

@app.route('/api/alerts/<chat_id>', methods=['GET'])
def get_alerts(chat_id):
    """Lấy danh sách cảnh báo của user"""
    alerts = alert_system.get_user_alerts(int(chat_id))
    return jsonify({
        'alerts': [{
            'id': a['id'],
            'symbol': a['symbol'],
            'target': a['target_price'],
            'condition': a['condition'],
            'created': a['created_at'].isoformat() if hasattr(a['created_at'], 'isoformat') else str(a['created_at']),
            'triggered': a['triggered']
        } for a in alerts]
    })

@app.route('/api/alerts/<alert_id>', methods=['DELETE'])
def delete_alert(alert_id):
    """Xóa cảnh báo"""
    alert_system.remove_alert(alert_id)
    return jsonify({'success': True})

@app.route('/api/alerts/stats', methods=['GET'])
def alert_stats():
    """Thống kê hệ thống cảnh báo"""
    return jsonify(alert_system.get_stats())

# ========== BACKTEST ==========
from agents.backtest_engine import BacktestEngine, sma_crossover_strategy, rsi_strategy, macd_strategy, bollinger_bounce_strategy
import pandas as pd

@app.route('/api/backtest', methods=['POST'])
def run_backtest():
    """Chạy backtest chiến lược"""
    data = request.get_json()
    symbol = data.get('symbol', '').upper()
    strategy_name = data.get('strategy', 'sma_crossover')
    initial_capital = data.get('initial_capital', 100_000_000)
    
    stock_data = collector.get_stock_data(symbol, period="5y")
    if not stock_data['success']:
        return jsonify({'error': 'Không lấy được dữ liệu'}), 404
    
    df = stock_data['data']
    
    strategies = {
        'sma_crossover': sma_crossover_strategy,
        'rsi': rsi_strategy,
        'macd': macd_strategy,
        'bollinger': bollinger_bounce_strategy
    }
    
    strategy_func = strategies.get(strategy_name, sma_crossover_strategy)
    params = data.get('params', {})
    params['name'] = strategy_name
    
    engine = BacktestEngine(initial_capital=initial_capital)
    result = engine.run_strategy(df, strategy_func, params, symbol)
    
    return jsonify({
        'strategy': result.strategy_name,
        'symbol': result.symbol,
        'period': f"{result.start_date} to {result.end_date}",
        'metrics': {
            'initial_capital': result.initial_capital,
            'final_capital': round(result.final_capital, 2),
            'total_return_pct': round(result.total_return, 2),
            'total_trades': result.total_trades,
            'winning_trades': result.winning_trades,
            'losing_trades': result.losing_trades,
            'win_rate_pct': round(result.win_rate, 2),
            'avg_return_per_trade_pct': round(result.avg_return, 2),
            'max_drawdown_pct': round(result.max_drawdown, 2),
            'sharpe_ratio': round(result.sharpe_ratio, 3)
        },
        'trades': [{
            'entry_date': t.entry_date.isoformat() if hasattr(t.entry_date, 'isoformat') else str(t.entry_date),
            'exit_date': t.exit_date.isoformat() if hasattr(t.exit_date, 'isoformat') else str(t.exit_date),
            'entry_price': round(t.entry_price, 2),
            'exit_price': round(t.exit_price, 2),
            'shares': t.shares,
            'pnl': round(t.pnl, 2),
            'pnl_pct': round(t.pnl_pct, 2),
            'exit_reason': t.exit_reason
        } for t in result.trades],
        'equity_curve': result.equity_curve[::5],
        'monthly_returns': {str(k): round(v, 2) for k, v in result.monthly_returns.items() if pd.notna(v)}
    })

@app.route('/api/backtest/compare', methods=['POST'])
def compare_strategies():
    """So sánh nhiều chiến lược"""
    data = request.get_json()
    symbol = data.get('symbol', '').upper()
    
    stock_data = collector.get_stock_data(symbol, period="3y")
    if not stock_data['success']:
        return jsonify({'error': 'Không lấy được dữ liệu'}), 404
    
    df = stock_data['data']
    
    strategies = {
        'SMA Crossover (20/50)': lambda d, p: sma_crossover_strategy(d, {'short': 20, 'long': 50, **p}),
        'RSI (30/70)': lambda d, p: rsi_strategy(d, {'oversold': 30, 'overbought': 70, **p}),
        'MACD Signal': macd_strategy,
        'Bollinger Bounce': bollinger_bounce_strategy
    }
    
    engine = BacktestEngine(initial_capital=100_000_000)
    results = engine.run_multiple_strategies(df, strategies, symbol)
    
    comparison = []
    for r in results:
        comparison.append({
            'strategy': r.strategy_name,
            'total_return_pct': round(r.total_return, 2),
            'win_rate_pct': round(r.win_rate, 2),
            'max_drawdown_pct': round(r.max_drawdown, 2),
            'sharpe_ratio': round(r.sharpe_ratio, 3),
            'total_trades': r.total_trades,
            'avg_return_pct': round(r.avg_return, 2)
        })
    
    comparison.sort(key=lambda x: x['total_return_pct'], reverse=True)
    
    return jsonify({
        'symbol': symbol,
        'comparison': comparison,
        'best_strategy': comparison[0]['strategy'] if comparison else None
    })

# ========== TELEGRAM BOT (OPTIONAL) ==========
# Chỉ khởi động nếu có TELEGRAM_BOT_TOKEN trong env
telegram_bot = None

def init_telegram_bot():
    """Khởi tạo Telegram bot - optional"""
    global telegram_bot
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("ℹ️ Không có TELEGRAM_BOT_TOKEN - Bỏ qua Telegram Bot")
        return
    
    try:
        from agents.telegram_bot import StockTelegramBot
        
        def analyze_callback(symbol):
            with app.test_client() as client:
                resp = client.post('/api/analyze', json={'symbol': symbol})
                return resp.get_json()
        
        telegram_bot = StockTelegramBot(token=token, analyzer_callback=analyze_callback)
        # Chạy trong thread riêng
        bot_thread = threading.Thread(target=telegram_bot.run, daemon=True)
        bot_thread.start()
        print("✅ Telegram Bot đã khởi động")
    except Exception as e:
        print(f"⚠️ Lỗi khởi động Telegram Bot: {e}")

# Khởi động bot sau khi app ready (chỉ khi không phải reloader process)
if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not os.environ.get('GUNICORN_WORKER'):
    init_telegram_bot()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
