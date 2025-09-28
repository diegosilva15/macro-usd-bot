#!/usr/bin/env python3
"""
Dynamic Data Engine - Sistema para buscar dados sempre atualizados
Integra múltiplas fontes para manter análises frescas como analistas profissionais
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Tuple
import json
import pytz
import calendar

logger = logging.getLogger(__name__)

class DynamicDataEngine:
    """Engine para buscar dados econômicos sempre atualizados"""
    
    def __init__(self, fred_key: str = None, alpha_vantage_key: str = None):
        self.fred_key = fred_key
        self.alpha_vantage_key = alpha_vantage_key
        self.session = None
        self.ny_tz = pytz.timezone('America/New_York')
        
        # Economic calendar for current week
        self.weekly_calendar = self._generate_weekly_calendar()
        
    async def initialize(self):
        """Inicializa sessão HTTP"""
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        
    async def close(self):
        """Fecha sessão HTTP"""
        if self.session:
            await self.session.close()
    
    def _generate_weekly_calendar(self) -> Dict[str, Any]:
        """Gera calendário econômico da semana atual"""
        now = datetime.now(self.ny_tz)
        
        # Get current week dates
        week_start = now - timedelta(days=now.weekday())
        week_dates = [(week_start + timedelta(days=i)).date() for i in range(7)]
        
        # Define releases for current week (September 2025 context)
        weekly_events = {
            'monday': ['PMI Services Final', 'Construction Spending'],
            'tuesday': ['JOLTs Job Openings', 'Trade Balance'],  
            'wednesday': ['ADP Employment', 'ISM Services PMI'],
            'thursday': ['Initial Jobless Claims', 'Factory Orders'],
            'friday': ['Nonfarm Payrolls', 'Unemployment Rate']
        }
        
        # Special events to watch
        special_events = {
            'government_shutdown_risk': self._check_shutdown_risk(),
            'fomc_meeting': self._check_fomc_this_week(),
            'fed_speakers': self._get_fed_speakers_week()
        }
        
        return {
            'week_dates': week_dates,
            'daily_events': weekly_events,
            'special_events': special_events,
            'generated_at': now
        }
    
    def _check_shutdown_risk(self) -> Dict[str, Any]:
        """Verifica risco de shutdown do governo"""
        # Fiscal year ends Sept 30, so check if we're close
        now = datetime.now(self.ny_tz)
        fiscal_year_end = datetime(now.year, 9, 30, tzinfo=self.ny_tz)
        
        days_to_deadline = (fiscal_year_end - now).days
        
        if days_to_deadline <= 10 and days_to_deadline >= 0:
            return {
                'risk_level': 'HIGH' if days_to_deadline <= 3 else 'MEDIUM',
                'days_remaining': days_to_deadline,
                'impact': 'USD negative if no deal reached',
                'active': True
            }
        
        return {'active': False}
    
    def _check_fomc_this_week(self) -> Dict[str, Any]:
        """Verifica se há FOMC esta semana"""
        # FOMC meetings 2025 (approximate dates)
        fomc_dates_2025 = [
            date(2025, 1, 29),   # Jan 28-29
            date(2025, 3, 19),   # Mar 18-19
            date(2025, 4, 30),   # Apr 29-30
            date(2025, 6, 11),   # Jun 10-11
            date(2025, 7, 30),   # Jul 29-30
            date(2025, 9, 17),   # Sep 16-17
            date(2025, 11, 6),   # Nov 5-6
            date(2025, 12, 17),  # Dec 16-17
        ]
        
        now = datetime.now(self.ny_tz).date()
        week_start = now - timedelta(days=now.weekday())
        week_end = week_start + timedelta(days=6)
        
        for fomc_date in fomc_dates_2025:
            if week_start <= fomc_date <= week_end:
                return {
                    'date': fomc_date,
                    'this_week': True,
                    'impact': 'HIGH - Rate decision + Powell press conference'
                }
        
        return {'this_week': False}
    
    def _get_fed_speakers_week(self) -> List[Dict[str, str]]:
        """Lista speakers do Fed para a semana"""
        # Simplified - in production would use Fed calendar
        return [
            {'speaker': 'Powell', 'day': 'Wednesday', 'event': 'Economic Symposium'},
            {'speaker': 'Williams', 'day': 'Friday', 'event': 'Regional Fed Speech'}
        ]
    
    async def get_latest_economic_data(self) -> Dict[str, Any]:
        """Busca dados econômicos mais recentes"""
        try:
            data = {}
            
            # Get FRED data if available
            if self.fred_key:
                data['fred'] = await self._fetch_fred_latest()
            
            # Get Alpha Vantage data if available
            if self.alpha_vantage_key:
                data['alpha_vantage'] = await self._fetch_alpha_vantage_latest()
            
            # Get market data (DXY, Treasury yields)
            data['market'] = await self._fetch_market_data()
            
            # Add calendar context
            data['calendar'] = self.weekly_calendar
            
            return data
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados econômicos: {e}")
            return {}
    
    async def _fetch_fred_latest(self) -> Dict[str, Any]:
        """Busca dados mais recentes do FRED"""
        try:
            fred_series = {
                'PAYEMS': 'nfp',           # Nonfarm Payrolls
                'UNRATE': 'unemployment',   # Unemployment Rate
                'CPIAUCSL': 'cpi',         # Consumer Price Index
                'CPILFESL': 'core_cpi',    # Core CPI
                'PCE': 'pce',              # Personal Consumption Expenditures
                'PCEPILFE': 'core_pce',    # Core PCE
                'FEDFUNDS': 'fed_funds',   # Federal Funds Rate
                'DGS10': 'treasury_10y'    # 10-Year Treasury
            }
            
            fred_data = {}
            
            for series_id, name in fred_series.items():
                try:
                    url = f"https://api.stlouisfed.org/fred/series/observations"
                    params = {
                        'series_id': series_id,
                        'api_key': self.fred_key,
                        'file_type': 'json',
                        'limit': 5,
                        'sort_order': 'desc'
                    }
                    
                    async with self.session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            observations = data.get('observations', [])
                            
                            if observations:
                                latest = observations[0]
                                if latest['value'] != '.':
                                    fred_data[name] = {
                                        'value': float(latest['value']),
                                        'date': latest['date'],
                                        'series_id': series_id
                                    }
                    
                    # Rate limiting
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.warning(f"Erro ao buscar {series_id}: {e}")
                    continue
            
            return fred_data
            
        except Exception as e:
            logger.error(f"Erro geral FRED: {e}")
            return {}
    
    async def _fetch_alpha_vantage_latest(self) -> Dict[str, Any]:
        """Busca dados do Alpha Vantage"""
        try:
            # Get key economic indicators
            indicators = ['UNEMPLOYMENT', 'RETAIL_SALES', 'GDP']
            av_data = {}
            
            for indicator in indicators[:2]:  # Limit to avoid rate limits
                try:
                    url = "https://www.alphavantage.co/query"
                    params = {
                        'function': indicator,
                        'apikey': self.alpha_vantage_key,
                        'datatype': 'json'
                    }
                    
                    async with self.session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            if 'data' in data and data['data']:
                                latest = data['data'][0]
                                av_data[indicator.lower()] = {
                                    'value': float(latest['value']),
                                    'date': latest['date']
                                }
                    
                    # Rate limiting (5 calls per minute)
                    await asyncio.sleep(12)
                    
                except Exception as e:
                    logger.warning(f"Erro Alpha Vantage {indicator}: {e}")
                    continue
            
            return av_data
            
        except Exception as e:
            logger.error(f"Erro geral Alpha Vantage: {e}")
            return {}
    
    async def _fetch_market_data(self) -> Dict[str, Any]:
        """Busca dados de mercado (DXY, yields) via Yahoo Finance"""
        try:
            symbols = {
                'DX-Y.NYB': 'dxy',
                '^TNX': 'treasury_10y_yield'
            }
            
            market_data = {}
            
            for symbol, name in symbols.items():
                try:
                    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
                    params = {
                        'interval': '1d',
                        'range': '5d'
                    }
                    
                    async with self.session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            result = data.get('chart', {}).get('result', [])
                            
                            if result:
                                meta = result[0].get('meta', {})
                                current_price = meta.get('regularMarketPrice')
                                prev_close = meta.get('previousClose')
                                
                                if current_price and prev_close:
                                    change_pct = ((current_price - prev_close) / prev_close) * 100
                                    
                                    market_data[name] = {
                                        'current': current_price,
                                        'previous': prev_close,
                                        'change_pct': change_pct,
                                        'symbol': symbol
                                    }
                    
                    await asyncio.sleep(1)  # Rate limiting
                    
                except Exception as e:
                    logger.warning(f"Erro Yahoo {symbol}: {e}")
                    continue
            
            return market_data
            
        except Exception as e:
            logger.error(f"Erro market data: {e}")
            return {}
    
    def calculate_dynamic_usd_score(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calcula USD Score baseado em dados dinâmicos atualizados"""
        try:
            score = 0
            confidence = "Baixa"
            components = []
            
            fred_data = data.get('fred', {})
            market_data = data.get('market', {})
            calendar_data = data.get('calendar', {})
            
            # Employment component
            if 'nfp' in fred_data:
                nfp_val = fred_data['nfp']['value']
                if nfp_val > 200:
                    score += 1.2  # Strong employment
                elif nfp_val > 150:
                    score += 0.6  # Moderate employment
                else:
                    score -= 0.6  # Weak employment
                    
                components.append(f"NFP: {nfp_val:.0f}k")
            
            # Unemployment component (inverted)
            if 'unemployment' in fred_data:
                unemp_val = fred_data['unemployment']['value']
                if unemp_val < 4.0:
                    score += 1.0  # Very low unemployment = USD positive
                elif unemp_val < 5.0:
                    score += 0.5
                else:
                    score -= 0.5
                    
                components.append(f"Unemployment: {unemp_val:.1f}%")
            
            # Inflation component
            if 'core_pce' in fred_data:
                pce_val = fred_data['core_pce']['value']
                # Assuming monthly rate, convert to annualized
                if pce_val > 0.3:  # Above 3.6% annualized
                    score += 0.8  # High inflation = hawkish Fed
                elif pce_val > 0.2:  # 2.4-3.6% range
                    score += 0.4
                else:
                    score -= 0.4  # Low inflation = dovish Fed
                    
                components.append(f"Core PCE: {pce_val:.1f}%")
            
            # DXY momentum
            if 'dxy' in market_data:
                dxy_change = market_data['dxy']['change_pct']
                if abs(dxy_change) > 0.5:  # Significant move
                    score += 0.3 if dxy_change > 0 else -0.3
                    
                components.append(f"DXY: {market_data['dxy']['current']:.1f} ({dxy_change:+.1f}%)")
            
            # Calendar events impact
            special_events = calendar_data.get('special_events', {})
            
            # Shutdown risk
            shutdown_risk = special_events.get('government_shutdown_risk', {})
            if shutdown_risk.get('active', False):
                score -= 0.5  # Negative for USD
                components.append(f"Shutdown risk: {shutdown_risk['risk_level']}")
            
            # FOMC impact
            fomc_info = special_events.get('fomc_meeting', {})
            if fomc_info.get('this_week', False):
                score += 0.3  # Anticipation usually supports USD
                components.append("FOMC meeting this week")
            
            # Determine confidence based on data availability
            if len(components) >= 4:
                confidence = "Alta"
            elif len(components) >= 2:
                confidence = "Média"
            
            # Classify score
            if score >= 1.5:
                classification = "USD Forte"
            elif score >= 0.5:
                classification = "Levemente Forte"
            elif score <= -1.5:
                classification = "USD Fraco"
            elif score <= -0.5:
                classification = "Levemente Fraco"
            else:
                classification = "Neutro"
            
            return {
                'score': round(score, 2),
                'classification': classification,
                'confidence': confidence,
                'components': components,
                'data_sources': list(data.keys()),
                'calendar_events': calendar_data.get('daily_events', {}),
                'special_events': special_events
            }
            
        except Exception as e:
            logger.error(f"Erro ao calcular USD Score dinâmico: {e}")
            return {
                'score': 0,
                'classification': 'Neutro',
                'confidence': 'Baixa',
                'components': [],
                'error': str(e)
            }
    
    def format_weekly_outlook(self, analysis: Dict[str, Any]) -> str:
        """Formata outlook semanal como analistas profissionais"""
        try:
            now = datetime.now(self.ny_tz)
            week_start = now - timedelta(days=now.weekday())
            week_end = week_start + timedelta(days=6)
            
            outlook = f"""
📊 **Outlook Semanal USD** — {week_start.strftime('%d/%m')} a {week_end.strftime('%d/%m')}

**🎯 Drivers da Semana:**
"""
            
            # Daily events
            daily_events = analysis.get('calendar_events', {})
            for day, events in daily_events.items():
                if events:
                    outlook += f"• **{day.title()}:** {', '.join(events)}\n"
            
            # Special events
            special_events = analysis.get('special_events', {})
            
            shutdown_risk = special_events.get('government_shutdown_risk', {})
            if shutdown_risk.get('active', False):
                outlook += f"\n⚠️ **Risco Fiscal:** Shutdown em {shutdown_risk['days_remaining']} dias ({shutdown_risk['risk_level']} risk)\n"
            
            fomc_info = special_events.get('fomc_meeting', {})
            if fomc_info.get('this_week', False):
                outlook += f"\n🏛️ **FOMC Meeting:** {fomc_info['date']} - {fomc_info['impact']}\n"
            
            # Score and probabilities
            score = analysis.get('score', 0)
            classification = analysis.get('classification', 'Neutro')
            
            outlook += f"""
**🧮 USD Score Semanal:** {score:+.2f} → **{classification}**

**📈 Cenários Probabilísticos:**
"""
            
            # Generate probabilities based on score
            if score > 1.0:
                bull_prob, neutral_prob, bear_prob = 50, 30, 20
            elif score > 0.3:
                bull_prob, neutral_prob, bear_prob = 40, 35, 25
            elif score < -1.0:
                bull_prob, neutral_prob, bear_prob = 20, 30, 50
            elif score < -0.3:
                bull_prob, neutral_prob, bear_prob = 25, 35, 40
            else:
                bull_prob, neutral_prob, bear_prob = 33, 34, 33
            
            outlook += f"🔵 **Alta ({bull_prob}%):** Payroll forte + Fed hawkish → USD ganha tração\n"
            outlook += f"🟡 **Lateral ({neutral_prob}%):** Dados mistos + Fed dividido → USD oscila\n"
            outlook += f"🔴 **Baixa ({bear_prob}%):** Payroll fraco + risco fiscal → USD perde espaço\n"
            
            return outlook
            
        except Exception as e:
            logger.error(f"Erro ao formatar outlook: {e}")
            return "Erro ao gerar outlook semanal"
