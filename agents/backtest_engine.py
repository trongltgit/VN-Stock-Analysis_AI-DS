import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Callable
import json
from dataclasses import dataclass

@dataclass
class Trade:
    entry_date: datetime
    exit_date: datetime = None
    entry_price: float = 0
    exit_price: float = 0
    shares: int = 0
    side: str = 'long'  # long/short
    pnl: float = 0
    pnl_pct: float = 0
    exit_reason: str = ''

@dataclass
class BacktestResult:
    strategy_name: str
    symbol: str
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    total_return: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_return: float
    max_drawdown: float
    sharpe_ratio: float
    trades: List[Trade]
    equity_curve: List[Dict]
    monthly_returns: Dict

class BacktestEngine:
    """Engine backtesting chiến lược giao dịch"""
    
    def __init__(self, initial_capital=100_000_000):  # 100M VND
        self.initial_capital = initial_capital
        self.results = []
    
    def run_strategy(self, df: pd.DataFrame, strategy_func: Callable, 
                    strategy_params: dict = None, symbol: str = "UNKNOWN") -> BacktestResult:
        """
        Chạy backtest một chiến lược
        
        strategy_func: Hàm nhận (df, params) -> signals DataFrame với cột 'signal' (1=mua, -1=bán, 0=giữ)
        """
        df = df.copy()
        
        # Tính tín hiệu từ chiến lược
        signals = strategy_func(df, strategy_params or {})
        
        # Merge signals vào df
        df['signal'] = signals['signal']
        df['position'] = df['signal'].shift(1).fillna(0)  # Thực hiện ở ngày hôm sau
        
        capital = self.initial_capital
        position = 0  # Số cổ phiếu đang nắm giữ
        trades = []
        equity_curve = []
        current_trade = None
        
        for i, row in df.iterrows():
            price = row['Close']
            signal = row['signal']
            date = i if isinstance(i, datetime) else pd.to_datetime(i)
            
            # Tính giá trị portfolio hiện tại
            portfolio_value = capital + (position * price)
            
            equity_curve.append({
                'date': date.isoformat(),
                'price': price,
                'portfolio_value': portfolio_value,
                'position': position,
                'signal': signal
            })
            
            # Xử lý tín hiệu
            if signal == 1 and position == 0:  # Mua
                shares = int(capital * 0.95 / price)  # Dùng 95% vốn, giữ 5% dự phòng
                if shares > 0:
                    cost = shares * price
                    capital -= cost
                    position = shares
                    current_trade = Trade(
                        entry_date=date,
                        entry_price=price,
                        shares=shares,
                        side='long'
                    )
            
            elif signal == -1 and position > 0:  # Bán
                revenue = position * price
                capital += revenue
                
                if current_trade:
                    current_trade.exit_date = date
                    current_trade.exit_price = price
                    current_trade.pnl = (price - current_trade.entry_price) * current_trade.shares
                    current_trade.pnl_pct = (price / current_trade.entry_price - 1) * 100
                    current_trade.exit_reason = 'signal'
                    trades.append(current_trade)
                    current_trade = None
                
                position = 0
        
        # Đóng vị thế cuối cùng nếu còn
        if position > 0 and current_trade:
            last_price = df['Close'].iloc[-1]
            last_date = df.index[-1]
            revenue = position * last_price
            capital += revenue
            
            current_trade.exit_date = last_date if isinstance(last_date, datetime) else pd.to_datetime(last_date)
            current_trade.exit_price = last_price
            current_trade.pnl = (last_price - current_trade.entry_price) * current_trade.shares
            current_trade.pnl_pct = (last_price / current_trade.entry_price - 1) * 100
            current_trade.exit_reason = 'end_of_data'
            trades.append(current_trade)
        
        # Tính metrics
        final_capital = capital
        total_return = (final_capital / self.initial_capital - 1) * 100
        
        winning = [t for t in trades if t.pnl > 0]
        losing = [t for t in trades if t.pnl <= 0]
        
        # Max Drawdown
        equity_values = [e['portfolio_value'] for e in equity_curve]
        peak = equity_values[0]
        max_dd = 0
        for val in equity_values:
            if val > peak:
                peak = val
            dd = (peak - val) / peak
            if dd > max_dd:
                max_dd = dd
        
        # Sharpe Ratio (giả định risk-free = 0)
        returns = []
        for i in range(1, len(equity_values)):
            daily_return = (equity_values[i] - equity_values[i-1]) / equity_values[i-1]
            returns.append(daily_return)
        
        returns_series = pd.Series(returns)
        sharpe = 0
        if returns_series.std() != 0:
            sharpe = (returns_series.mean() / returns_series.std()) * np.sqrt(252)  # Annualized
        
        # Monthly returns
        equity_df = pd.DataFrame(equity_curve)
        equity_df['date'] = pd.to_datetime(equity_df['date'])
        equity_df.set_index('date', inplace=True)
        monthly = equity_df['portfolio_value'].resample('M').last().pct_change() * 100
        
        return BacktestResult(
            strategy_name=strategy_params.get('name', 'Unknown'),
            symbol=symbol,
            start_date=df.index[0].isoformat() if hasattr(df.index[0], 'isoformat') else str(df.index[0]),
            end_date=df.index[-1].isoformat() if hasattr(df.index[-1], 'isoformat') else str(df.index[-1]),
            initial_capital=self.initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            total_trades=len(trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=(len(winning) / len(trades) * 100) if trades else 0,
            avg_return=np.mean([t.pnl_pct for t in trades]) if trades else 0,
            max_drawdown=max_dd * 100,
            sharpe_ratio=sharpe,
            trades=trades,
            equity_curve=equity_curve,
            monthly_returns=monthly.to_dict()
        )
    
    def run_multiple_strategies(self, df: pd.DataFrame, strategies: Dict[str, Callable], symbol: str):
        """So sánh nhiều chiến lược"""
        results = []
        for name, strategy in strategies.items():
            result = self.run_strategy(df, strategy, {'name': name}, symbol)
            results.append(result)
        return results

# ========== CÁC CHIẾN LƯỢC MẪU ==========

def sma_crossover_strategy(df, params):
    """Chiến lược cắt nhau SMA"""
    short_window = params.get('short', 20)
    long_window = params.get('long', 50)
    
    df['SMA_short'] = df['Close'].rolling(window=short_window).mean()
    df['SMA_long'] = df['Close'].rolling(window=long_window).mean()
    
    df['signal'] = 0
    df.loc[df['SMA_short'] > df['SMA_long'], 'signal'] = 1
    df.loc[df['SMA_short'] < df['SMA_long'], 'signal'] = -1
    
    # Chỉ lấy điểm cắt (thay đổi tín hiệu)
    df['position'] = df['signal'].diff()
    
    final_signal = pd.Series(0, index=df.index)
    final_signal[df['position'] == 2] = 1   # Short -> Long (mua)
    final_signal[df['position'] == -2] = -1 # Long -> Short (bán)
    
    df['signal'] = final_signal
    return df

def rsi_strategy(df, params):
    """Chiến lược RSI quá mua/quá bán"""
    import ta
    rsi_period = params.get('rsi_period', 14)
    oversold = params.get('oversold', 30)
    overbought = params.get('overbought', 70)
    
    df['RSI'] = ta.momentum.rsi(df['Close'], window=rsi_period)
    
    df['signal'] = 0
    df.loc[df['RSI'] < oversold, 'signal'] = 1   # Quá bán -> Mua
    df.loc[df['RSI'] > overbought, 'signal'] = -1 # Quá mua -> Bán
    
    return df

def macd_strategy(df, params):
    """Chiến lược MACD"""
    import ta
    df['MACD'] = ta.trend.macd(df['Close'])
    df['MACD_signal'] = ta.trend.macd_signal(df['Close'])
    
    df['signal'] = 0
    df.loc[df['MACD'] > df['MACD_signal'], 'signal'] = 1
    df.loc[df['MACD'] < df['MACD_signal'], 'signal'] = -1
    
    # Chỉ lấy điểm cắt
    df['position'] = df['signal'].diff()
    final_signal = pd.Series(0, index=df.index)
    final_signal[df['position'] == 2] = 1
    final_signal[df['position'] == -2] = -1
    df['signal'] = final_signal
    
    return df

def bollinger_bounce_strategy(df, params):
    """Chiến lược nảy Bollinger Bands"""
    import ta
    window = params.get('window', 20)
    std_dev = params.get('std', 2)
    
    bb = ta.volatility.BollingerBands(df['Close'], window=window, window_dev=std_dev)
    df['BB_upper'] = bb.bollinger_hband()
    df['BB_lower'] = bb.bollinger_lband()
    df['BB_middle'] = bb.bollinger_mavg()
    
    df['signal'] = 0
    # Mua khi chạm dải dưới, bán khi chạm dải trên
    df.loc[df['Close'] <= df['BB_lower'], 'signal'] = 1
    df.loc[df['Close'] >= df['BB_upper'], 'signal'] = -1
    
    return df