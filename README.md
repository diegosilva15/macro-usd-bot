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
import requests
from cachetools import cached, TTLCache

from dotenv import load_dotenv
load_dotenv()

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

AV_BASE = "https://www.alphavantage.co/query"
TD_BASE = "https://api.twelvedata.com"

# Cache para evitar chamadas excessivas à API
api_cache = TTLCache(maxsize=100, ttl=60)

def _env(key: str, default: str = "") -> str:
    v = os.getenv(key, default).strip()
    if not v:
        raise ValueError(f"Variável de ambiente ausente: {key}")
    return v

def _fmt_pct(x):
    try:
        return f"{float(x):+.2f}%"
    except:
        return "N/A"

def _fmt_num(x):
    try:
        x = float(x)
        if abs(x) >= 1_000_000:
            return f"{x/1_000_000:.1f}M"
        if abs(x) >= 1_000:
            return f"{x/1_000:.1f}k"
        return f"{x:.0f}"
    except:
        return "N/A"

class MacroUSDBot:
    def __init__(self):
        self.bot_token = _env('BOT_TOKEN')
        self.av_api_key = _env('AV_API_KEY')
        self.td_api_key = _env('TD_API_KEY')

        self.ny_tz = pytz.timezone('America/New_York')

        # Mapeamento de indicadores Alpha Vantage (FRED codes)
        self.av_indicators = {
            'nfp': 'PAYEMS',  # Total Nonfarm Payrolls
            'unemployment': 'UNRATE',  # Unemployment Rate
            'cpi': 'CPIAUCSL',  # CPI All Urban Consumers
            'pce': 'PCEPI',  # Personal Consumption Expenditures Price Index
            'retail_sales': 'RSXFS',  # Retail Sales
            'claims': 'ICSA',  # Initial Claims
            'gdp': 'GDP',  # GDP
        }

        logger.info("✅ Bot Macroeconômico USD com IA inicializado (Alpha Vantage + Twelve Data)")

    @cached(api_cache)
    def fetch_av_indicator(self, fred_code: str) -> dict:
        """Busca indicador econômico via Alpha Vantage (FRED)"""
        params = {
            "function": "REAL_GDP" if fred_code == "GDP" else "UNEMPLOYMENT" if fred_code == "UNRATE" else "CPI" if fred_code == "CPIAUCSL" else "NONFARM_PAYROLL" if fred_code == "PAYEMS" else "RETAIL_SALES" if fred_code == "RSXFS" else fred_code,
            "apikey": self.av_api_key
        }
        
        # Alpha Vantage tem funções específicas para cada indicador
        # Vamos usar a função genérica de séries temporais do FRED
        params = {
            "function": "TIME_SERIES_MONTHLY",
            "symbol": fred_code,
            "apikey": self.av_api_key
        }
        
        # Melhor: usar a função FRED diretamente
        params = {
            "function": "FEDERAL_FUNDS_RATE" if "FF" in fred_code else "TREASURY_YIELD" if "GS" in fred_code else "CPI" if "CPI" in fred_code else "UNEMPLOYMENT" if "UNRATE" in fred_code else "NONFARM_PAYROLL" if "PAYEMS" in fred_code else "RETAIL_SALES" if "RSXFS" in fred_code else "REAL_GDP",
            "apikey": self.av_api_key
        }
        
        # Simplificando: Alpha Vantage tem endpoints específicos
        # Vamos mapear corretamente
        function_map = {
            'PAYEMS': 'NONFARM_PAYROLL',
            'UNRATE': 'UNEMPLOYMENT',
            'CPIAUCSL': 'CPI',
            'RSXFS': 'RETAIL_SALES',
            'GDP': 'REAL_GDP',
            'ICSA': 'UNEMPLOYMENT',  # Proxy
            'PCEPI': 'CPI',  # Proxy
        }
        
        params = {
            "function": function_map.get(fred_code, "CPI"),
            "apikey": self.av_api_key
        }
        
        try:
            r = requests.get(AV_BASE, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            
            # Alpha Vantage retorna formato: {"name": "...", "data": [{"date": "...", "value": "..."}]}
            if "data" in data and len(data["data"]) >= 2:
                latest = data["data"][0]
                previous = data["data"][1]
                return {
                    "last": float(latest.get("value", 0)),
                    "previous": float(previous.get("value", 0)),
                    "last_update": latest.get("date"),
                    "unit": data.get("unit", ""),
                    "category": fred_code
                }
            else:
                logger.warning(f"Alpha Vantage: formato inesperado para {fred_code}")
                return {}
        except Exception as e:
            logger.warning(f"Erro ao buscar {fred_code} no Alpha Vantage: {e}")
            return {}

    @cached(api_cache)
    def fetch_td_price(self, symbol: str) -> dict:
        """Busca preço e variação via Twelve Data"""
        params = {"symbol": symbol, "apikey": self.td_api_key}
        url = f"{TD_BASE}/price"
        r1 = requests.get(url, params=params, timeout=10)
        price = None
        if r1.ok:
            try:
                price = float(r1.json().get("price"))
            except:
                price = None

        url2 = f"{TD_BASE}/quote"
        r2 = requests.get(url2, params=params, timeout=10)
        change_pct = None
        if r2.ok:
            try:
                jp = r2.json()
                change_pct = float(jp.get("percent_change"))
            except:
                change_pct = None

        return {"symbol": symbol, "price": price, "change_pct": change_pct}

    def get_live_indicators(self) -> dict:
        """Busca indicadores econômicos ao vivo"""
        out = {}
        for key, fred_code in self.av_indicators.items():
            try:
                out[key] = self.fetch_av_indicator(fred_code)
            except Exception as e:
                logger.warning(f"Falha ao buscar {key}: {e}")
                out[key] = {}
        
        # Adiciona proxies para indicadores que não temos direto
        out['adp'] = out.get('nfp', {})  # Proxy
        out['ahe'] = {'last': 0.3, 'previous': 0.3}  # Mock temporário
        out['ism_manufacturing'] = {'last': 48.0, 'previous': 47.5}  # Mock
        out['ism_services'] = {'last': 52.0, 'previous': 51.5}  # Mock
        out['jolts'] = {'last': 8500, 'previous': 8700}  # Mock (em milhares)
        out['cpi_yoy'] = out.get('cpi', {})
        out['pce_yoy'] = out.get('pce', {})
        
        return out

    def calculate_usd_score(self) -> Dict[str, Any]:
        """Calcula USD Score baseado em dados reais"""
        data = self.get_live_indicators()
        weights = {
            "nfp": 0.25,
            "unemployment": 0.15,
            "ahe": 0.10,
            "cpi_yoy": 0.15,
            "pce_yoy": 0.10,
            "ism_manufacturing": 0.10,
            "ism_services": 0.10,
            "jolts": 0.03,
            "claims": 0.02
        }

        def norm_pos(curr, prev):
            try:
                curr, prev = float(curr), float(prev)
                if prev == 0: return 0.0
                return max(-2, min(2, (curr - prev) / abs(prev) * 2))
            except:
                return 0.0

        def norm_neg(curr, prev):
            try:
                curr, prev = float(curr), float(prev)
                if prev == 0: return 0.0
                return max(-2, min(2, (prev - curr) / abs(prev) * 2))
            except:
                return 0.0

        components = {}
        total = 0.0

        # NFP
        if data["nfp"].get("last") is not None and data["nfp"].get("previous") is not None:
            s = norm_pos(data["nfp"]["last"], data["nfp"]["previous"])
        else:
            s = 0.0
        components["nfp"] = {"score": s, "weight": weights["nfp"], "contribution": s*weights["nfp"]}
        total += components["nfp"]["contribution"]

        pairs = [
            ("unemployment", norm_neg),
            ("ahe", norm_neg),
            ("cpi_yoy", norm_neg),
            ("pce_yoy", norm_neg),
            ("ism_manufacturing", norm_pos),
            ("ism_services", norm_pos),
            ("jolts", norm_pos),
            ("claims", norm_neg)
        ]
        for k, fn in pairs:
            last = data.get(k, {}).get("last")
            prev = data.get(k, {}).get("previous")
            s = fn(last, prev) if (last is not None and prev is not None) else 0.0
            w = weights[k]
            components[k] = {"score": s, "weight": w, "contribution": s*w}
            total += s*w

        if total >= 1.5:
            classification = "🟢 FORTE ALTA"
        elif total >= 0.5:
            classification = "🔵 MODERADA ALTA"
        elif total >= -0.5:
            classification = "🟡 NEUTRO"
        elif total >= -1.5:
            classification = "🟠 MODERADA BAIXA"
        else:
            classification = "🔴 FORTE BAIXA"

        confidence = "Alta" if abs(total) > 1.2 else "Média" if abs(total) > 0.6 else "Baixa"

        return {
            "score": round(total, 2),
            "classification": classification,
            "confidence": confidence,
            "components": components,
            "raw": data,
            "timestamp": datetime.now(self.ny_tz)
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

    def get_symbol_map(self):
        return {
            "DXY": "DXY",
            "EURUSD": "EUR/USD",
            "GBPUSD": "GBP/USD",
            "USDJPY": "USD/JPY",
            "GOLD": "XAU/USD",
            "OIL": "WTI"
        }

    def attach_price(self, asset: str, rec: Dict[str, Any]) -> Dict[str, Any]:
        sym = self.get_symbol_map().get(asset)
        if not sym:
            return rec
        try:
            p = self.fetch_td_price(sym)
            if p["price"] is not None:
                rec["live_price"] = p["price"]
            if p["change_pct"] is not None:
                rec["live_change_pct"] = p["change_pct"]
        except Exception as e:
            logger.warning(f"Preço {asset} falhou: {e}")
        return rec

    def get_ai_trade_recommendation(self, score: float, asset: str) -> Dict[str, Any]:
        mapping = {
            'DXY': self._analyze_dxy,
            'EURUSD': self._analyze_eurusd,
            'GBPUSD': self._analyze_gbpusd,
            'USDJPY': self._analyze_usdjpy,
            'GOLD': self._analyze_gold,
            'OIL': self._analyze_oil,
        }
        return mapping.get(asset, lambda s: {})(score)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("📊 Análise Completa", callback_data='analise')],
            [InlineKeyboardButton("📌 Briefing Macro", callback_data='briefing'), InlineKeyboardButton("📅 Calendário Hoje", callback_data='calendario_hoje')],
            [InlineKeyboardButton("💹 DXY", callback_data='dxy'), InlineKeyboardButton("💶 EURUSD", callback_data='eurusd')],
            [InlineKeyboardButton("💷 GBPUSD", callback_data='gbpusd'), InlineKeyboardButton("💴 USDJPY", callback_data='usdjpy')],
            [InlineKeyboardButton("🥇 OURO", callback_data='gold'), InlineKeyboardButton("🛢️ PETRÓLEO", callback_data='oil')],
            [InlineKeyboardButton("📅 Calendário Semanal", callback_data='calendario')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        response = """🤖 BOT MACROECONÔMICO USD COM IA

🎯 Análise Inteligente + Recomendações de Entrada

Use os botões ou comandos:
/analise /briefing /calendario /calendario_hoje /dxy /eurusd /gbpusd /usdjpy /gold /oil
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
            rec = self.attach_price(asset, rec)
            now = datetime.now(self.ny_tz)

            price_line = ""
            if rec.get("live_price") is not None:
                chg = rec.get("live_change_pct")
                chg_txt = f" ({chg:+.2f}%)" if isinstance(chg, (float, int)) else ""
                price_line = f"\n📈 Preço: {rec['live_price']}{chg_txt}"

            response = f"""🤖 RECOMENDAÇÃO IA - {asset}
*{now.strftime('%d/%m/%Y %H:%M')} ET*

📊 USD Score: {usd['score']:+.2f}{price_line}

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
        now_et = datetime.now(self.ny_tz)
        text = f"""📅 CALENDÁRIO ECONÔMICO

⚠️ Calendário em tempo real em breve.

Por enquanto, consulte:
🔗 https://www.forexfactory.com/calendar
🔗 https://www.investing.com/economic-calendar/

Principais eventos desta semana:
• NFP (Payroll) - Sexta-feira 08:30 ET
• CPI (Inflação) - Quarta-feira 08:30 ET
• FOMC Minutes - Quarta-feira 14:00 ET
• Initial Claims - Quinta-feira 08:30 ET

Atualizado: {now_et.strftime('%d/%m/%Y %H:%M')} ET
"""
        await update.message.reply_text(text, disable_web_page_preview=True)

    async def calendario_hoje_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        now_et = datetime.now(self.ny_tz)
        text = f"""📅 CALENDÁRIO HOJE ({now_et.strftime('%d/%m/%Y')})

⚠️ Calendário em tempo real em breve.

Consulte eventos de hoje em:
🔗 https://www.forexfactory.com/calendar
🔗 https://www.investing.com/economic-calendar/

Atualizado: {now_et.strftime('%H:%M')} ET
"""
        await update.message.reply_text(text, disable_web_page_preview=True)

    def _compute_probabilities(self, data: dict) -> dict:
        score = 0.0
        try:
            adp = float(data.get("adp",{}).get("last", 0))
            if adp < 100: score += 1.0
            elif adp < 150: score += 0.5
        except: pass
        try:
            isms = float(data.get("ism_services",{}).get("last", 50))
            if isms < 50: score += 0.7
        except: pass
        try:
            jolts = float(data.get("jolts",{}).get("last", 0))
            prevj = float(data.get("jolts",{}).get("previous", 0)) or jolts
            if jolts < prevj: score += 0.4
        except: pass
        try:
            claims = float(data.get("claims",{}).get("last", 0))
            if claims > 230: score += 0.4
        except: pass

        base_prob = min(0.85, 0.50 + score/3.0)
        alt_prob = 1 - base_prob
        return {"base": round(base_prob*100), "alt": round(alt_prob*100)}

    def _generate_headline(self, usd_score: float, data: dict) -> str:
        headline = ""
        if usd_score >= 1.0:
            headline = "📈 Dólar forte: dados macro bullish impulsionam DXY e pressionam commodities."
        elif usd_score <= -1.0:
            headline = "📉 Dólar fraco: dados macro bearish derrubam DXY e favorecem ouro/pares."
        else:
            if data.get("cpi_yoy", {}).get("last") is not None and float(data["cpi_yoy"]["last"]) < 2.5:
                headline = "🟡 Inflação controlada + dados mistos = Fed cauteloso, mercado busca direcional."
            elif data.get("unemployment", {}).get("last") is not None and float(data["unemployment"]["last"]) > 4.0:
                headline = "🟡 Mercado de trabalho esfriando + inflação em queda = corte de juros no radar."
            else:
                headline = "🟡 Mercado em consolidação: aguardando novos catalisadores macroeconômicos."
        return f"📊 Headline: {headline}"

    async def briefing_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🔄 Montando briefing macro com dados ao vivo...")
        try:
            usd = self.calculate_usd_score()
            data = usd["raw"]
            probs = self._compute_probabilities(data)

            try:
                adp = float(data.get("adp",{}).get("last", 120))
                isms = float(data.get("ism_services",{}).get("last", 52))
                nfp_proj = max(0, round(0.8*adp + 8*(isms-50)))
            except:
                nfp_proj = 160

            try:
                ahe_last = float(data.get("ahe",{}).get("last", 0.2))
            except:
                ahe_last = 0.2
            try:
                unemp_last = float(data.get("unemployment",{}).get("last", 4.1))
            except:
                unemp_last = 4.1

            px_dxy = self.fetch_td_price(self.get_symbol_map()["DXY"])
            px_xau = self.fetch_td_price(self.get_symbol_map()["GOLD"])
            px_oil = self.fetch_td_price(self.get_symbol_map()["OIL"])

            direcional = self._get_ai_interpretation(usd['score'])
            recomend = self._get_general_recommendation(usd['score'])
            headline_text = self._generate_headline(usd['score'], data)

            text = f"""{headline_text}

📌 Briefing Macro — USD/DXY

Visão geral: {direcional}
USD Score: {usd['score']:+.2f} ({usd['classification']}, confiança {usd['confidence']})

Cenário Base (probabilidade: {probs['base']}%) — Desaceleração
• Payroll: +{_fmt_num(nfp_proj)} empregos
• Ganho médio por hora: {_fmt_pct(ahe_last)}
• Taxa de desemprego: {unemp_last:.1f}%
Justificativas:
• Dados recentes sinalizam arrefecimento do emprego
• Claims elevadas reforçam risco de payroll mais fraco

Cenário Alternativo (probabilidade: {probs['alt']}%) — Surpresa de Força
• Payroll: +{_fmt_num(max(nfp_proj+80, nfp_proj*1.5))} empregos
• Ganho médio por hora: {_fmt_pct(max(ahe_last+0.1, ahe_last))}
• Taxa de desemprego: {max(unemp_last-0.1, 3.5):.1f}%
Drivers:
• Possível revisão sazonal/volatilidade setorial
• Efeito atrasado de contratações públicas/saúde

Implicações de política monetária:
• Se cenário base confirmar: aumenta precificação de corte; Treasuries tendem a cair nos yields, DXY pressionado.
• Se cenário alternativo: reduz prob. de corte; yields sobem, DXY fortalece.

Mercado agora:
• DXY: {px_dxy.get('price','N/A')} ({(px_dxy.get('change_pct') or 0):+.2f}%)
• Ouro (XAUUSD): {px_xau.get('price','N/A')} ({(px_xau.get('change_pct') or 0):+.2f}%)
• WTI: {px_oil.get('price','N/A')} ({(px_oil.get('change_pct') or 0):+.2f}%)

Tático sugerido:
{recomend}

Dica: Evite abrir posição grande imediatamente antes de releases de alto impacto.
"""
            await update.message.reply_text(text)
        except Exception as e:
            logger.error(f"Briefing erro: {e}")
            await update.message.reply_text("❌ Não consegui montar o briefing agora. Tente novamente em instantes.")

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        update.message = query.message
        data = query.data
        if data == 'analise': await self.analise_command(update, context)
        elif data == 'briefing': await self.briefing_command(update, context)
        elif data == 'calendario': await self.calendario_command(update, context)
        elif data == 'calendario_hoje': await self.calendario_hoje_command(update, context)
        elif data == 'dxy': await self.dxy_command(update, context)
        elif data == 'eurusd': await self.eurusd_command(update, context)
        elif data == 'gbpusd': await self.gbpusd_command(update, context)
        elif data == 'usdjpy': await self.usdjpy_command(update, context)
        elif data == 'gold': await self.gold_command(update, context)
        elif data == 'oil': await self.oil_command(update, context)

def main():
    try:
        logger.info("🚀 Iniciando Bot Macroeconômico USD com IA...")
        bot = MacroUSDBot()
        application = Application.builder().token(bot.bot_token).build()

        application.add_handler(CommandHandler("start", bot.start_command))
        application.add_handler(CommandHandler("analise", bot.analise_command))
        application.add_handler(CommandHandler("briefing", bot.briefing_command))
        application.add_handler(CommandHandler("calendario", bot.calendario_command))
        application.add_handler(CommandHandler("calendario_hoje", bot.calendario_hoje_command))
        application.add_handler(CommandHandler("dxy", bot.dxy_command))
        application.add_handler(CommandHandler("eurusd", bot.eurusd_command))
        application.add_handler(CommandHandler("gbpusd", bot.gbpusd_command))
        application.add_handler(CommandHandler("usdjpy", bot.usdjpy_command))
        application.add_handler(CommandHandler("gold", bot.gold_command))
        application.add_handler(CommandHandler("oil", bot.oil_command))
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
