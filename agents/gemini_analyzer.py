import google.generativeai as genai
from config import Config
import json

class GeminiAnalyzer:
    """Tầng phân tích cơ bản: Đọc hiểu BCTC, phân tích sức khỏe tài chính"""
    
    def __init__(self):
        self._model = None
    
    @property
    def model(self):
        if self._model is None:
            genai.configure(api_key=Config.GEMINI_API_KEY)
            self._model = genai.GenerativeModel(Config.GEMINI_MODEL)
        return self._model
    
    def analyze_fundamentals(self, fundamental_data: dict):
        """Phân tích chỉ số cơ bản và tạo báo cáo"""
        prompt = f"""
        Bạn là chuyên gia phân tích tài chính cấp cao. Hãy phân tích sâu dữ liệu cơ bản sau 
        và tạo báo cáo chuyên nghiệp bằng tiếng Việt:
        
        DỮ LIỆU CÔNG TY:
        {json.dumps(fundamental_data, indent=2, ensure_ascii=False)}
        
        YÊU CẦU PHÂN TÍCH:
        1. SỨC KHỎE TÀI CHÍNH: Đánh giá cơ cấu tài chính, khả năng thanh toán, nợ vay
        2. HIỆU QUẢ HOẠT ĐỘNG: ROE, ROA, biên lợi nhuận, tăng trưởng doanh thu/lợi nhuận
        3. ĐỊNH GIÁ: P/E, P/B, PEG so với ngành trung bình
        4. RỦI RO: Beta, đòn bẩy tài chính, rủi ro thanh khoản
        5. ĐIỂM MẠNH/YẾU: SWOT ngắn gọn
        
        Định dạng JSON:
        {{
            "financial_health": {{"score": 0-100, "assessment": "...", "details": ["..."]}},
            "operational_efficiency": {{"score": 0-100, "assessment": "...", "details": ["..."]}},
            "valuation": {{"score": 0-100, "assessment": "...", "fair_value": "...", "details": ["..."]}},
            "risk_analysis": {{"score": 0-100, "assessment": "...", "details": ["..."]}},
            "swot": {{"strengths": ["..."], "weaknesses": ["..."], "opportunities": ["..."], "threats": ["..."]}},
            "overall_score": 0-100,
            "investment_grade": "A/B/C/D/F",
            "summary": "..."
        }}
        """
        
        try:
            response = self.model.generate_content(prompt)
            text = response.text
            
            if '```json' in text:
                json_str = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                json_str = text.split('```')[1].split('```')[0]
            else:
                json_str = text
            
            result = json.loads(json_str)
            return result
        except Exception as e:
            return {
                'error': str(e),
                'fallback_analysis': self._fallback_analysis(fundamental_data)
            }
    
    def analyze_pdf_report(self, pdf_content: str):
        """Phân tích báo cáo tài chính PDF đã extract text"""
        prompt = f"""
        Phân tích báo cáo tài chính sau. Tập trung vào:
        1. Tăng trưởng doanh thu, lợi nhuận quý/năm
        2. Biên lợi nhuận gộp và ròng
        3. Dòng tiền hoạt động
        4. Nợ phải trả và vốn chủ sở hữu
        5. Các chỉ số quan trọng: EPS, BVPS, DPS
        
        Báo cáo:
        {pdf_content[:15000]}
        
        Trả về JSON với cấu trúc tương tự analyze_fundamentals.
        """
        
        response = self.model.generate_content(prompt)
        return response.text
    
    def _fallback_analysis(self, data: dict):
        """Phân tích dự phòng khi API lỗi"""
        pe = data.get('pe_ratio', 0)
        pb = data.get('price_to_book', 0)
        roe = data.get('return_on_equity', 0)
        
        grade = 'C'
        if pe < 15 and roe > 0.15:
            grade = 'A'
        elif pe < 20 and roe > 0.10:
            grade = 'B'
        elif pe > 30 or roe < 0:
            grade = 'D'
        
        return {
            'overall_score': 50,
            'investment_grade': grade,
            'summary': f'P/E: {pe}, P/B: {pb}, ROE: {roe}. Phân tích tự động.'
        }
