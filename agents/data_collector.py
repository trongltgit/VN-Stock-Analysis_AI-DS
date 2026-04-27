import yfinance as yf
import pandas as pd
import requests
from duckduckgo_search import DDGS
from datetime import datetime, timedelta
import json

class DataCollector:
    """Tầng thu thập dữ liệu: Giá chứng khoán, quỹ, tin tức"""
    
    def __init__(self):
        self.ddgs = DDGS()
    
    def get_stock_data(self, symbol: str, period="2y", interval="1d"):
        """Lấy dữ liệu giá từ Yahoo Finance"""
        try:
            # Xử lý mã quỹ VN (thêm .VN nếu cần)
            if symbol.isdigit() or symbol.upper() in ['MGF', 'VCBF', 'VESAF']:
                # Mã quỹ hoặc chứng khoán VN
                ticker = yf.Ticker(symbol.upper())
            else:
                ticker = yf.Ticker(symbol.upper())
            
            hist = ticker.history(period=period, interval=interval)
            info = ticker.info
            
            return {
                'success': True,
                'data': hist,
                'info': info,
                'symbol': symbol.upper()
            }
        except Exception as e:
            return {'success': False, 'error': str(e), 'symbol': symbol}
    
    def get_fund_data(self, fund_code: str):
        """Lấy dữ liệu quỹ mở (VCBS, VCBF, SSI...)"""
        # Mapping mã quỹ phổ biến VN
        fund_mapping = {
            'MGF': 'MGF',      # VCBF
            'VESAF': 'VESAF',  # Vietcombank
            'SSISCA': '0P0000Z8I8.F',  # SSI
            'E1VFVN30': 'E1VFVN30',
        }
        
        ticker_symbol = fund_mapping.get(fund_code.upper(), fund_code.upper())
        return self.get_stock_data(ticker_symbol)
    
    def search_market_news(self, query: str, max_results=10):
        """Tìm tin tức thị trường qua DuckDuckGo"""
        try:
            results = self.ddgs.text(
                keywords=f"{query} stock market news analysis",
                region='vn-vi',
                safesearch='off',
                max_results=max_results
            )
            return list(results)
        except Exception as e:
            return [{'error': str(e)}]
    
    def get_fundamental_data(self, symbol: str):
        """Thu thập dữ liệu cơ bản: P/E, EPS, Market Cap..."""
        try:
            ticker = yf.Ticker(symbol.upper())
            info = ticker.info
            
            fundamentals = {
                'symbol': symbol.upper(),
                'name': info.get('longName', 'N/A'),
                'sector': info.get('sector', 'N/A'),
                'industry': info.get('industry', 'N/A'),
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'forward_pe': info.get('forwardPE', 0),
                'peg_ratio': info.get('pegRatio', 0),
                'price_to_book': info.get('priceToBook', 0),
                'price_to_sales': info.get('priceToSalesTrailing12Months', 0),
                'enterprise_value': info.get('enterpriseValue', 0),
                'profit_margins': info.get('profitMargins', 0),
                'revenue_growth': info.get('revenueGrowth', 0),
                'earnings_growth': info.get('earningsGrowth', 0),
                'debt_to_equity': info.get('debtToEquity', 0),
                'current_ratio': info.get('currentRatio', 0),
                'quick_ratio': info.get('quickRatio', 0),
                'return_on_equity': info.get('returnOnEquity', 0),
                'return_on_assets': info.get('returnOnAssets', 0),
                'dividend_yield': info.get('dividendYield', 0),
                'beta': info.get('beta', 0),
                'fifty_two_week_high': info.get('fiftyTwoWeekHigh', 0),
                'fifty_two_week_low': info.get('fiftyTwoWeekLow', 0),
                'avg_volume': info.get('averageVolume', 0),
                'employees': info.get('fullTimeEmployees', 0),
                'website': info.get('website', ''),
                'summary': info.get('longBusinessSummary', 'Không có thông tin'),
            }
            return fundamentals
        except Exception as e:
            return {'error': str(e), 'symbol': symbol}
    
    def get_forex_data(self, pair: str, period="1y", interval="1d"):
        """Lấy dữ liệu tỷ giá: USDVND=X, USDJPY=X..."""
        # Chuyển đổi pair sang format Yahoo Finance
        pair_map = {
            'USD.VND': 'USDVND=X',
            'USD.JPY': 'USDJPY=X',
            'EUR.VND': 'EURVND=X',
            'EUR.USD': 'EURUSD=X',
            'GBP.USD': 'GBPUSD=X',
            'AUD.USD': 'AUDUSD=X',
        }
        yf_symbol = pair_map.get(pair.upper(), pair.upper().replace('.', ''))
        return self.get_stock_data(yf_symbol, period=period, interval=interval)