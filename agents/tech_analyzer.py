import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
import os
import uuid
from datetime import datetime
import ta

class TechnicalAnalyzer:
    """Tầng phân tích kỹ thuật: Tính indicator, vẽ biểu đồ"""
    
    def __init__(self, temp_dir="static/charts"):
        self.temp_dir = temp_dir
        os.makedirs(temp_dir, exist_ok=True)
    
    def calculate_indicators(self, df: pd.DataFrame):
        """Tính toán các chỉ báo kỹ thuật"""
        df = df.copy()
        
        # Moving Averages
        df['SMA20'] = ta.trend.sma_indicator(df['Close'], window=20)
        df['SMA50'] = ta.trend.sma_indicator(df['Close'], window=50)
        df['SMA200'] = ta.trend.sma_indicator(df['Close'], window=200)
        df['EMA12'] = ta.trend.ema_indicator(df['Close'], window=12)
        df['EMA26'] = ta.trend.ema_indicator(df['Close'], window=26)
        
        # RSI
        df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
        
        # MACD
        macd = ta.trend.MACD(df['Close'])
        df['MACD'] = macd.macd()
        df['MACD_Signal'] = macd.macd_signal()
        df['MACD_Hist'] = macd.macd_diff()
        
        # Bollinger Bands
        bb = ta.volatility.BollingerBands(df['Close'])
        df['BB_Upper'] = bb.bollinger_hband()
        df['BB_Lower'] = bb.bollinger_lband()
        df['BB_Middle'] = bb.bollinger_mavg()
        
        # Stochastic
        df['Stoch_K'] = ta.momentum.stoch(df['High'], df['Low'], df['Close'])
        df['Stoch_D'] = ta.momentum.stoch_signal(df['High'], df['Low'], df['Close'])
        
        # Volume
        df['Volume_MA20'] = df['Volume'].rolling(20).mean()
        
        # ATR (Average True Range)
        df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'])
        
        return df
    
    def generate_signals(self, df: pd.DataFrame):
        """Tạo tín hiệu MUA/BÁN/GIỮ dựa trên indicator"""
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        signals = {
            'trend': 'NEUTRAL',
            'momentum': 'NEUTRAL',
            'volume': 'NEUTRAL',
            'overall': 'NEUTRAL',
            'score': 50,
            'details': []
        }
        
        # Trend Analysis
        if latest['Close'] > latest['SMA20'] > latest['SMA50']:
            signals['trend'] = 'BULLISH'
            signals['score'] += 15
            signals['details'].append("Giá trên SMA20 và SMA50 - Xu hướng tăng")
        elif latest['Close'] < latest['SMA20'] < latest['SMA50']:
            signals['trend'] = 'BEARISH'
            signals['score'] -= 15
            signals['details'].append("Giá dưới SMA20 và SMA50 - Xu hướng giảm")
        
        # RSI
        if latest['RSI'] > 70:
            signals['momentum'] = 'OVERBOUGHT'
            signals['score'] -= 10
            signals['details'].append(f"RSI = {latest['RSI']:.1f} > 70 - Quá mua")
        elif latest['RSI'] < 30:
            signals['momentum'] = 'OVERSOLD'
            signals['score'] += 10
            signals['details'].append(f"RSI = {latest['RSI']:.1f} < 30 - Quá bán")
        else:
            signals['details'].append(f"RSI = {latest['RSI']:.1f} - Trung tính")
        
        # MACD
        if latest['MACD'] > latest['MACD_Signal'] and prev['MACD'] <= prev['MACD_Signal']:
            signals['details'].append("MACD cắt lên tín hiệu - MUA")
            signals['score'] += 10
        elif latest['MACD'] < latest['MACD_Signal'] and prev['MACD'] >= prev['MACD_Signal']:
            signals['details'].append("MACD cắt xuống tín hiệu - BÁN")
            signals['score'] -= 10
        
        # Bollinger Bands
        if latest['Close'] >= latest['BB_Upper']:
            signals['details'].append("Giá chạm biên trên Bollinger - Có thể điều chỉnh")
            signals['score'] -= 5
        elif latest['Close'] <= latest['BB_Lower']:
            signals['details'].append("Giá chạm biên dưới Bollinger - Có thể hồi phục")
            signals['score'] += 5
        
        # Overall signal
        if signals['score'] >= 70:
            signals['overall'] = 'STRONG_BUY'
        elif signals['score'] >= 55:
            signals['overall'] = 'BUY'
        elif signals['score'] <= 30:
            signals['overall'] = 'STRONG_SELL'
        elif signals['score'] <= 45:
            signals['overall'] = 'SELL'
        else:
            signals['overall'] = 'HOLD'
        
        return signals
    
    def create_chart(self, df: pd.DataFrame, symbol: str, chart_type='candlestick'):
        """Tạo biểu đồ tương tác với Plotly"""
        df = self.calculate_indicators(df)
        
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=[0.6, 0.2, 0.2],
            subplot_titles=(f'{symbol} - Phân tích kỹ thuật', 'Volume', 'RSI / MACD')
        )
        
        # Main chart - Candlestick
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name='Giá',
            increasing_line_color='#26a69a',
            decreasing_line_color='#ef5350'
        ), row=1, col=1)
        
        # Moving Averages
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA20'], 
                                line=dict(color='#2196F3', width=1), 
                                name='SMA20'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA50'], 
                                line=dict(color='#FF9800', width=1), 
                                name='SMA50'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_Upper'], 
                                line=dict(color='gray', width=1, dash='dash'), 
                                name='BB Upper'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_Lower'], 
                                line=dict(color='gray', width=1, dash='dash'), 
                                name='BB Lower'), row=1, col=1)
        
        # Volume
        colors = ['#26a69a' if df['Close'].iloc[i] >= df['Open'].iloc[i] 
                 else '#ef5350' for i in range(len(df))]
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], 
                            marker_color=colors, name='Volume'), row=2, col=1)
        
        # RSI
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], 
                                line=dict(color='#9C27B0', width=2), 
                                name='RSI'), row=3, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
        
        # MACD
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], 
                                line=dict(color='#2196F3', width=1), 
                                name='MACD'), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD_Signal'], 
                                line=dict(color='#FF9800', width=1), 
                                name='Signal'), row=3, col=1)
        
        fig.update_layout(
            title=f'Phân tích kỹ thuật {symbol}',
            yaxis_title='Giá',
            xaxis_rangeslider_visible=False,
            height=800,
            template='plotly_white',
            showlegend=True,
            hovermode='x unified'
        )
        
        # Save to file
        chart_id = str(uuid.uuid4())[:8]
        filepath = os.path.join(self.temp_dir, f"{symbol}_{chart_id}.html")
        fig.write_html(filepath, full_html=False, include_plotlyjs='cdn')
        
        return filepath, df
    
    def create_forex_chart(self, df: pd.DataFrame, pair: str):
        """Biểu đồ chuyên biệt cho tỷ giá"""
        df = self.calculate_indicators(df)
        
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.1,
            row_heights=[0.7, 0.3],
            subplot_titles=(f'{pair} - Tỷ giá & Xu hướng', 'Biến động (ATR)')
        )
        
        # Line chart cho tỷ giá (không có OHLC đầy đủ)
        fig.add_trace(go.Scatter(
            x=df.index, y=df['Close'],
            line=dict(color='#2196F3', width=2),
            name='Tỷ giá',
            fill='tozeroy',
            fillcolor='rgba(33, 150, 243, 0.1)'
        ), row=1, col=1)
        
        # SMA
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA20'], 
                                line=dict(color='#FF9800', width=1), 
                                name='SMA20'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA50'], 
                                line=dict(color='#4CAF50', width=1), 
                                name='SMA50'), row=1, col=1)
        
        # Bollinger Bands
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_Upper'], 
                                line=dict(color='gray', width=1, dash='dash'), 
                                name='BB Upper'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_Lower'], 
                                line=dict(color='gray', width=1, dash='dash'), 
                                name='BB Lower'), row=1, col=1)
        
        # ATR - Biến động
        fig.add_trace(go.Bar(x=df.index, y=df['ATR'], 
                            marker_color='#9C27B0', name='ATR'), row=2, col=1)
        
        fig.update_layout(
            title=f'Phân tích tỷ giá {pair}',
            height=700,
            template='plotly_white',
            showlegend=True,
            hovermode='x unified'
        )
        
        chart_id = str(uuid.uuid4())[:8]
        filepath = os.path.join(self.temp_dir, f"forex_{pair.replace('.', '_')}_{chart_id}.html")
        fig.write_html(filepath, full_html=False, include_plotlyjs='cdn')
        
        return filepath, df