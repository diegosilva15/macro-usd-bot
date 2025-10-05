#!/usr/bin/env python3
"""
🤖 BOT MACROECONÔMICO USD COM IA - VERSÃO COMPLETA
Análise inteligente para DXY, Commodities e Forex com recomendações de entrada
"""

import os
import logging
import sys
from datetime import datetime, timedelta
from typing import Dict, Any
import pytz

from dotenv import load_dotenv
load_dotenv()

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MacroUSDBot:
    def __init__(self):
        self.bot_token = os.getenv('BOT_TOKEN')
        if not self.bot_token:
            raise ValueError("❌ BOT_TOKEN não configurado! Configure no Render: Settings > Environment > BOT_TOKEN")

        self.ny_tz = pytz.timezone('America/New_York')

        self.indicator_weights = {
            'nfp': 0.25,
            'unemployment': 0.15,
            'cpi': 0.20,
            'pce': 0.15,
            'ism_manufacturing': 0.10,
            'ism_services': 0.10,
            'retail_sales': 0.05
        }

        self.current_data = {
            'nfp': {'value': 254000, 'consensus': 150000, 'previous': 159000},
            'unemployment': {'value': 4.1, 'consensus': 4.2, 'previous': 4.2},
            'cpi': {'value': 2.4, 'consensus': 2.3, 'previous': 2.5},
            'pce': {'value': 2.2, 'consensus': 2.1, 'previous': 2.5},
            'ism_manufacturing': {'value': 47.2, 'consensus': 47.5, 'previous': 47.2},
            'ism_services': {'value': 54.9, 'consensus': 51.7, 'previous': 51.5},
            'retail_sales': {'value': 0.4, 'consensus': 0.3, 'previous': 0.1}
        }

        logger.info("✅ Bot Macroeconômico USD com IA inicializado")

    def calculate_usd_score(self) -> Dict[str, Any]:
        total_score = 0.0
        component_scores = {}

        for indicator, weight in self.indicator_weights.items():
            data = self.current_data[indicator]

            if indicator in ['nfp', 'retail_sales', 'ism_manufacturing', 'ism_services']:
                consensus_beat = (data['value'] - data['consensus']) / abs(data['consensus']) if data['consensus'] else 0
                mom_improvement = (data['value'] - data['previous']) / abs(data['previous']) if data['previous'] else 0
            elif indicator == 'unemployment':
                consensus_beat = -(data['value'] - data['consensus']) / abs(data['consensus']) if data['consensus'] else 0
                mom_improvement = -(data['value'] - data['previous']) / abs(data['previous']) if data['previous'] else 0
            else:
                consensus_beat = -(data['value'] - data['consensus']) / abs(data['consensus']) if data['consensus'] else 0
                mom_improvement = -(data['value'] - data['previous']) / abs(data['previous']) if data['previous'] else 0

            component_score = max(-2, min(2, (consensus_beat + mom_improvement) * 2))
            component_scores[indicator] = {'score': component_score, 'weight': weight, 'contribution': component_score * weight}
            total_score += component_score * weight

        if total_score >= 1.5:
            classification = "🟢 FORTE ALTA"
        elif total_score >= 0.5:
            classification = "🔵 MODERADA ALTA"
        elif total_score >= -0.5:
            classification = "🟡 NEUTRO"
        elif total_score >= -1.5:
            classification = "🟠 MODERADA BAIXA"
        else:
            classification = "🔴 FORTE BAIXA"

        confidence_scores = [abs(comp['score']) for comp in component_scores.values()]
        confidence = "Alta" if sum(confidence_scores) / len(confidence_scores) > 1.2 else "Média" if sum(confidence_scores) / len(confidence_scores) > 0.7 else "Baixa"

        return {
            'score': round(total_score, 2),
            'classification': classification,
            'confidence': confidence,
            'components': component_scores,
            'timestamp': datetime.now(self.ny_tz)
        }

    def _get_ai_interpretation(self, score: float) -> str:
        if score >= 1.5:
            return "🟢 Cenário MUITO BULLISH para USD."
        elif score >= 0.5:
            return "🔵 Cenário BULLISH moderado."
        elif score <= -1.5:
            return "🔴 Cenário MUITO BEARISH para USD."
        elif score <= -0.5:
            return "🟠 Cenário BEARISH moderado."
        else:
            return "🟡 Cenário NEUTRO/MISTO."

    def _get_general_recommendation(self, score: float) -> str:
        if score >= 1.0:
            return "✅ LONG DXY | SHORT EURUSD, GBPUSD | SHORT OURO"
        elif score >= 0.3:
            return "⚠️ Viés LONG USD (aguardar confirmação)"
        elif score <= -1.0:
            return "✅ SHORT DXY | LONG EURUSD, GBPUSD | LONG OURO"
        elif score <= -0.3:
            return "⚠️ Viés SHORT USD (aguardar confirmação)"
        else:
            return "🚫 FORA DO MERCADO - Aguardar direcionamento"

    def _analyze_dxy(self, score: float) -> Dict[str, Any]:
        if score >= 1.0:
            return {'direction': '📈 COMPRA (LONG)', 'confidence': '95%', 'entry': '104.80 - 105.20', 'stop_loss': '104.20',
                    'take_profit_1': '106.50', 'take_profit_2': '108.00', 'take_profit_3': '109.50', 'risk_reward': '1:3.5',
                    'reasoning': 'Dados macro fortemente bullish.', 'timeframe': 'Swing (5-15 dias)', 'position_size': '2% do capital'}
        elif score >= 0.3:
            return {'direction': '📈 COMPRA MODERADA', 'confidence': '70%', 'entry': '104.00 - 104.50', 'stop_loss': '103.50',
                    'take_profit_1': '105.50', 'take_profit_2': '106.50', 'take_profit_3': '107.50', 'risk_reward': '1:2.5',
                    'reasoning': 'Viés bullish moderado.', 'timeframe': 'Day/Swing', 'position_size': '1.5% do capital'}
        elif score <= -1.0:
            return {'direction': '📉 VENDA (SHORT)', 'confidence': '90%', 'entry': '104.50 - 105.00', 'stop_loss': '105.50',
                    'take_profit_1': '103.00', 'take_profit_2': '101.50', 'take_profit_3': '100.00', 'risk_reward': '1:3.0',
                    'reasoning': 'Dados macro fracos.', 'timeframe': 'Swing (5-15 dias)', 'position_size': '2% do capital'}
        elif score <= -0.3:
            return {'direction': '📉 VENDA MODERADA', 'confidence': '65%', 'entry': '104.80 - 105.20', 'stop_loss': '105.80',
                    'take_profit_1': '103.50', 'take_profit_2': '102.50', 'take_profit_3': '101.50', 'risk_reward': '1:2.0',
                    'reasoning': 'Pressão bearish no USD.', 'timeframe': 'Day Trade', 'position_size': '1% do capital'}
        else:
            return {'direction': '🟡 AGUARDAR (LATERAL)', 'confidence': '40%', 'entry': 'Não recomendado', 'stop_loss': 'N/A',
                    'take_profit_1': 'N/A', 'take_profit_2': 'N/A', 'take_profit_3': 'N/A', 'risk_reward': 'N/A',
                    'reasoning': 'Mercado sem direção clara.', 'timeframe': 'Fora do mercado', 'position_size': '0%'}

    def _analyze_eurusd(self, score: float) -> Dict[str, Any]:
        if score >= 1.0:
            return {'direction': '📉 VENDA (SHORT)', 'confidence': '90%', 'entry': '1.1050 - 1.1100', 'stop_loss': '1.1180',
                    'take_profit_1': '1.0900', 'take_profit_2': '1.0750', 'take_profit_3': '1.0600', 'risk_reward': '1:3.0',
                    'reasoning': 'USD forte pressiona EUR.', 'timeframe': 'Swing', 'position_size': '2% do capital'}
        elif score <= -1.0:
            return {'direction': '📈 COMPRA (LONG)', 'confidence': '85%', 'entry': '1.0950 - 1.1000', 'stop_loss': '1.0880',
                    'take_profit_1': '1.1150', 'take_profit_2': '1.1300', 'take_profit_3': '1.1450', 'risk_reward': '1:2.8',
                    'reasoning': 'USD fraco favorece EUR.', 'timeframe': 'Swing', 'position_size': '2% do capital'}
        else:
            return {'direction': '🟡 AGUARDAR', 'confidence': '50%', 'entry': 'Range 1.0950 - 1.1100',
                    'reasoning': 'Mercado lateral.', 'timeframe': 'Scalp/Day', 'position_size': '1% do capital'}

    def _analyze_gbpusd(self, score: float) -> Dict[str, Any]:
        if score >= 1.0:
            return {'direction': '📉 VENDA (SHORT)', 'confidence': '85%', 'entry': '1.3250 - 1.3300', 'stop_loss': '1.3380',
                    'take_profit_1': '1.3100', 'take_profit_2': '1.2950', 'take_profit_3': '1.2800', 'risk_reward': '1:2.5',
                    'reasoning': 'USD forte + incertezas UK.', 'timeframe': 'Swing', 'position_size': '1.5% do capital'}
        elif score <= -1.0:
            return {'direction': '📈 COMPRA (LONG)', 'confidence': '80%', 'entry': '1.3150 - 1.3200', 'stop_loss': '1.3080',
                    'take_profit_1': '1.3350', 'take_profit_2': '1.3500', 'take_profit_3': '1.3650', 'risk_reward': '1:2.8',
                    'reasoning': 'USD fraco favorece GBP.', 'timeframe': 'Swing', 'position_size': '1.5% do capital'}
        else:
            return {'direction': '🟡 AGUARDAR', 'confidence': '45%', 'reasoning': 'Consolidação.', 'timeframe': 'Fora', 'position_size': '0%'}

    def _analyze_usdjpy(self, score: float) -> Dict[str, Any]:
        if score >= 1.0:
            return {'direction': '📈 COMPRA (LONG)', 'confidence': '88%', 'entry': '148.50 - 149.00', 'stop_loss': '147.80',
                    'take_profit_1': '150.50', 'take_profit_2': '152.00', 'take_profit_3': '154.00', 'risk_reward': '1:3.2',
                    'reasoning': 'Divergência Fed/BoJ.', 'timeframe': 'Swing', 'position_size': '2% do capital'}
        elif score <= -1.0:
            return {'direction': '📉 VENDA (SHORT)', 'confidence': '75%', 'entry': '149.50 - 150.00', 'stop_loss': '150.80',
                    'take_profit_1': '147.50', 'take_profit_2': '145.50', 'take_profit_3': '143.00', 'risk_reward': '1:2.5',
                    'reasoning': 'USD fraco + possível intervenção.', 'timeframe': 'Swing', 'position_size': '1.5% do capital'}
        else:
            return {'direction': '🟡 AGUARDAR', 'confidence': '50%', 'reasoning': 'Range 148-150.', 'timeframe': 'Fora', 'position_size': '0%'}

    def _analyze_gold(self, score: float) -> Dict[str, Any]:
        if score >= 1.0:
            return {'direction': '📉 VENDA (SHORT)', 'confidence': '80%', 'entry': '2650 - 2670', 'stop_loss': '2700',
                    'take_profit_1': '2600', 'take_profit_2': '2550', 'take_profit_3': '2500', 'risk_reward': '1:2.5',
                    'reasoning': 'USD forte pressiona ouro.', 'timeframe': 'Swing', 'position_size': '1.5% do capital'}
        elif score <= -1.0:
            return {'direction': '📈 COMPRA (LONG)', 'confidence': '92%', 'entry': '2620 - 2640', 'stop_loss': '2590',
                    'take_profit_1': '2700', 'take_profit_2': '2750', 'take_profit_3': '2800', 'risk_reward': '1:3.5',
                    'reasoning': 'USD fraco + tensões.', 'timeframe': 'Swing', 'position_size': '2% do capital'}
        else:
            return {'direction': '🟡 AGUARDAR', 'confidence': '55%', 'reasoning': 'Consolidação 2600-2670.', 'timeframe': 'Fora', 'position_size': '0%'}

    def _analyze_oil(self, score: float) -> Dict[str, Any]:
        if score >= 0.5:
            return {'direction': '📉 VIÉS BAIXA', 'confidence': '65%', 'entry': '73.50 - 75.00', 'stop_loss': '76.50',
                    'take_profit_1': '70.00', 'take_profit_2': '67.50', 'take_profit_3': '65.00', 'risk_reward': '1:2.0',
                    'reasoning': 'USD forte pressiona commodities.', 'timeframe': 'Swing', 'position_size': '1% do capital'}
        elif score <= -0.5:
            return {'direction': '📈 VIÉS ALTA', 'confidence': '70%', 'entry': '70.00 - 71.50', 'stop_loss': '68.50',
                    'take_profit_1': '74.00', 'take_profit_2': '77.00', 'take_profit_3': '80.00', 'risk_reward': '1:2.5',
                    'reasoning': 'USD fraco + tensões geopolíticas.', 'timeframe': 'Swing', 'position_size': '1.5% do capital'}
        else:
            return {'direction': '🟡 NEUTRO', 'confidence': '50%', 'reasoning': 'Fatores geopolíticos dominam.', 'timeframe': 'Aguardar', 'position_size': '0%'}

    def get_ai_trade_recommendation(self, score: float, asset: str) -> Dict[str, Any]:
        mapping = {
            'DXY': self._analyze_dxy,
            'EURUSD': self._analyze_eurusd,
            'GBPUSD': self._analyze_gbpusd,
            'USDJPY': self._analyze_usdjpy,
            'GOLD': self._analyze_gold,
            'OIL': self._analyze_oil,
        }
        return mapping.get(asset, lambda s: {}) (score)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("📊 Análise Completa", callback_data='analise')],
            [InlineKeyboardButton("💹 DXY", callback_data='dxy'), InlineKeyboardButton("💶 EURUSD", callback_data='eurusd')],
            [InlineKeyboardButton("💷 GBPUSD", callback_data='gbpusd'), InlineKeyboardButton("💴 USDJPY", callback_data='usdjpy')],
            [InlineKeyboardButton("🥇 OURO", callback_data='gold'), InlineKeyboardButton("🛢️ PETRÓLEO", callback_data='oil')],
            [InlineKeyboardButton("📅 Calendário", callback_data='calendario')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        response = """🤖 BOT MACROECONÔMICO USD COM IA

🎯 Análise Inteligente + Recomendações de Entrada

Use os botões ou comandos:
/analise /dxy /eurusd /gbpusd /usdjpy /gold /oil /calendario
"""
        await update.message.reply_text(response, reply_markup=reply_markup, parse_mode='Markdown')

    async def analise_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🔄 Analisando dados macroeconômicos...")
        try:
            usd = self.calculate_usd_score()
            now = datetime.now(self.ny_tz)

            components_text = ""
            for indicator, data in usd['components'].items():
                emoji = "📈" if data['score'] > 0 else "📉" if data['score'] < 0 else "➡️"
                components_text += f"• {indicator.upper()}: {data['score']:+.1f} {emoji}\n"

            response = f"""📊 ANÁLISE MACROECONÔMICA USD
*{now.strftime('%d/%m/%Y %H:%M')} ET*

🎯 USD SCORE: {usd['score']:+.2f}
{usd['classification']}
🎲 Confiança: {usd['confidence']}

📋 Componentes:
{components_text}

💡 Interpretação IA:
{self._get_ai_interpretation(usd['score'])}

🎯 Recomendação Geral:
{self._get_general_recommendation(usd['score'])}
"""
            await update.message.reply_text(response, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Erro na análise: {e}")
            await update.message.reply_text(f"❌ Erro: {str(e)}")

    async def _send_trade_recommendation(self, update: Update, asset: str):
        try:
            usd = self.calculate_usd_score()
            rec = self.get_ai_trade_recommendation(usd['score'], asset)
            now = datetime.now(self.ny_tz)

            response = f"""🤖 RECOMENDAÇÃO IA - {asset}
*{now.strftime('%d/%m/%Y %H:%M')} ET*

📊 USD Score: {usd['score']:+.2f}

🎯 DIREÇÃO: {rec['direction']}
📈 Confiança: {rec['confidence']}

💰 SETUP:
• Entry: {rec.get('entry', 'N/A')}
• Stop Loss: {rec.get('stop_loss', 'N/A')}
• TP1: {rec.get('take_profit_1', 'N/A')}
• TP2: {rec.get('take_profit_2', 'N/A')}
• TP3: {rec.get('take_profit_3', 'N/A')}

📊 Risk/Reward: {rec.get('risk_reward', 'N/A')}
⏱️ Timeframe: {rec.get('timeframe', 'N/A')}
💼 Tamanho: {rec.get('position_size', 'N/A')}

🧠 Análise IA:
{rec.get('reasoning', '—')}

⚠️ Use sempre stop loss e não arrisque >2% por trade.
"""
            await update.message.reply_text(response, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Erro em {asset}: {e}")
            await update.message.reply_text(f"❌ Erro ao analisar {asset}")

    async def dxy_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE): await self._send_trade_recommendation(update, 'DXY')
    async def eurusd_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE): await self._send_trade_recommendation(update, 'EURUSD')
    async def gbpusd_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE): await self._send_trade_recommendation(update, 'GBPUSD')
    async def usdjpy_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE): await self._send_trade_recommendation(update, 'USDJPY')
    async def gold_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE): await self._send_trade_recommendation(update, 'GOLD')
    async def oil_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE): await self._send_trade_recommendation(update, 'OIL')

    async def calendario_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        now = datetime.now(self.ny_tz)
        calendar = f"""📅 CALENDÁRIO ECONÔMICO
*Semana de {now.strftime('%d/%m/%Y')}*

SEG: ISM Manufacturing, Construction Spending
TER: JOLTs, Trade Balance
QUA: ADP, ISM Services
QUI: Jobless Claims, Continuing Claims
SEX: NFP, Unemployment, Hourly Earnings

⚠️ Alta volatilidade: Sexta (NFP)
"""
        await update.message.reply_text(calendar, parse_mode='Markdown')

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        update.message = query.message
        data = query.data
        if data == 'analise': await self.analise_command(update, context)
        elif data == 'dxy': await self.dxy_command(update, context)
        elif data == 'eurusd': await self.eurusd_command(update, context)
        elif data == 'gbpusd': await self.gbpusd_command(update, context)
        elif data == 'usdjpy': await self.usdjpy_command(update, context)
        elif data == 'gold': await self.gold_command(update, context)
        elif data == 'oil': await self.oil_command(update, context)
        elif data == 'calendario': await self.calendario_command(update, context)

def main():
    try:
        logger.info("🚀 Iniciando Bot Macroeconômico USD com IA...")
        bot = MacroUSDBot()
        application = Application.builder().token(bot.bot_token).build()

        application.add_handler(CommandHandler("start", bot.start_command))
        application.add_handler(CommandHandler("analise", bot.analise_command))
        application.add_handler(CommandHandler("dxy", bot.dxy_command))
        application.add_handler(CommandHandler("eurusd", bot.eurusd_command))
        application.add_handler(CommandHandler("gbpusd", bot.gbpusd_command))
        application.add_handler(CommandHandler("usdjpy", bot.usdjpy_command))
        application.add_handler(CommandHandler("gold", bot.gold_command))
        application.add_handler(CommandHandler("oil", bot.oil_command))
        application.add_handler(CommandHandler("calendario", bot.calendario_command))
        application.add_handler(CallbackQueryHandler(bot.button_callback))

        logger.info("✅ Bot pronto! Iniciando polling...")
        application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
    except KeyboardInterrupt:
        logger.info("🛑 Bot interrompido")
    except Exception as e:
        logger.error(f"❌ Erro crítico: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
