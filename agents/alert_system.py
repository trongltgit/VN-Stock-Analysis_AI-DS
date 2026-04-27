import asyncio
import threading
import time
from datetime import datetime, timedelta
from collections import defaultdict
import yfinance as yf
from typing import Callable

class PriceAlertSystem:
    """Hệ thống cảnh báo giá real-time với WebSocket simulation"""
    
    def __init__(self, check_interval=60):
        self.alerts = defaultdict(list)  # {symbol: [{chat_id, target, condition, callback}]}
        self.running = False
        self.check_interval = check_interval
        self.price_cache = {}  # Cache giá gần nhất
        self.alert_history = []  # Lịch sử cảnh báo
        self._thread = None
    
    def add_alert(self, symbol: str, chat_id: int, target_price: float, 
                  condition: str = 'above', callback: Callable = None, 
                  alert_type: str = 'price'):
        """
        Thêm cảnh báo mới
        
        condition: 'above' (vượt lên), 'below' (xuống dưới), 'percent_change'
        alert_type: 'price', 'percent', 'volume_spike', 'rsi_extreme'
        """
        alert = {
            'id': f"{chat_id}_{symbol}_{int(time.time())}",
            'chat_id': chat_id,
            'symbol': symbol.upper(),
            'target_price': target_price,
            'condition': condition,
            'created_at': datetime.now(),
            'triggered': False,
            'callback': callback,
            'type': alert_type
        }
        self.alerts[symbol.upper()].append(alert)
        return alert['id']
    
    def remove_alert(self, alert_id: str):
        """Xóa cảnh báo theo ID"""
        for symbol, alerts in self.alerts.items():
            self.alerts[symbol] = [a for a in alerts if a['id'] != alert_id]
    
    def get_user_alerts(self, chat_id: int):
        """Lấy danh sách cảnh báo của user"""
        user_alerts = []
        for symbol, alerts in self.alerts.items():
            for alert in alerts:
                if alert['chat_id'] == chat_id:
                    user_alerts.append(alert)
        return user_alerts
    
    def _check_price(self, symbol: str):
        """Kiểm tra giá hiện tại"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d", interval="1m")
            if not data.empty:
                return data['Close'].iloc[-1]
            return None
        except:
            return self.price_cache.get(symbol)
    
    def _evaluate_alerts(self):
        """Đánh giá và trigger cảnh báo"""
        symbols_to_check = list(self.alerts.keys())
        
        for symbol in symbols_to_check:
            current_price = self._check_price(symbol)
            if current_price is None:
                continue
            
            self.price_cache[symbol] = current_price
            
            for alert in self.alerts[symbol]:
                if alert['triggered']:
                    continue
                
                triggered = False
                reason = ""
                
                if alert['type'] == 'price':
                    if alert['condition'] == 'above' and current_price >= alert['target_price']:
                        triggered = True
                        reason = f"Giá {current_price:,.0f} đã vượt mục tiêu {alert['target_price']:,.0f}"
                    elif alert['condition'] == 'below' and current_price <= alert['target_price']:
                        triggered = True
                        reason = f"Giá {current_price:,.0f} đã xuống dưới mục tiêu {alert['target_price']:,.0f}"
                
                elif alert['type'] == 'percent_change':
                    # So sánh với giá khi tạo alert (cần lưu giá reference)
                    pass
                
                if triggered:
                    alert['triggered'] = True
                    alert['triggered_at'] = datetime.now()
                    alert['trigger_price'] = current_price
                    
                    # Gọi callback
                    if alert['callback']:
                        try:
                            alert['callback'](
                                chat_id=alert['chat_id'],
                                symbol=symbol,
                                current_price=current_price,
                                target_price=alert['target_price'],
                                reason=reason,
                                alert_id=alert['id']
                            )
                        except Exception as e:
                            print(f"Callback error: {e}")
                    
                    # Lưu lịch sử
                    self.alert_history.append({
                        'timestamp': datetime.now().isoformat(),
                        'symbol': symbol,
                        'chat_id': alert['chat_id'],
                        'trigger_price': current_price,
                        'reason': reason
                    })
    
    def _monitor_loop(self):
        """Vòng lặp giám sát"""
        while self.running:
            try:
                self._evaluate_alerts()
                time.sleep(self.check_interval)
            except Exception as e:
                print(f"Alert monitor error: {e}")
                time.sleep(self.check_interval)
    
    def start(self):
        """Bắt đầu giám sát"""
        if not self.running:
            self.running = True
            self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._thread.start()
            print("🔔 Price Alert System started")
    
    def stop(self):
        """Dừng giám sát"""
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)
    
    def get_stats(self):
        """Thống kê hệ thống"""
        total = sum(len(a) for a in self.alerts.values())
        triggered = sum(1 for alerts in self.alerts.values() for a in alerts if a['triggered'])
        return {
            'total_alerts': total,
            'active_alerts': total - triggered,
            'triggered_alerts': triggered,
            'monitored_symbols': len(self.alerts),
            'last_check': datetime.now().isoformat()
        }