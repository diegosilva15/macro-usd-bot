#!/usr/bin/env python3
"""
Bot Macroeconômico USD - Análise de Indicadores Econômicos
Monitora indicadores dos EUA para prever direcional do dólar
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, Any

from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from config import Config
from data_ingestor import DataIngestor
from scoring_engine import ScoringEngine
from hit_rate_tracker import HitRateTracker
from scheduler import EconomicScheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('macro_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class MacroEconomicBot:
    """Bot principal para análise macroeconômica do USD"""
    
    def __init__(self):
        self.config = Config()
        self.data_ingestor = DataIngestor(self.config)
        self.scoring_engine = ScoringEngine()
        self.hit_rate_tracker = HitRateTracker()
        self.scheduler = EconomicScheduler()
        self.app = None
        
    async def initialize(self):
        """Inicializa o bot e componentes"""
        try:
            # Initialize Telegram bot
            self.app = Application.builder().token(self.config.bot_token).build()
            
            # Add command handlers
            self.app.add_handler(CommandHandler("start", self.start_command))
            self.app.add_handler(CommandHandler("status", self.status_command))
            self.app.add_handler(CommandHandler("score", self.manual_score_command))
            self.app.add_handler(CommandHandler("hitrate", self.hitrate_command))
            
            # Initialize data ingestor
            await self.data_ingestor.initialize()
            
            # Setup scheduler
            await self.setup_scheduler()
            
            logger.info("Bot inicializado com sucesso!")
            
        except Exception as e:
            logger.error(f"Erro na inicialização: {e}")
            raise
    
    async def setup_scheduler(self):
        """Configura agendamento automático dos indicadores"""
        ny_tz = pytz.timezone('America/New_York')
        
        # Schedule major economic indicators
        schedules = {
            'ADP': {'cron': '15 8 * * 3', 'func': self.process_adp},  # Wed 08:15 NY
            'NFP': {'cron': '30 8 1-7 * 5', 'func': self.process_nfp},  # First Fri 08:30 NY
            'CPI': {'cron': '30 8 10-16 * *', 'func': self.process_cpi},  # Mid-month 08:30 NY
            'PCE': {'cron': '30 8 25-31 * *', 'func': self.process_pce},  # End-month 08:30 NY
            'ISM_MFG': {'cron': '0 10 1 * *', 'func': self.process_ism_mfg},  # 1st 10:00 NY
            'ISM_SVCS': {'cron': '0 10 3-9 * *', 'func': self.process_ism_services},  # 3rd+ 10:00 NY
            'CLAIMS': {'cron': '30 8 * * 4', 'func': self.process_claims},  # Thu 08:30 NY
            'FOMC': {'cron': '0 14 * * *', 'func': self.check_fomc},  # 14:00 NY (dynamic)
        }
        
        scheduler = AsyncIOScheduler(timezone=ny_tz)
        
        for name, config in schedules.items():
            scheduler.add_job(
                config['func'],
                trigger=CronTrigger.from_crontab(config['cron'], timezone=ny_tz),
                id=name,
                max_instances=1,
                replace_existing=True
            )
            logger.info(f"Scheduled {name}: {config['cron']}")
        
        scheduler.start()
        logger.info("Scheduler iniciado com timezone America/New_York")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para comando /start"""
        welcome_msg = """
🧭 **Bot Macroeconômico USD** 

Monitoro indicadores econômicos dos EUA para prever o direcional do dólar.

**Comandos disponíveis:**
• `/status` - Status do bot e próximos releases
• `/score` - Análise manual do USD score atual  
• `/hitrate` - Performance histórica do bot

**Indicadores monitorados:**
• Emprego: NFP, Unemployment, AHE, ADP, Claims
• Inflação: CPI, Core CPI, PCE, Core PCE
• Atividade: ISM Manufacturing/Services

Análises automáticas nos horários de release (NY timezone).
        """
        await update.message.reply_text(welcome_msg, parse_mode='Markdown')
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para comando /status"""
        try:
            # Get next economic releases
            releases = await self.data_ingestor.get_upcoming_releases(days=7)
            
            status_msg = "📊 **Status do Bot**\n\n"
            status_msg += f"🟢 Bot operacional\n"
            status_msg += f"📅 Timezone: America/New_York\n"
            status_msg += f"🔄 Último update: {self.data_ingestor.last_update}\n\n"
            
            if releases:
                status_msg += "📋 **Próximos Releases (7 dias):**\n"
                for release in releases[:10]:  # Limit to 10
                    status_msg += f"• {release['date']} {release['time']} - {release['event']}\n"
            else:
                status_msg += "📋 Nenhum release relevante nos próximos 7 dias\n"
            
            await update.message.reply_text(status_msg, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Erro no comando status: {e}")
            await update.message.reply_text("❌ Erro ao buscar status")
    
    async def manual_score_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para análise manual do USD score"""
        try:
            # Get latest economic data
            latest_data = await self.data_ingestor.get_latest_data()
            
            if not latest_data:
                await update.message.reply_text("❌ Nenhum dado recente disponível")
                return
            
            # Calculate USD score
            analysis = self.scoring_engine.calculate_usd_score(latest_data)
            
            # Format message
            message = self.format_analysis_message(analysis)
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Erro no comando score: {e}")
            await update.message.reply_text("❌ Erro ao calcular score")
    
    async def hitrate_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para métricas de hit-rate"""
        try:
            metrics = self.hit_rate_tracker.get_performance_metrics()
            
            msg = "📈 **Performance do Bot (Hit-Rate)**\n\n"
            
            if metrics:
                msg += f"🎯 **Geral:**\n"
                msg += f"• Hit-rate 30min: {metrics['overall']['30m']:.1%}\n"
                msg += f"• Hit-rate 60min: {metrics['overall']['60m']:.1%}\n"
                msg += f"• Hit-rate 120min: {metrics['overall']['120m']:.1%}\n"
                msg += f"• Total análises: {metrics['total_predictions']}\n\n"
                
                msg += f"📊 **Por Indicador:**\n"
                for indicator, stats in metrics['by_indicator'].items():
                    msg += f"• {indicator}: {stats['hit_rate']:.1%} ({stats['count']} análises)\n"
                    
            else:
                msg += "📊 Ainda coletando dados para calcular performance..."
            
            await update.message.reply_text(msg, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Erro no comando hitrate: {e}")
            await update.message.reply_text("❌ Erro ao buscar métricas")
    
    # Economic indicator processors
    async def process_nfp(self):
        """Processa release do NFP (Payroll)"""
        await self._process_indicator('NFP', ['Nonfarm Payrolls', 'Unemployment Rate', 'Average Hourly Earnings'])
    
    async def process_cpi(self):
        """Processa release do CPI"""
        await self._process_indicator('CPI', ['Consumer Price Index', 'Core CPI'])
    
    async def process_pce(self):
        """Processa release do PCE"""
        await self._process_indicator('PCE', ['Personal Consumption Expenditures', 'Core PCE'])
    
    async def process_adp(self):
        """Processa release do ADP"""
        await self._process_indicator('ADP', ['ADP Employment Change'])
    
    async def process_ism_mfg(self):
        """Processa ISM Manufacturing"""
        await self._process_indicator('ISM_MFG', ['ISM Manufacturing PMI'])
    
    async def process_ism_services(self):
        """Processa ISM Services"""
        await self._process_indicator('ISM_SVCS', ['ISM Services PMI'])
    
    async def process_claims(self):
        """Processa Weekly Claims"""
        await self._process_indicator('CLAIMS', ['Initial Jobless Claims'])
    
    async def check_fomc(self):
        """Verifica se há FOMC hoje"""
        fomc_today = await self.data_ingestor.check_fomc_today()
        if fomc_today:
            await self._process_indicator('FOMC', ['FOMC Rate Decision'])
    
    async def _process_indicator(self, indicator_type: str, event_names: list):
        """Processa um indicador específico"""
        try:
            logger.info(f"Processando {indicator_type}...")
            
            # Get fresh data for this indicator
            data = await self.data_ingestor.get_indicator_data(event_names)
            
            if not data:
                logger.warning(f"Nenhum dado disponível para {indicator_type}")
                return
            
            # Calculate USD score
            analysis = self.scoring_engine.calculate_usd_score(data)
            
            if analysis['score'] is None:
                logger.warning(f"Score não calculado para {indicator_type}")
                return
            
            # Format and send message
            message = self.format_analysis_message(analysis, indicator_type)
            
            # Send to default chat
            bot = Bot(token=self.config.bot_token)
            await bot.send_message(
                chat_id=self.config.default_chat_id,
                text=message,
                parse_mode='Markdown'
            )
            
            # Log for hit-rate tracking
            self.hit_rate_tracker.log_prediction(
                event_type=indicator_type,
                usd_score=analysis['score'],
                classification=analysis['classification'],
                timestamp=analysis['timestamp']
            )
            
            logger.info(f"Análise {indicator_type} enviada: Score {analysis['score']:.2f}")
            
        except Exception as e:
            logger.error(f"Erro ao processar {indicator_type}: {e}")
            # Try to send error notification
            try:
                bot = Bot(token=self.config.bot_token)
                await bot.send_message(
                    chat_id=self.config.default_chat_id,
                    text=f"❌ Erro ao processar {indicator_type}: {str(e)}"
                )
            except:
                pass
    
    def format_analysis_message(self, analysis: Dict[str, Any], indicator_type: str = "Manual") -> str:
        """Formata mensagem de análise"""
        from datetime import datetime
        import pytz
        
        ny_tz = pytz.timezone('America/New_York')
        now_ny = datetime.now(ny_tz)
        
        msg = f"🧭 **Leitura Macro USD** — {now_ny.strftime('%d/%m/%Y %H:%M')} (NY)\n\n"
        
        # Indicators breakdown
        if analysis.get('indicators'):
            for indicator in analysis['indicators']:
                name = indicator['name']
                actual = indicator.get('actual', 'N/A')
                consensus = indicator.get('consensus', 'N/A')
                component_score = indicator.get('component_score', 0)
                weight = indicator.get('weight', 0)
                surprise = indicator.get('surprise_pct', 0)
                
                msg += f"• **{name}**: {actual} vs {consensus} → surpresa {surprise:+.0%} | comp {component_score:+.1f} (w={weight})\n"
        
        msg += f"\n🧮 **USD Score**: *{analysis['score']:+.2f}* → *{analysis['classification']}* (Confiança: {analysis['confidence']})\n\n"
        
        # Scenarios
        base_scenario = analysis.get('base_scenario', {})
        alt_scenario = analysis.get('alternative_scenario', {})
        
        msg += f"📌 **Cenário base** ({base_scenario.get('probability', 65)}%): {base_scenario.get('description', 'Análise em desenvolvimento')}\n"
        msg += f"📌 **Alternativo** ({alt_scenario.get('probability', 35)}%): {alt_scenario.get('description', 'Cenário contrário')}\n\n"
        
        # Directional suggestion
        direction = analysis.get('directional_suggestion', 'Aguardar confirmação')
        pairs = analysis.get('suggested_pairs', ['EURUSD', 'GBPUSD', 'USDJPY'])
        
        msg += f"🎯 **Direcional**: {direction}\n"
        msg += f"👀 **Pares/mercados**: {', '.join(pairs)}\n"
        
        return msg
    
    async def run(self):
        """Executa o bot"""
        try:
            await self.initialize()
            
            logger.info("🚀 Bot Macroeconômico USD iniciado!")
            logger.info(f"Monitorando chat: {self.config.default_chat_id}")
            
            # Run the bot
            await self.app.run_polling(drop_pending_updates=True)
            
        except Exception as e:
            logger.error(f"Erro fatal: {e}")
            raise
        finally:
            # Cleanup
            if self.data_ingestor:
                await self.data_ingestor.close()

async def main():
    """Função principal"""
    bot = MacroEconomicBot()
    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot finalizado pelo usuário")
    except Exception as e:
        logger.error(f"Erro fatal: {e}")
        sys.exit(1)