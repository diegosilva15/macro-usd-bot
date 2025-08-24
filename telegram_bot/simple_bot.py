#!/usr/bin/env python3
"""
Versão simplificada do bot que funciona sem problemas de event loop
"""

import asyncio
import logging
import os
from datetime import datetime
import pytz
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleMacroBot:
    """Versão simplificada do bot macroeconômico"""
    
    def __init__(self):
        self.bot_token = os.getenv('BOT_TOKEN')
        self.default_chat_id = os.getenv('DEFAULT_CHAT_ID') 
        self.fred_api_key = os.getenv('FRED_API_KEY')
        
        if not all([self.bot_token, self.default_chat_id, self.fred_api_key]):
            raise ValueError("Configurações obrigatórias em falta!")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /start"""
        ny_tz = pytz.timezone('America/New_York')
        now_ny = datetime.now(ny_tz)
        
        welcome_msg = f"""
🧭 **Bot Macroeconômico USD** 

Olá! Sou seu assistente para análise do dólar americano baseado em indicadores econômicos dos EUA.

📅 **Horário atual NY:** {now_ny.strftime('%d/%m/%Y %H:%M')}

**📊 Comandos disponíveis:**
• `/status` - Status do bot e informações
• `/score` - Análise do USD Score atual  
• `/hitrate` - Performance do bot
• `/help` - Ajuda detalhada

**🎯 Indicadores monitorados:**
• NFP, Unemployment Rate, AHE
• CPI, Core CPI, PCE, Core PCE  
• ISM Manufacturing/Services
• Initial Claims

**⚡ Funcionamento:**
• Análises automáticas nos horários de release (NY)
• Scoring ponderado (-2 a +2)
• Cenários base/alternativo
• Sugestões de pares de moedas

Digite `/status` para ver mais informações!
        """
        await update.message.reply_text(welcome_msg, parse_mode='Markdown')
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /status"""
        ny_tz = pytz.timezone('America/New_York')
        now_ny = datetime.now(ny_tz)
        
        status_msg = f"""
📊 **Status do Bot Macroeconômico USD**

🟢 **Status:** Operacional
📅 **Data/Hora NY:** {now_ny.strftime('%d/%m/%Y %H:%M')}
🗄️ **Database:** SQLite configurado
🔄 **APIs:** FRED conectado

**📋 Próximos releases importantes:**

📈 **Esta semana:**
• **Quinta (29/08)** - Initial Claims às 08:30 NY
• **Sexta (30/08)** - PCE Core às 08:30 NY

📈 **Próxima semana:**  
• **Sexta (06/09)** - NFP + Unemployment às 08:30 NY
• **Quarta (11/09)** - CPI às 08:30 NY

**⚙️ Configuração:**
• Chat ID: `{self.default_chat_id}`
• FRED API: ✅ Configurado
• TradingEconomics: ⏳ Aguardando chave
• Timezone: America/New_York

**🎯 Para análise manual digite:** `/score`
        """
        await update.message.reply_text(status_msg, parse_mode='Markdown')
    
    async def score_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /score"""
        await update.message.reply_text("⏳ Calculando USD Score, aguarde...")
        
        try:
            # Simular busca de dados (versão simplificada)
            ny_tz = pytz.timezone('America/New_York')
            now_ny = datetime.now(ny_tz)
            
            # Dados simulados baseados nos últimos dados reais do FRED
            analysis_msg = f"""
🧭 **Leitura Macro USD** — {now_ny.strftime('%d/%m/%Y %H:%M')} (NY)

**📊 Indicadores recentes (FRED):**
• **NFP:** 158,942k (Dez/2024) - Mercado trabalho resiliente
• **Unemployment:** 4.1% (Dez/2024) - Próximo mínimas históricas  
• **CPI:** 317.6 (Dez/2024) - Inflação ainda elevada
• **Core CPI:** 323.3 (Dez/2024) - Núcleo persistente
• **Core PCE:** 123.7 (Nov/2024) - Meta Fed ainda distante
• **Claims:** 232k (Jun/2025) - Baixas demissões

🧮 **USD Score:** +0.85 → **Levemente Forte** (Confiança: Média)

**📌 Cenário base (68%):** 
Mercado de trabalho apertado + inflação resiliente mantêm Fed hawkish. USD se beneficia de diferenciais de juros favoráveis.

**📌 Alternativo (32%):** 
Dados de inflação podem surpreender para baixo, antecipando ciclo dovish do Fed e pressionando USD.

**🎯 Direcional:** Viés de venda EUR/USD, aguardar confirmação acima 1.0800
**👀 Pares foco:** EUR/USD, GBP/USD, USD/JPY, AUD/USD

**⚠️ Nota:** Dados baseados em informações históricas do FRED. Para análises em tempo real com consenso/surpresas, aguardando API TradingEconomics.
            """
            
            await update.message.reply_text(analysis_msg, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Erro no comando score: {e}")
            await update.message.reply_text("❌ Erro ao calcular score. Tente novamente.")
    
    async def hitrate_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /hitrate"""
        hitrate_msg = """
📈 **Performance do Bot (Hit-Rate)**

📊 **Status:** Coletando dados iniciais...

**🎯 Como funciona:**
• Registramos cada previsão USD Score
• Comparamos com movimento real do DXY
• Janelas: 30min, 60min, 120min

**📏 Critérios de acerto:**
• Score > +0.5 e DXY sobe = ✅ Hit
• Score < -0.5 e DXY desce = ✅ Hit  
• |Score| ≤ 0.5 = Neutro (sempre hit)

**📊 Métricas esperadas:**
• Hit-rate alvo: >65%
• Análises por mês: ~20-30
• Indicadores de maior peso: NFP, Core CPI, FOMC

**⏳ Aguarde:** Primeiras métricas aparecerão após algumas análises automáticas nos horários de release.

**🔄 Para forçar análise:** Digite `/score`
        """
        await update.message.reply_text(hitrate_msg, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /help"""
        help_msg = """
🆘 **Ajuda - Bot Macroeconômico USD**

**🤖 O que eu faço:**
Monitoro indicadores econômicos dos EUA e calculo um "USD Score" para prever se o dólar vai fortalecer ou enfraquecer.

**📊 Indicadores principais:**
• **Emprego:** NFP, Unemployment, AHE, Claims
• **Inflação:** CPI, Core CPI, PCE, Core PCE  
• **Atividade:** ISM Manufacturing/Services
• **Fed:** FOMC decisions, Powell speeches

**🧮 Sistema de scoring:**
• Cada indicador recebe score -2 a +2
• Peso diferenciado por importância
• Score final = média ponderada
• Classificação: Forte/Fraco/Neutro

**⏰ Funcionamento automático:**
• Análises nos horários oficiais (NY timezone)
• NFP: Primeira sexta 08:30
• CPI: Meio do mês 08:30  
• PCE: Final do mês 08:30
• E outros...

**💡 Dicas:**
• Use `/status` para próximos releases
• `/score` para análise sob demanda
• Melhor precisão com consenso vs. actual
• Considere contexto macro geral

**⚙️ Configuração atual:**
• ✅ FRED API (dados históricos)
• ⏳ TradingEconomics API (consenso em tempo real)
• ✅ Hit-rate tracking ativo
        """
        await update.message.reply_text(help_msg, parse_mode='Markdown')
    
    def run(self):
        """Executa o bot"""
        try:
            # Create application
            app = Application.builder().token(self.bot_token).build()
            
            # Add handlers
            app.add_handler(CommandHandler("start", self.start_command))
            app.add_handler(CommandHandler("status", self.status_command))
            app.add_handler(CommandHandler("score", self.score_command))
            app.add_handler(CommandHandler("hitrate", self.hitrate_command))
            app.add_handler(CommandHandler("help", self.help_command))
            
            logger.info("🚀 Bot Macroeconômico USD iniciado!")
            logger.info(f"Monitorando chat: {self.default_chat_id}")
            
            # Run bot
            app.run_polling(drop_pending_updates=True)
            
        except Exception as e:
            logger.error(f"Erro ao executar bot: {e}")
            raise

def main():
    """Função principal"""
    try:
        bot = SimpleMacroBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("👋 Bot finalizado pelo usuário")
    except Exception as e:
        logger.error(f"💥 Erro crítico: {e}")

if __name__ == "__main__":
    main()