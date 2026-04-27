import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import os
from datetime import datetime
import json

class StockTelegramBot:
    """Bot Telegram tích hợp phân tích chứng khoán"""
    
    def __init__(self, token, analyzer_callback):
        self.token = token
        self.analyze = analyzer_callback  # Callback đến hàm analyze_stock
        self.user_watchlists = {}  # {chat_id: [symbols]}
        self.price_alerts = {}     # {chat_id: {symbol: {target, condition}}}
        self.app = Application.builder().token(token).build()
        self._setup_handlers()
    
    def _setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("analyze", self.cmd_analyze))
        self.app.add_handler(CommandHandler("watchlist", self.cmd_watchlist))
        self.app.add_handler(CommandHandler("alert", self.cmd_alert))
        self.app.add_handler(CommandHandler("forex", self.cmd_forex))
        self.app.add_handler(CommandHandler("market", self.cmd_market))
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        welcome = """
🚀 *AI Stock Analyzer Bot*

Chào mừng! Tôi là trợ lý phân tích chứng khoán AI đa tầng.

*Các lệnh chính:*
📊 `/analyze [MÃ]` - Phân tích chứng khoán/quỹ
💱 `/forex [CẶP]` - Phân tích tỷ giá (VD: USD.VND)
📋 `/watchlist` - Danh sách theo dõi
🔔 `/alert [MÃ] [GIÁ]` - Cảnh báo giá
📈 `/market` - Tổng quan thị trường

*Ví dụ:*
`/analyze VCB`
`/forex USD.VND`
`/alert VCB 85000`
        """
        await update.message.reply_text(welcome, parse_mode='Markdown')
    
    async def cmd_analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Vui lòng nhập mã chứng khoán\nVD: `/analyze VCB`", parse_mode='Markdown')
            return
        
        symbol = context.args[0].upper()
        chat_id = update.effective_chat.id
        
        # Gửi tin nhắn đang xử lý
        processing_msg = await update.message.reply_text(f"⏳ Đang phân tích {symbol}...")
        
        try:
            # Gọi hàm phân tích (từ app.py)
            result = await self.analyze(symbol)
            
            # Format kết quả
            rec = result.get('recommendation', {})
            action = rec.get('recommendation', 'THEO DÕI')
            
            emojis = {
                'MUA': '🟢', 'STRONG_BUY': '🟢🟢',
                'BÁN': '🔴', 'STRONG_SELL': '🔴🔴',
                'GIỮ': '🟡', 'HOLD': '🟡',
                'THEO DÕI': '🔵'
            }
            
            message = f"""
{emojis.get(action, '⚪')} *{symbol}* - {action}

💰 Giá hiện tại: `{result.get('current_price', 'N/A'):,} {result.get('currency', 'VND')}`

📊 *Phân tích kỹ thuật:*
• Xu hướng: {result.get('technical', {}).get('signals', {}).get('trend', 'N/A')}
• RSI: {result.get('technical', {}).get('indicators', {}).get('rsi', 'N/A')}
• Điểm tổng hợp: {result.get('technical', {}).get('signals', {}).get('score', 'N/A')}/100

🧠 *Khuyến nghị AI (DeepSeek):*
• Giá mục tiêu: `{rec.get('target_price', 'N/A'):,}`
• Cắt lỗ: `{rec.get('stop_loss', 'N/A'):,}`
• Tiềm năng: {rec.get('upside_potential', 'N/A')}
• Khung thời gian: {rec.get('time_horizon', 'N/A')}

📝 *Luận điểm:*
{rec.get('investment_thesis', 'N/A')[:300]}...
            """
            
            # Keyboard inline
            keyboard = [
                [InlineKeyboardButton("📈 Xem biểu đồ", callback_data=f"chart_{symbol}")],
                [InlineKeyboardButton("➕ Thêm vào Watchlist", callback_data=f"addwl_{symbol}")],
                [InlineKeyboardButton("🔔 Đặt cảnh báo", callback_data=f"alert_{symbol}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await processing_msg.delete()
            await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            await processing_msg.edit_text(f"❌ Lỗi phân tích {symbol}: {str(e)}")
    
    async def cmd_forex(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Vui lòng nhập cặp tiền tệ\nVD: `/forex USD.VND`", parse_mode='Markdown')
            return
        
        pair = context.args[0].upper()
        await update.message.reply_text(f"⏳ Phân tích tỷ giá {pair}...")
        # Tương tự như analyze, gọi API forex
    
    async def cmd_watchlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        watchlist = self.user_watchlists.get(chat_id, [])
        
        if not watchlist:
            await update.message.reply_text("📋 Watchlist trống. Thêm bằng lệnh:\n`/analyze MACK` rồi bấm 'Thêm vào Watchlist'", parse_mode='Markdown')
            return
        
        message = "📋 *Danh sách theo dõi:*\n\n"
        for symbol in watchlist:
            message += f"• `{symbol}`\n"
        
        keyboard = [[InlineKeyboardButton("🔄 Cập nhật tất cả", callback_data="update_all")]]
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def cmd_alert(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text("❌ Cú pháp: `/alert [MÃ] [GIÁ_MỤC_TIÊU]`\nVD: `/alert VCB 85000`", parse_mode='Markdown')
            return
        
        symbol = context.args[0].upper()
        target_price = float(context.args[1])
        chat_id = update.effective_chat.id
        
        if chat_id not in self.price_alerts:
            self.price_alerts[chat_id] = {}
        
        self.price_alerts[chat_id][symbol] = {
            'target': target_price,
            'condition': 'above' if target_price > 0 else 'below',
            'created_at': datetime.now().isoformat()
        }
        
        await update.message.reply_text(f"🔔 Đã đặt cảnh báo:\n*{symbol}* đạt giá `{target_price:,.0f}`\nTôi sẽ thông báo khi điều kiện thỏa mãn!", parse_mode='Markdown')
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        data = query.data
        chat_id = update.effective_chat.id
        
        if data.startswith("addwl_"):
            symbol = data.split("_")[1]
            if chat_id not in self.user_watchlists:
                self.user_watchlists[chat_id] = []
            if symbol not in self.user_watchlists[chat_id]:
                self.user_watchlists[chat_id].append(symbol)
                await query.edit_message_text(f"✅ Đã thêm *{symbol}* vào watchlist!", parse_mode='Markdown')
        
        elif data.startswith("chart_"):
            symbol = data.split("_")[1]
            await query.message.reply_text(f"📊 [Xem biểu đồ {symbol}](https://your-render-url.com/charts/{symbol})", parse_mode='Markdown')
        
        elif data == "update_all":
            await query.message.reply_text("🔄 Đang cập nhật toàn bộ watchlist...")
            # Trigger batch analysis
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý tin nhắn text thuần (mã chứng khoán)"""
        text = update.message.text.strip().upper()
        
        # Nếu là mã chứng khoán (1-5 ký tự, chữ cái)
        if text.isalpha() and 1 <= len(text) <= 5:
            # Giả lập command /analyze
            context.args = [text]
            await self.cmd_analyze(update, context)
        else:
            await update.message.reply_text("❓ Không hiểu lệnh. Gõ /help để xem hướng dẫn.")
    
    async def send_price_alert(self, chat_id, symbol, current_price, target_price):
        """Gửi cảnh báo giá"""
        message = f"""
🚨 *CẢNH BÁO GIÁ*

*{symbol}* đã đạt mức giá: `{current_price:,.0f}`
🎯 Mục tiêu của bạn: `{target_price:,.0f}`

Gõ `/analyze {symbol}` để xem phân tích cập nhật.
        """
        await self.app.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
    
    def run(self):
        """Chạy bot"""
        print("🤖 Telegram Bot đang chạy...")
        self.app.run_polling()
    
    async def run_async(self):
        """Chạy async cho integration với Flask"""
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()