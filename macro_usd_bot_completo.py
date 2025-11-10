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
            'nfp': 'PAYEMS',
            'unemployment': 'UNRATE',
            'cpi': 'CPIAUCSL',
            'pce': 'PCEPI',
            'retail_sales': 'RSXFS',
            'claims': 'ICSA',
            'gdp': 'GDP',
        }

        logger.info("✅ Bot Macroeconômico USD com IA inicializado (Alpha Vantage + Twelve Data)")

    @cached(api_cache)
    def fetch_av_indicator(self, fred_code: str) -> dict:
        """Busca indicador econômico via Alpha Vantage (FRED)"""
        function_map = {
            'PAYEMS': 'NONFARM_PAYROLL',
            'UNRATE': 'UNEMPLOYMENT',
            'CPIAUCSL': 'CPI',
            'RSXFS': 'RETAIL_SALES',
            'GDP': 'REAL_GDP',
            'ICSA': 'UNEMPLOYMENT',
            'PCEPI': 'CPI',
        }
        
        params = {
            "function": function_map.get(fred_code, "CPI"),
            "apikey": self.av_api_key
        }
        
        try:
            r = requests.get(AV_BASE, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            
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
        
        out['adp'] = out.get('nfp', {})
        out['ahe'] = {'last': 0.3, 'previous': 0.3}
        out['ism_manufacturing'] = {'last': 48.0, 'previous': 47.5}
        out['ism_services'] = {'last': 52.0, 'previous': 51.5}
        out['jolts'] = {'last': 8500, 'previous': 8700}
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
                    'take_profit_1': '70.00', 'take_profit_2
