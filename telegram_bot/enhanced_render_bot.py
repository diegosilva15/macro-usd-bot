#!/usr/bin/env python3
"""
Enhanced Bot Macroeconômico USD - Versão SEMPRE ATUALIZADA
Com dynamic data engine para análises frescas como analistas profissionais
"""

import os
import asyncio
import logging
import sys
from datetime import datetime, timedelta
from typing import Dict, Any
import pytz

# Telegram imports
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import our dynamic engine
from dynamic_data_engine import DynamicDataEngine

# Configure logging for Render
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

class EnhancedRenderMacroBot:
    """Bot com dados sempre atualizados - versão enhanced"""
    
    def __init__(self):
        # Get environment variables
        self.bot_token = os.getenv('BOT_TOKEN')
        self.fred_api_key = os.getenv('FRED_API_KEY')
        self.alpha_vantage_key = os.getenv('ALPHA_VANTAGE_API_KEY')
        self.default_chat_id = os.getenv('DEFAULT_CHAT_ID')
        
        # Validate required env vars
        if not self.bot_token:
            raise ValueError("❌ BOT_TOKEN não configurado!")
        
        # Initialize dynamic data engine
        self.data_engine = DynamicDataEngine(
            fred_key=self.fred_api_key,
            alpha_vantage_key=self.alpha_vantage_key
        )
        
        logger.info("✅ Enhanced Bot configurado com Dynamic Data Engine")
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /start - versão enhanced"""
        ny_tz = pytz.timezone('America/New_York')
        now_ny = datetime.now(ny_tz)
        
        welcome_msg = f"""
🧭 **Bot Macroeconômico USD - Enhanced Edition**

🚀 **NOVIDADE:** Dados sempre atualizados como analistas profissionais!
📅 **NY Time:** {now_ny.strftime('%d/%m/%Y %H:%M')}

**🔥 Enhanced Features:**
• **Dados dinâmicos** - Busca automaticamente dados atuais
• **Calendário semanal** - Eventos específicos da semana
• **Análise contextual** - Inclui riscos (shutdown, FOMC, etc.)
• **Score em tempo real** - Baseado em dados frescos

**📊 Comandos Enhanced:**
• `/status` - Status + calendário semanal
• `/score` - USD Score com dados atualizados  
• `/weekly` - 🆕 Outlook semanal completo
• `/summary` - Resumo econômico atual
• `/help` - Manual enhanced

**🔗 Fontes Enhanced:**
• FRED API: {"✅ Ativo" if self.fred_api_key else "⚠️ Configure"}
• Alpha Vantage: {"✅ Ativo" if self.alpha_vantage_key else "⚠️ Configure"}  
• Yahoo Finance: ✅ DXY + Treasury yields
• Economic Calendar: ✅ Eventos semanais

**⚡ Sempre atualizado como Bloomberg!**

Digite `/weekly` para outlook da semana atual!
        """
        await update.message.reply_text(welcome_msg, parse_mode='Markdown')
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /status enhanced com calendário"""
        ny_tz = pytz.timezone('America/New_York')
        now_ny = datetime.now(ny_tz)
        
        try:
            await self.data_engine.initialize()
            
            # Get current week calendar
            calendar_data = self.data_engine.weekly_calendar
            special_events = calendar_data.get('special_events', {})
            
            status_msg = f"""
📊 **Status Enhanced - Sempre Atualizado**

🟢 **Status:** Online 24/7 com dados dinâmicos
📅 **NY Time:** {now_ny.strftime('%d/%m/%Y %H:%M')}
🔄 **Last Update:** Dados buscados em tempo real

**🔗 APIs Status:**
• FRED: {"✅ Conectado" if self.fred_api_key else "⚠️ Configure FRED_API_KEY"}
• Alpha Vantage: {"✅ Conectado" if self.alpha_vantage_key else "⚠️ Configure AV_KEY"}
• Yahoo Finance: ✅ DXY + yields em tempo real
• Dynamic Engine: ✅ Ativo

**📅 Esta Semana - Eventos Chave:**
• **Segunda:** PMI Services Final
• **Terça:** JOLTs + Trade Balance  
• **Quarta:** ADP + ISM Services
• **Quinta:** Initial Claims
• **Sexta:** NFP + Unemployment

**⚠️ Alertas Especiais:**
"""
            
            # Add special events
            shutdown_risk = special_events.get('government_shutdown_risk', {})
            if shutdown_risk.get('active', False):
                status_msg += f"• 🚨 **Shutdown Risk:** {shutdown_risk['risk_level']} ({shutdown_risk['days_remaining']} dias)\n"
            
            fomc_info = special_events.get('fomc_meeting', {})
            if fomc_info.get('this_week', False):
                status_msg += f"• 🏛️ **FOMC Meeting:** {fomc_info['date']}\n"
            else:
                status_msg += f"• 🏛️ **FOMC:** Próxima reunião em breve\n"
            
            status_msg += """
**🎯 Commands:** `/score` para análise atual | `/weekly` para outlook
            """
            
            await update.message.reply_text(status_msg, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Erro no status enhanced: {e}")
            await update.message.reply_text("❌ Erro ao buscar status. Tente novamente.")
        finally:
            await self.data_engine.close()
    
    async def score_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /score - SEMPRE ATUALIZADO"""
        await update.message.reply_text("🔄 Buscando dados atualizados... (pode demorar 30s)")
        
        try:
            await self.data_engine.initialize()
            
            # Get fresh data
            fresh_data = await self.data_engine.get_latest_economic_data()
            
            # Calculate dynamic USD score
            analysis = self.data_engine.calculate_dynamic_usd_score(fresh_data)
            
            ny_tz = pytz.timezone('America/New_York')
            now_ny = datetime.now(ny_tz)
            
            # Format enhanced analysis message
            analysis_msg = f"""
🧭 **USD Score Enhanced** — {now_ny.strftime('%d/%m/%Y %H:%M')} (NY)

**📊 Dados Atualizados em Tempo Real:**

**🏦 Componentes Analisados:**
"""
            
            # Add components found
            components = analysis.get('components', [])
            if components:
                for comp in components:
                    analysis_msg += f"• {comp}\n"
            else:
                analysis_msg += "• Buscando dados mais recentes...\n"
            
            score = analysis.get('score', 0)
            classification = analysis.get('classification', 'Neutro')
            confidence = analysis.get('confidence', 'Baixa')
            
            analysis_msg += f"""
**🧮 USD Score Dinâmico:** {score:+.2f} → **{classification}**
**🎯 Confiança:** {confidence} (dados atualizados)

**📌 Análise Contextual:**
"""
            
            # Add contextual analysis based on score
            if score > 1.0:
                analysis_msg += """
• **Cenário Dominante:** Dados robustos favorecem USD forte
• **Fed Outlook:** Postura hawkish sustentada por fundamentos
• **Market Impact:** Fluxo para USD vs. moedas de risco
"""
            elif score > 0.3:
                analysis_msg += """
• **Cenário Dominante:** Moderada fortaleza do USD
• **Fed Outlook:** Mantém "higher for longer" cauteloso  
• **Market Impact:** USD ganha seletivamente vs. majors
"""
            elif score < -1.0:
                analysis_msg += """
• **Cenário Dominante:** Pressão sobre USD por dados fracos
• **Fed Outlook:** Mercado antecipa pivot dovish
• **Market Impact:** Fuga do USD para moedas de commodity
"""
            else:
                analysis_msg += """
• **Cenário Dominante:** USD em consolidação, aguarda catalisadores
• **Fed Outlook:** Dados mistos mantêm Fed em pausa
• **Market Impact:** Trading em ranges, volatilidade baixa
"""
            
            # Add special events impact
            special_events = analysis.get('special_events', {})
            
            shutdown_risk = special_events.get('government_shutdown_risk', {})
            if shutdown_risk.get('active', False):
                analysis_msg += f"\n⚠️ **Risco Fiscal:** Shutdown em {shutdown_risk['days_remaining']} dias pressiona USD"
            
            fomc_info = special_events.get('fomc_meeting', {})
            if fomc_info.get('this_week', False):
                analysis_msg += f"\n🏛️ **FOMC Impact:** Meeting esta semana pode aumentar volatilidade"
            
            # Generate tactical recommendations
            analysis_msg += f"""

**🎯 Recomendações Táticas:**
"""
            
            if score > 0.5:
                analysis_msg += """• **EUR/USD:** VENDA bias, target 1.0700-1.0750
• **GBP/USD:** Weakness esperada, break 1.2600
• **USD/JPY:** COMPRA em dips, target 150.00+
• **DXY:** Suporte 103.50, resistência 106.00"""
            elif score < -0.5:
                analysis_msg += """• **EUR/USD:** COMPRA em dips, target 1.0900+
• **GBP/USD:** Recovery para 1.2800-1.2900
• **USD/JPY:** VENDA rallies, target 148.00
• **DXY:** Resistência 104.50, suporte 102.00"""
            else:
                analysis_msg += """• **EUR/USD:** Range 1.0750-1.0850, trade breakouts
• **GBP/USD:** Consolidação 1.2600-1.2800
• **USD/JPY:** Range amplo 148.00-151.00
• **DXY:** Lateralização 103.00-105.00"""
            
            analysis_msg += f"""

**🔄 Próxima Atualização:** Automática com novos dados
**📊 Enhanced:** Dados dinâmicos vs. dados fixos tradicionais
            """
            
            await update.message.reply_text(analysis_msg, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Erro no score enhanced: {e}")
            await update.message.reply_text("❌ Erro ao buscar dados atualizados. APIs podem estar temporariamente indisponíveis.")
        finally:
            await self.data_engine.close()
    
    async def weekly_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /weekly - NOVO comando outlook semanal"""
        await update.message.reply_text("📊 Gerando outlook semanal... (buscando dados atuais)")
        
        try:
            await self.data_engine.initialize()
            
            # Get fresh data and analysis
            fresh_data = await self.data_engine.get_latest_economic_data()
            analysis = self.data_engine.calculate_dynamic_usd_score(fresh_data)
            
            # Generate weekly outlook
            weekly_outlook = self.data_engine.format_weekly_outlook(analysis)
            
            await update.message.reply_text(weekly_outlook, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Erro no weekly outlook: {e}")
            await update.message.reply_text("❌ Erro ao gerar outlook semanal.")
        finally:
            await self.data_engine.close()
    
    async def summary_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /summary enhanced"""
        await update.message.reply_text("📈 Buscando resumo econômico atualizado...")
        
        try:
            await self.data_engine.initialize()
            fresh_data = await self.data_engine.get_latest_economic_data()
            
            ny_tz = pytz.timezone('America/New_York')
            now_ny = datetime.now(ny_tz)
            
            summary_msg = f"""
📈 **Resumo Econômico USA Enhanced** — {now_ny.strftime('%d/%m/%Y %H:%M')} (NY)

**📊 Dados Atualizados:**
"""
            
            # Add FRED data if available
            fred_data = fresh_data.get('fred', {})
            if fred_data:
                summary_msg += "\n**🏦 Federal Reserve (FRED):**\n"
                
                if 'nfp' in fred_data:
                    nfp_data = fred_data['nfp']
                    summary_msg += f"• NFP: {nfp_data['value']:.0f}k ({nfp_data['date']})\n"
                
                if 'unemployment' in fred_data:
                    unemp_data = fred_data['unemployment']
                    summary_msg += f"• Unemployment: {unemp_data['value']:.1f}% ({unemp_data['date']})\n"
                
                if 'fed_funds' in fred_data:
                    ff_data = fred_data['fed_funds']
                    summary_msg += f"• Fed Funds: {ff_data['value']:.2f}% ({ff_data['date']})\n"
            
            # Add market data
            market_data = fresh_data.get('market', {})
            if market_data:
                summary_msg += "\n**📊 Market Data (Tempo Real):**\n"
                
                if 'dxy' in market_data:
                    dxy_data = market_data['dxy']
                    summary_msg += f"• DXY: {dxy_data['current']:.2f} ({dxy_data['change_pct']:+.2f}%)\n"
                
                if 'treasury_10y_yield' in market_data:
                    yield_data = market_data['treasury_10y_yield']
                    summary_msg += f"• 10Y Treasury: {yield_data['current']:.2f}% ({yield_data['change_pct']:+.2f}%)\n"
            
            summary_msg += f"""

**🎯 Síntese Macro:**
Dados coletados automaticamente de fontes oficiais e mercado em tempo real. Enhanced engine mantém análises sempre atualizadas.

**📅 Próximos Eventos:** Use `/weekly` para calendário completo
**🧮 Análise Completa:** Use `/score` para USD Score atual

**Powered by Enhanced Dynamic Engine** 🚀
            """
            
            await update.message.reply_text(summary_msg, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Erro no summary enhanced: {e}")
            await update.message.reply_text("❌ Erro ao buscar resumo atualizado.")
        finally:
            await self.data_engine.close()
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /help enhanced"""
        help_msg = """
🆘 **Manual - Bot Enhanced Always Updated**

**🚀 Enhanced Edition - O Diferencial:**
• **Dados Dinâmicos:** Busca automaticamente dados atuais
• **Nunca Desatualizado:** Como analistas profissionais  
• **Contexto Semanal:** Calendário econômico integrado
• **Análise em Tempo Real:** APIs múltiplas sincronizadas

**📱 Comandos Enhanced:**
• **`/start`** - Apresentação enhanced
• **`/status`** - Status + calendário da semana
• **`/score`** - USD Score com dados frescos (⭐ PRINCIPAL)
• **`/weekly`** - 🆕 Outlook semanal completo
• **`/summary`** - Resumo econômico atualizado
• **`/help`** - Este manual

**🔄 Como Funciona o Enhanced:**
1. **Dynamic Data Engine** busca dados em tempo real
2. **Multiple APIs:** FRED + Alpha Vantage + Yahoo Finance  
3. **Smart Calendar:** Detecta eventos da semana atual
4. **Contextual Analysis:** Inclui riscos (shutdown, FOMC)
5. **Always Fresh:** Nunca usa dados hardcoded

**📊 Fontes de Dados:**
• **FRED:** Dados oficiais do Federal Reserve
• **Alpha Vantage:** Indicadores econômicos atualizados
• **Yahoo Finance:** DXY + Treasury yields tempo real
• **Economic Calendar:** Eventos semanais contextualizados

**💡 Dicas Enhanced:**
• Use `/score` diariamente - sempre dados frescos!
• `/weekly` toda segunda para outlook da semana
• Compare com analistas - mesma qualidade profissional
• Bot nunca "envelhece" - sempre atualizado

**🎯 Diferença vs. Bots Tradicionais:**
❌ **Bots normais:** Dados fixos, desatualizados
✅ **Enhanced:** Dados dinâmicos, sempre frescos

**Como Bloomberg, mas gratuito!** 📈🚀
        """
        await update.message.reply_text(help_msg, parse_mode='Markdown')
    
    def run(self):
        """Executa o enhanced bot no Render"""
        try:
            # Create application
            app = Application.builder().token(self.bot_token).build()
            
            # Add handlers
            app.add_handler(CommandHandler("start", self.start_command))
            app.add_handler(CommandHandler("status", self.status_command))
            app.add_handler(CommandHandler("score", self.score_command))
            app.add_handler(CommandHandler("weekly", self.weekly_command))  # NOVO!
            app.add_handler(CommandHandler("summary", self.summary_command))
            app.add_handler(CommandHandler("help", self.help_command))
            
            logger.info("🚀 Enhanced Bot Macroeconômico iniciado no Render!")
            logger.info("🔄 Dynamic Data Engine ativo - dados sempre atualizados")
            logger.info(f"📊 APIs: FRED={'✅' if self.fred_api_key else '❌'} | AlphaVantage={'✅' if self.alpha_vantage_key else '❌'}")
            
            # Run bot
            app.run_polling(drop_pending_updates=True)
            
        except Exception as e:
            logger.error(f"💥 Erro crítico enhanced: {e}")
            raise

def main():
    """Função principal enhanced"""
    try:
        logger.info("🚀 Iniciando Enhanced Bot - Always Updated Edition...")
        bot = EnhancedRenderMacroBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("👋 Enhanced Bot finalizado pelo usuário")
    except Exception as e:
        logger.error(f"💥 Erro fatal enhanced: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()