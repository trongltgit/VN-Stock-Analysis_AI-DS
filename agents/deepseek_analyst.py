from groq import Groq
from config import Config
import json

class DeepSeekAnalyst:
    """Tầng định giá & khuyến nghị: Suy luận logic, tính toán"""
    
    def __init__(self):
        self.client = Groq(api_key=Config.GROQ_API_KEY)
        self.model = Config.GROQ_MODEL
    
    def generate_investment_recommendation(self, 
                                       symbol: str,
                                       fundamental_analysis: dict,
                                       technical_signals: dict,
                                       market_news: list,
                                       current_price: float):
        """Tổng hợp để đưa ra khuyến nghị cuối cùng"""
        
        news_summary = "\n".join([
            f"- {n.get('title', 'N/A')}: {n.get('body', 'N/A')[:200]}" 
            for n in market_news[:5]
        ])
        
        prompt = f"""Bạn là Giám đốc Phân tích Đầu tư (CFA, FRM) với 20 năm kinh nghiệm. 
        Hãy phân tích tổng hợp và đưa ra khuyến nghị chuyên nghiệp.
        
        MÃ CHỨNG KHOÁN: {symbol}
        GIÁ HIỆN TẠI: {current_price:,.0f} VND
        
        === PHÂN TÍCH CƠ BẢN ===
        {json.dumps(fundamental_analysis, indent=2, ensure_ascii=False)}
        
        === TÍN HIỆU KỸ THUẬT ===
        {json.dumps(technical_signals, indent=2, ensure_ascii=False)}
        
        === TIN TỨC THỊ TRƯỜNG ===
        {news_summary}
        
        YÊU CẦU:
        1. Tổng hợp phân tích đa chiều (cơ bản + kỹ thuật + vĩ mô)
        2. Định giá hợp lý (Fair Value) với phương pháp DCF/Comparables
        3. Khuyến nghị cuối cùng: MUA / BÁN / GIỮ / THEO DÕI
        4. Mức giá mục tiêu: Target price và Stop loss
        5. Rủi ro chính và kịch bản thay thế
        6. Khung thời gian đầu tư phù hợp
        
        Trả về JSON:
        {{
            "recommendation": "MUA/BÁN/GIỮ/THEO DÕI",
            "confidence": "CAO/TRUNG BÌNH/THẤP",
            "target_price": 0,
            "stop_loss": 0,
            "fair_value": 0,
            "upside_potential": "0%",
            "investment_thesis": "...",
            "risk_factors": ["..."],
            "time_horizon": "Ngắn hạn/Trung hạn/Dài hạn",
            "allocation_suggestion": "...",
            "detailed_reasoning": "..."
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Bạn là chuyên gia phân tích đầu tư chuyên nghiệp. Trả lời bằng tiếng Việt, logic chặt chẽ, có số liệu cụ thể."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=4000
            )
            
            text = response.choices[0].message.content
            
            # Parse JSON
            if '```json' in text:
                json_str = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                json_str = text.split('```')[1].split('```')[0]
            else:
                json_str = text
            
            return json.loads(json_str)
            
        except Exception as e:
            return {
                'recommendation': 'THEO DÕI',
                'confidence': 'THẤP',
                'error': str(e),
                'fallback_reasoning': 'Hệ thống gặp lỗi kết nối. Vui lòng thử lại sau.'
            }
    
    def analyze_forex(self, pair: str, 
                     technical_data: dict,
                     macro_news: list):
        """Phân tích tỷ giá tiền tệ"""
        prompt = f"""Phân tích cặp tiền tệ {pair}:
        
        Dữ liệu kỹ thuật: {json.dumps(technical_data, ensure_ascii=False)}
        Tin vĩ mô: {json.dumps(macro_news[:3], ensure_ascii=False)}
        
        Yêu cầu:
        1. Xu hướng tỷ giá ngắn hạn và trung hạn
        2. Các yếu tố vĩ mô ảnh hưởng (lãi suất, lạm phát, chính sách tiền tệ)
        3. Mức hỗ trợ/kháng cự quan trọng
        4. Khuyến nghị: TĂNG/GIẢM/ĐI NGANG
        5. Rủi ro biến động
        
        JSON format.
        """
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=3000
        )
        
        return response.choices[0].message.content