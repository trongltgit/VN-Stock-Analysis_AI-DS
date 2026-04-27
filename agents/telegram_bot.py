from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import os
from datetime import datetime
import json

class StockTelegramBot:
    """Bot Telegram tích hợp phân tích chứng khoán"""
    
    def __init__(self, token, analyzer_callback):
        self.token = token
        self.analyze = analyzer_callback
        self.user_watchlists = {}
        self.price_alerts = {}
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
💱 `/forex [CẶP]` - Phân tích tỷ giá
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
        processing_msg = await update.message.reply_text(f"⏳ Đang phân tích {symbol}...")
        
        try:
            result = self.analyze(symbol)
            
            if result.get('error'):
                await processing_msg.edit_text(f"❌ Lỗi: {result['error']}")
                return
            
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

🧠 *Khuyến nghị AI:*
• Giá mục tiêu: `{rec.get('target_price', 'N/A'):,}`
• Cắt lỗ: `{rec.get('stop_loss', 'N/A'):,}`
• Tiềm năng: {rec.get('upside_potential', 'N/A')}

📝 *Luận điểm:*
{rec.get('investment_thesis', 'N/A')[:300]}...
            """
            
            keyboard = [
                [InlineKeyboardButton("➕ Thêm vào Watchlist", callback_data=f"addwl_{symbol}")],
            ]
            
            await processing_msg.delete()
            await update.message.reply_text(message, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
            
        except Exception as e:
            await processing_msg.edit_text(f"❌ Lỗi phân tích {symbol}: {str(e)}")
    
    async def cmd_watchlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        watchlist = self.user_watchlists.get(chat_id, [])
        
        if not watchlist:
            await update.message.reply_text("📋 Watchlist trống.")
            return
        
        message = "📋 *Danh sách theo dõi:*\n\n"
        for symbol in watchlist:
            message += f"• `{symbol}`\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def cmd_alert(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text("❌ Cú pháp: `/alert [MÃ] [GIÁ]`", parse_mode='Markdown')
            return
        
        symbol = context.args[0].upper()
        target_price = float(context.args[1])
        chat_id = update.effective_chat.id
        
        if chat_id not in self.price_alerts:
            self.price_alerts[chat_id] = {}
        
        self.price_alerts[chat_id][symbol] = {
            'target': target_price,
            'created_at': datetime.now().isoformat()
        }
        
        await update.message.reply_text(f"🔔 Đã đặt cảnh báo {symbol} tại `{target_price:,.0f}`", parse_mode='Markdown')
    
    async def cmd_forex(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ VD: `/forex USD.VND`", parse_mode='Markdown')
            return
        await update.message.reply_text("⏳ Đang phát triển...")
    
    async def cmd_market(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("📈 Đang lấy dữ liệu thị trường...")
    
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
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.strip().upper()
        if text.isalpha() and 1 <= len(text) <= 5:
            context.args = [text]
            await self.cmd_analyze(update, context)
        else:
            await update.message.reply_text("❓ Gõ /help để xem hướng dẫn.")
    
    def run(self):
        print("🤖 Telegram Bot đang chạy...")
        self.app.run_polling(drop_pending_updates=True)
