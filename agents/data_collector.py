import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timedelta
import json

class DataCollector:
    """Tầng thu thập dữ liệu: Giá chứng khoán, quỹ, tin tức"""
    
    def __init__(self):
        self.ddgs = None  # Khởi tạo lazy để tránh lỗi boot
    
    def _get_ddgs(self):
        """Lazy init DDGS để tránh lỗi khởi động"""
        if self.ddgs is None:
            try:
                from duckduckgo_search import DDGS
                self.ddgs = DDGS()
            except Exception as e:
                print(f"DDGS init warning: {e}")
                self.ddgs = False  # Đánh dấu failed
        return self.ddgs
    
    def get_stock_data(self, symbol: str, period="2y", interval="1d"):
        """Lấy dữ liệu giá từ Yahoo Finance"""
        try:
            if symbol.isdigit() or symbol.upper() in ['MGF', 'VCBF', 'VESAF']:
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
        """Lấy dữ liệu quỹ mở"""
        fund_mapping = {
            'MGF': 'MGF',
            'VESAF': 'VESAF',
            'SSISCA': '0P0000Z8I8.F',
            'E1VFVN30': 'E1VFVN30',
        }
        ticker_symbol = fund_mapping.get(fund_code.upper(), fund_code.upper())
        return self.get_stock_data(ticker_symbol)
    
    def search_market_news(self, query: str, max_results=10):
        """Tìm tin tức thị trường qua DuckDuckGo"""
        ddgs = self._get_ddgs()
        if ddgs is False:
            # Fallback: trả về empty list nếu DDGS lỗi
            print(f"DDGS not available, skipping news search for: {query}")
            return []
        
        try:
            results = ddgs.text(
                keywords=f"{query} stock market news analysis",
                region='vn-vi',
                safesearch='off',
                max_results=max_results
            )
            return list(results)
        except Exception as e:
            print(f"News search error: {e}")
            return []
    
    def get_fundamental_data(self, symbol: str):
        """Thu thập dữ liệu cơ bản"""
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
        """Lấy dữ liệu tỷ giá"""
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
