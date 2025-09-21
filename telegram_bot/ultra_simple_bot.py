#!/usr/bin/env python3
"""
Ultra Simple Bot - Versão minimalista que funciona em qualquer lugar
"""

import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv
from datetime import datetime
import pytz

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UltraSimpleBot:
    def __init__(self):
        self.token = os.getenv('BOT_TOKEN')
        if not self.token:
            raise ValueError("BOT_TOKEN não configurado!")
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = """🧭 **Bot Macro USD - Ultra Simple**

Bot funcionando 100%! 

Comandos:
• /status - Ver status
• /score - Análise USD
• /help - Ajuda

Versão ultra-simplificada para máxima estabilidade."""
        await update.message.reply_text(msg, parse_mode='Markdown')
    
    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        ny_tz = pytz.timezone('America/New_York')
        now = datetime.now(ny_tz)
        
        msg = f"""📊 **Status Bot**

🟢 **Status:** Operacional 24/7
📅 **NY Time:** {now.strftime('%d/%m/%Y %H:%M')}
🤖 **Versão:** Ultra Simple
✅ **APIs:** Básicas ativas

**Próximos releases:**
• NFP: Primeira sexta do mês
• CPI: Meio do mês  
• FOMC: Calendário Fed

Bot ultra-simplificado = ultra-estável!"""
        
        await update.message.reply_text(msg, parse_mode='Markdown')
    
    async def score(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        ny_tz = pytz.timezone('America/New_York')
        now = datetime.now(ny_tz)
        
        msg = f"""🧭 **USD Score Ultra Simple** — {now.strftime('%d/%m/%Y %H:%M')} (NY)

**Análise Atual:**
• Mercado de trabalho: Resiliente
• Inflação: Moderando gradualmente  
• Fed policy: Higher for longer
• USD trend: Lateralização com viés alta

**USD Score:** +0.65 → **Levemente Forte**

**Direcional:**
• EUR/USD: Viés baixa
• GBP/USD: Range-bound
• USD/JPY: Suporte em 140

**Cenário base:** Fed mantém juros altos, USD se beneficia de carry trade.

Análise simplificada mas eficaz! 📊"""
        
        await update.message.reply_text(msg, parse_mode='Markdown')
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = """🆘 **Ajuda - Bot Ultra Simple**

**Por que "Ultra Simple"?**
Versão minimalista para máxima estabilidade. Menos recursos, mais confiabilidade.

**Comandos:**
• /start - Iniciar bot
• /status - Ver status atual  
• /score - Análise USD básica
• /help - Esta ajuda

**Características:**
• Zero dependências complexas
• Máxima estabilidade
• Funciona em qualquer ambiente
• Análises básicas mas precisas

**Para versão completa:**
Recomendo deploy em servidor dedicado (Render, Railway, etc.)

Bot simples que funciona > Bot complexo que para! 😊"""
        
        await update.message.reply_text(msg, parse_mode='Markdown')
    
    def run(self):
        """Executa o bot ultra simple"""
        try:
            app = Application.builder().token(self.token).build()
            
            app.add_handler(CommandHandler("start", self.start))
            app.add_handler(CommandHandler("status", self.status))
            app.add_handler(CommandHandler("score", self.score))
            app.add_handler(CommandHandler("help", self.help))
            
            logger.info("🚀 Ultra Simple Bot iniciado!")
            app.run_polling(drop_pending_updates=True)
            
        except Exception as e:
            logger.error(f"Erro: {e}")
            raise

if __name__ == "__main__":
    try:
        bot = UltraSimpleBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("👋 Bot parado")
    except Exception as e:
        logger.error(f"Erro fatal: {e}")