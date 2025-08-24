"""
Data Ingestor - Sistema de ingestão de dados econômicos
Integra com TradingEconomics e FRED APIs
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
from dataclasses import dataclass
import pytz

from config import Config

logger = logging.getLogger(__name__)

@dataclass
class EconomicDataPoint:
    """Representa um ponto de dados econômicos"""
    indicator: str
    date: datetime
    actual: Optional[float]
    consensus: Optional[float]
    previous: Optional[float]
    surprise_pct: Optional[float]
    source: str
    
    def __post_init__(self):
        # Calculate surprise percentage if not provided
        if self.surprise_pct is None and self.actual is not None and self.consensus is not None:
            if self.consensus != 0:
                self.surprise_pct = ((self.actual - self.consensus) / abs(self.consensus)) * 100
            else:
                self.surprise_pct = 0

class DataIngestor:
    """Sistema de ingestão de dados econômicos"""
    
    def __init__(self, config: Config):
        self.config = config
        self.session = None
        self.last_update = None
        
        # Cache for data
        self._cache = {}
        self._cache_expiry = {}
        
        # NY timezone
        self.ny_tz = pytz.timezone('America/New_York')
    
    async def initialize(self):
        """Inicializa o ingestor de dados"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.request_timeout)
        )
        logger.info("Data Ingestor inicializado")
    
    async def close(self):
        """Fecha sessão HTTP"""
        if self.session:
            await self.session.close()
    
    async def get_indicator_data(self, event_names: List[str]) -> List[EconomicDataPoint]:
        """Busca dados para indicadores específicos"""
        data_points = []
        
        for event_name in event_names:
            try:
                # Try FRED first (more reliable)
                fred_data = await self._fetch_from_fred(event_name)
                if fred_data:
                    data_points.extend(fred_data)
                    continue
                
                # Fallback to TradingEconomics if FRED doesn't have data
                if self.config.te_api_key:
                    te_data = await self._fetch_from_trading_economics(event_name)
                    if te_data:
                        data_points.extend(te_data)
                else:
                    logger.info(f"TradingEconomics API não configurada, usando apenas FRED para {event_name}")
                    
            except Exception as e:
                logger.error(f"Erro ao buscar dados para {event_name}: {e}")
        
        self.last_update = datetime.now(self.ny_tz)
        return data_points
    
    async def get_latest_data(self) -> List[EconomicDataPoint]:
        """Busca dados mais recentes de todos os indicadores principais"""
        main_indicators = [
            'Nonfarm Payrolls',
            'Unemployment Rate', 
            'Consumer Price Index',
            'Core CPI',
            'Personal Consumption Expenditures',
            'Core PCE',
            'ISM Manufacturing PMI',
            'ISM Services PMI',
            'Initial Jobless Claims'
        ]
        
        return await self.get_indicator_data(main_indicators)
    
    async def get_upcoming_releases(self, days: int = 7) -> List[Dict[str, Any]]:
        """Busca próximos releases econômicos"""
        try:
            end_date = datetime.now() + timedelta(days=days)
            
            url = f"{self.config.te_base_url}/calendar"
            params = {
                'c': 'united states',
                'f': 'json',
                'format': 'json'
            }
            
            if self.config.te_api_key:
                params['key'] = self.config.te_api_key
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    releases = []
                    
                    for item in data:
                        release_date = datetime.fromisoformat(item.get('Date', '').replace('T', ' '))
                        if release_date <= end_date:
                            releases.append({
                                'date': release_date.strftime('%Y-%m-%d'),
                                'time': release_date.strftime('%H:%M'),
                                'event': item.get('Event', ''),
                                'importance': item.get('Importance', ''),
                                'country': item.get('Country', ''),
                                'consensus': item.get('Forecast', ''),
                                'previous': item.get('Previous', '')
                            })
                    
                    return sorted(releases, key=lambda x: x['date'])
                else:
                    logger.error(f"Erro na API TradingEconomics: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Erro ao buscar upcoming releases: {e}")
            return []
    
    async def check_fomc_today(self) -> bool:
        """Verifica se há meeting do FOMC hoje"""
        try:
            today = datetime.now(self.ny_tz).date()
            releases = await self.get_upcoming_releases(days=1)
            
            fomc_keywords = ['fomc', 'federal funds rate', 'interest rate decision']
            
            for release in releases:
                event_lower = release['event'].lower()
                release_date = datetime.strptime(release['date'], '%Y-%m-%d').date()
                
                if release_date == today:
                    for keyword in fomc_keywords:
                        if keyword in event_lower:
                            return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erro ao verificar FOMC: {e}")
            return False
    
    async def _fetch_from_trading_economics(self, event_name: str) -> List[EconomicDataPoint]:
        """Busca dados da API TradingEconomics"""
        try:
            # Get historical data
            url = f"{self.config.te_base_url}/historical"
            params = {
                'c': 'united states',
                'i': event_name,
                'f': 'json',
                'format': 'json'
            }
            
            if self.config.te_api_key:
                params['key'] = self.config.te_api_key
            
            # Add retry logic
            for attempt in range(self.config.max_retries):
                try:
                    async with self.session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            return self._parse_te_data(data, event_name)
                        elif response.status == 429:
                            # Rate limited, wait and retry
                            wait_time = self.config.retry_backoff * (2 ** attempt)
                            logger.warning(f"Rate limited, waiting {wait_time}s")
                            await asyncio.sleep(wait_time)
                        else:
                            logger.error(f"TradingEconomics API error: {response.status}")
                            break
                            
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout na tentativa {attempt + 1}")
                    if attempt < self.config.max_retries - 1:
                        await asyncio.sleep(self.config.retry_backoff)
                    
            return []
            
        except Exception as e:
            logger.error(f"Erro na API TradingEconomics para {event_name}: {e}")
            return []
    
    async def _fetch_from_fred(self, event_name: str) -> List[EconomicDataPoint]:
        """Busca dados da API FRED"""
        try:
            # Map event name to FRED series ID
            fred_mapping = {
                'Nonfarm Payrolls': 'PAYEMS',
                'Unemployment Rate': 'UNRATE',
                'Consumer Price Index': 'CPIAUCSL',
                'Core CPI': 'CPILFESL',
                'Personal Consumption Expenditures': 'PCE',
                'Core PCE': 'PCEPILFE',
                'Initial Jobless Claims': 'ICSA'
            }
            
            series_id = fred_mapping.get(event_name)
            if not series_id:
                return []
            
            url = f"{self.config.fred_base_url}/series/observations"
            params = {
                'series_id': series_id,
                'api_key': self.config.fred_api_key,
                'file_type': 'json',
                'limit': 10,
                'sort_order': 'desc'
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_fred_data(data, event_name, series_id)
                else:
                    logger.error(f"FRED API error: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Erro na API FRED para {event_name}: {e}")
            return []
    
    def _parse_te_data(self, data: List[Dict], event_name: str) -> List[EconomicDataPoint]:
        """Parseia dados da TradingEconomics"""
        data_points = []
        
        for item in data[-5:]:  # Last 5 data points
            try:
                date_str = item.get('DateTime')
                if date_str:
                    date = datetime.fromisoformat(date_str.replace('T', ' '))
                else:
                    continue
                
                actual = self._safe_float(item.get('Value'))
                consensus = self._safe_float(item.get('Forecast'))
                previous = self._safe_float(item.get('Previous'))
                
                data_point = EconomicDataPoint(
                    indicator=event_name,
                    date=date,
                    actual=actual,
                    consensus=consensus,
                    previous=previous,
                    surprise_pct=None,  # Will be calculated in __post_init__
                    source='TradingEconomics'
                )
                
                data_points.append(data_point)
                
            except Exception as e:
                logger.warning(f"Erro ao parsear item TE: {e}")
                continue
        
        return data_points
    
    def _parse_fred_data(self, data: Dict, event_name: str, series_id: str) -> List[EconomicDataPoint]:
        """Parseia dados do FRED"""
        data_points = []
        
        observations = data.get('observations', [])
        
        for obs in observations[-3:]:  # Last 3 observations
            try:
                date_str = obs.get('date')
                value_str = obs.get('value')
                
                if not date_str or value_str == '.':
                    continue
                
                date = datetime.strptime(date_str, '%Y-%m-%d')
                actual = float(value_str)
                
                data_point = EconomicDataPoint(
                    indicator=event_name,
                    date=date,
                    actual=actual,
                    consensus=None,  # FRED doesn't provide consensus
                    previous=None,
                    surprise_pct=None,
                    source='FRED'
                )
                
                data_points.append(data_point)
                
            except Exception as e:
                logger.warning(f"Erro ao parsear item FRED: {e}")
                continue
        
        return data_points
    
    async def get_dxy_data(self, period: str = '1d') -> Optional[List[Dict[str, Any]]]:
        """Busca dados do DXY (Dollar Index) do Yahoo Finance"""
        try:
            symbol = 'DX-Y.NYB'  # DXY symbol
            url = f"{self.config.yahoo_finance_base}/{symbol}"
            
            params = {
                'interval': '1m',
                'range': period,
                'includePrePost': 'false'
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    result = data.get('chart', {}).get('result', [])
                    
                    if result:
                        timestamps = result[0].get('timestamp', [])
                        quotes = result[0].get('indicators', {}).get('quote', [{}])[0]
                        
                        closes = quotes.get('close', [])
                        
                        dxy_data = []
                        for i, (timestamp, close) in enumerate(zip(timestamps, closes)):
                            if close is not None:
                                dxy_data.append({
                                    'timestamp': datetime.fromtimestamp(timestamp),
                                    'close': close
                                })
                        
                        return dxy_data
                    
                return None
                
        except Exception as e:
            logger.error(f"Erro ao buscar dados DXY: {e}")
            return None
    
    def _safe_float(self, value) -> Optional[float]:
        """Converte valor para float de forma segura"""
        if value is None or value == '':
            return None
        
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _is_cache_valid(self, key: str) -> bool:
        """Verifica se cache é válido"""
        if key not in self._cache_expiry:
            return False
        
        return datetime.now() < self._cache_expiry[key]
    
    def _set_cache(self, key: str, data: Any, ttl_minutes: int = 15):
        """Define cache com TTL"""
        self._cache[key] = data
        self._cache_expiry[key] = datetime.now() + timedelta(minutes=ttl_minutes)