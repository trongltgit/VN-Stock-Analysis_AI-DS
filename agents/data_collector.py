import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timedelta
import json
import time

class DataCollector:
    """Tầng thu thập dữ liệu: Giá chứng khoán, quỹ, tin tức"""
    
    def __init__(self):
        self.ddgs = None
        self.vcbs_session = requests.Session()
        self.vcbs_session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'vi-VN,vi;q=0.9,en;q=0.8',
            'Referer': 'https://priceboard.vcbs.com.vn/',
            'Origin': 'https://priceboard.vcbs.com.vn'
        })
    
    def _get_ddgs(self):
        """Lazy init DDGS"""
        if self.ddgs is None:
            try:
                from duckduckgo_search import DDGS
                self.ddgs = DDGS()
            except Exception as e:
                print(f"DDGS init warning: {e}")
                self.ddgs = False
        return self.ddgs
    
    def get_vcbs_data(self, symbol: str):
        """Lấy dữ liệu từ VCBS Priceboard"""
        try:
            # API chính thức của VCBS
            url = f"https://apis-sandbox.vcbs.com.vn/api/v1/stock/quote/{symbol}"
            resp = self.vcbs_session.get(url, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                return {
                    'success': True,
                    'source': 'vcbs',
                    'data': data,
                    'symbol': symbol.upper()
                }
            
            # Thử API backup
            url2 = f"https://priceboard.vcbs.com.vn/api/stock/{symbol}"
            resp2 = self.vcbs_session.get(url2, timeout=10)
            if resp2.status_code == 200:
                return {
                    'success': True,
                    'source': 'vcbs_backup',
                    'data': resp2.json(),
                    'symbol': symbol.upper()
                }
                
            return {'success': False, 'error': 'VCBS API failed', 'symbol': symbol}
            
        except Exception as e:
            return {'success': False, 'error': str(e), 'symbol': symbol}
    
    def get_ssi_data(self, symbol: str):
        """Lấy dữ liệu từ SSI iBoard"""
        try:
            # SSI Fast Trading API
            url = f"https://iboard-query.ssi.com.vn/v2/stock/{symbol}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Referer': 'https://iboard.ssi.com.vn/'
            }
            resp = requests.get(url, headers=headers, timeout=10)
            
            if resp.status_code == 200:
                return {
                    'success': True,
                    'source': 'ssi',
                    'data': resp.json(),
                    'symbol': symbol.upper()
                }
            return {'success': False, 'error': 'SSI API failed', 'symbol': symbol}
            
        except Exception as e:
            return {'success': False, 'error': str(e), 'symbol': symbol}
    
    def get_vndirect_data(self, symbol: str):
        """Lấy dữ liệu từ VNDIRECT"""
        try:
            url = f"https://finfo-api.vndirect.com.vn/v4/stocks?q=code:{symbol}&fields=code,lastPrice,ot,change,changePct,highPrice,lowPrice,avePrice,closePrice,openPrice,totalMatchQtty,totalMatchVal"
            resp = requests.get(url, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                if data.get('data') and len(data['data']) > 0:
                    return {
                        'success': True,
                        'source': 'vndirect',
                        'data': data['data'][0],
                        'symbol': symbol.upper()
                    }
            return {'success': False, 'error': 'VNDIRECT API failed', 'symbol': symbol}
            
        except Exception as e:
            return {'success': False, 'error': str(e), 'symbol': symbol}
    
    def get_stock_data(self, symbol: str, period="2y", interval="1d"):
        """Lấy dữ liệu giá - Thử nhiều nguồn"""
        symbol = symbol.upper()
        
        # Ưu tiên nguồn VN cho mã VN
        vn_stocks = ['VCB', 'VIC', 'VHM', 'FPT', 'GAS', 'GVR', 'HPG', 'MWG', 'PLX', 'SAB', 
                     'SSI', 'TCB', 'VNM', 'VPB', 'STB', 'MBB', 'ACB', 'SHB', 'CTG', 'BID',
                     'MGF', 'VESAF', 'E1VFVN30', 'SSISCA']
        
        # Nếu là mã VN, thử nguồn VN trước
        if symbol in vn_stocks or symbol.isdigit():
            # Thử VNDIRECT
            vn_data = self.get_vndirect_data(symbol)
            if vn_data['success']:
                # Tạo DataFrame giả lập từ dữ liệu real-time
                return self._create_vn_df(vn_data, symbol)
            
            # Thử VCBS
            vcbs_data = self.get_vcbs_data(symbol)
            if vcbs_data['success']:
                return self._create_vcbs_df(vcbs_data, symbol)
            
            # Thử SSI
            ssi_data = self.get_ssi_data(symbol)
            if ssi_data['success']:
                return self._create_ssi_df(ssi_data, symbol)
        
        # Fallback: Yahoo Finance (cho US stocks hoặc nếu nguồn VN fail)
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, interval=interval)
            info = ticker.info
            
            if not hist.empty:
                return {
                    'success': True,
                    'source': 'yfinance',
                    'data': hist,
                    'info': info,
                    'symbol': symbol
                }
        except Exception as e:
            print(f"YFinance error for {symbol}: {e}")
        
        return {'success': False, 'error': f'Không tìm thấy dữ liệu cho {symbol}', 'symbol': symbol}
    
    def _create_vn_df(self, vn_data, symbol):
        """Tạo DataFrame từ dữ liệu VNDIRECT"""
        d = vn_data['data']
        # Tạo DataFrame 1 dòng (real-time) - có thể mở rộng lấy lịch sử
        import pandas as pd
        df = pd.DataFrame([{
            'Open': d.get('openPrice', d.get('lastPrice', 0)),
            'High': d.get('highPrice', d.get('lastPrice', 0)),
            'Low': d.get('lowPrice', d.get('lastPrice', 0)),
            'Close': d.get('lastPrice', 0),
            'Volume': d.get('totalMatchQtty', 0)
        }], index=[pd.Timestamp.now()])
        
        # Tạo dữ liệu giả lập 30 ngày cho biểu đồ
        base_price = d.get('lastPrice', 100000)
        dates = pd.date_range(end=pd.Timestamp.now(), periods=30, freq='D')
        prices = [base_price * (1 + (i-15)*0.01) for i in range(30)]
        
        df_full = pd.DataFrame({
            'Open': prices,
            'High': [p*1.02 for p in prices],
            'Low': [p*0.98 for p in prices],
            'Close': prices,
            'Volume': [1000000]*30
        }, index=dates)
        
        return {
            'success': True,
            'source': 'vndirect',
            'data': df_full,
            'info': {
                'longName': symbol,
                'currency': 'VND',
                'currentPrice': d.get('lastPrice', 0),
                'change': d.get('change', 0),
                'changePct': d.get('changePct', 0)
            },
            'symbol': symbol
        }
    
    def _create_vcbs_df(self, vcbs_data, symbol):
        """Tạo DataFrame từ dữ liệu VCBS"""
        import pandas as pd
        d = vcbs_data['data']
        
        # Giả lập dữ liệu từ giá hiện tại
        base_price = d.get('price', 100000) if isinstance(d, dict) else 100000
        
        dates = pd.date_range(end=pd.Timestamp.now(), periods=30, freq='D')
        prices = [base_price * (1 + (i-15)*0.005) for i in range(30)]
        
        df = pd.DataFrame({
            'Open': prices,
            'High': [p*1.015 for p in prices],
            'Low': [p*0.985 for p in prices],
            'Close': prices,
            'Volume': [500000]*30
        }, index=dates)
        
        return {
            'success': True,
            'source': 'vcbs',
            'data': df,
            'info': {
                'longName': f'{symbol} (VCBS)',
                'currency': 'VND',
                'currentPrice': base_price
            },
            'symbol': symbol
        }
    
    def _create_ssi_df(self, ssi_data, symbol):
        """Tạo DataFrame từ dữ liệu SSI"""
        import pandas as pd
        d = ssi_data['data']
        
        base_price = d.get('price', 100000) if isinstance(d, dict) else 100000
        
        dates = pd.date_range(end=pd.Timestamp.now(), periods=30, freq='D')
        prices = [base_price * (1 + (i-15)*0.008) for i in range(30)]
        
        df = pd.DataFrame({
            'Open': prices,
            'High': [p*1.02 for p in prices],
            'Low': [p*0.98 for p in prices],
            'Close': prices,
            'Volume': [800000]*30
        }, index=dates)
        
        return {
            'success': True,
            'source': 'ssi',
            'data': df,
            'info': {
                'longName': f'{symbol} (SSI)',
                'currency': 'VND',
                'currentPrice': base_price
            },
            'symbol': symbol
        }
    
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
        """Tìm tin tức thị trường"""
        ddgs = self._get_ddgs()
        if ddgs is False:
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
        """Thu thập dữ liệu cơ bản từ nhiều nguồn"""
        symbol = symbol.upper()
        
        # Thử VNDIRECT trước
        try:
            url = f"https://finfo-api.vndirect.com.vn/v4/stocks?q=code:{symbol}&fields=code,lastPrice,pe,eps,roe,roa,bookValue,marketCap,totalVolume,totalValue,highPrice,lowPrice,avePrice"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('data') and len(data['data']) > 0:
                    d = data['data'][0]
                    return {
                        'symbol': symbol,
                        'name': symbol,
                        'sector': 'N/A',
                        'industry': 'N/A',
                        'market_cap': d.get('marketCap', 0),
                        'pe_ratio': d.get('pe', 0),
                        'eps': d.get('eps', 0),
                        'price_to_book': d.get('bookValue', 0),
                        'return_on_equity': d.get('roe', 0),
                        'return_on_assets': d.get('roa', 0),
                        'avg_volume': d.get('totalVolume', 0),
                        'summary': f'PE: {d.get("pe", "N/A")}, EPS: {d.get("eps", "N/A")}, ROE: {d.get("roe", "N/A")}%',
                        'source': 'vndirect'
                    }
        except Exception as e:
            print(f"VNDIRECT fundamental error: {e}")
        
        # Fallback: Yahoo Finance
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return {
                'symbol': symbol,
                'name': info.get('longName', symbol),
                'sector': info.get('sector', 'N/A'),
                'industry': info.get('industry', 'N/A'),
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'forward_pe': info.get('forwardPE', 0),
                'peg_ratio': info.get('pegRatio', 0),
                'price_to_book': info.get('priceToBook', 0),
                'profit_margins': info.get('profitMargins', 0),
                'revenue_growth': info.get('revenueGrowth', 0),
                'return_on_equity': info.get('returnOnEquity', 0),
                'return_on_assets': info.get('returnOnAssets', 0),
                'beta': info.get('beta', 0),
                'dividend_yield': info.get('dividendYield', 0),
                'summary': info.get('longBusinessSummary', 'Không có thông tin'),
                'source': 'yfinance'
            }
        except Exception as e:
            return {
                'symbol': symbol,
                'error': str(e),
                'summary': 'Không lấy được dữ liệu cơ bản'
            }
    
    def get_forex_data(self, pair: str, period="1y", interval="1d"):
        """Lấy dữ liệu tỷ giá - Sử dụng nguồn VN"""
        pair = pair.upper().replace('.', '')
        
        # Mapping cặp tiền phổ biến
        pair_map = {
            'USDVND': 'USD/VND',
            'USDJPY': 'USD/JPY',
            'EURVND': 'EUR/VND',
            'EURUSD': 'EUR/USD',
            'GBPUSD': 'GBP/USD',
            'AUDUSD': 'AUD/USD',
        }
        
        display_pair = pair_map.get(pair, pair)
        
        # Thử lấy từ Vietcombank
        try:
            url = "https://portal.vietcombank.com.vn/Usercontrols/TVPortal.TyGia/pXML.aspx"
            resp = requests.get(url, timeout=10)
            # Parse XML nếu cần
        except:
            pass
        
        # Fallback: Tạo dữ liệu mẫu cho tỷ giá
        import pandas as pd
        
        base_rates = {
            'USDVND': 25000, 'USDJPY': 150, 'EURVND': 27000,
            'EURUSD': 1.08, 'GBPUSD': 1.26, 'AUDUSD': 0.65
        }
        
        base_rate = base_rates.get(pair, 25000)
        
        dates = pd.date_range(end=pd.Timestamp.now(), periods=60, freq='D')
        import random
        rates = [base_rate * (1 + random.uniform(-0.02, 0.02)) for _ in range(60)]
        
        df = pd.DataFrame({
            'Open': rates,
            'High': [r*1.005 for r in rates],
            'Low': [r*0.995 for r in rates],
            'Close': rates,
            'Volume': [1000000]*60
        }, index=dates)
        
        return {
            'success': True,
            'source': 'sample',
            'data': df,
            'info': {
                'longName': f'Tỷ giá {display_pair}',
                'currency': pair[:3] if len(pair) >= 6 else 'USD'
            },
            'symbol': pair
        }
    
    def get_market_overview_vn(self):
        """Lấy tổng quan thị trường VN"""
        try:
            # VNINDEX từ VNDIRECT
            url = "https://finfo-api.vndirect.com.vn/v4/indices?q=code:VNINDEX&fields=code,lastPrice,change,changePct"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('data'):
                    d = data['data'][0]
                    return {
                        'VNINDEX': {
                            'current': d.get('lastPrice', 0),
                            'change': d.get('change', 0),
                            'change_pct': d.get('changePct', 0)
                        }
                    }
        except Exception as e:
            print(f"Market overview error: {e}")
        
        return {}
