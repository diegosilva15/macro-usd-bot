"""
Alpha Vantage Data Ingestor - Integração gratuita com dados econômicos
25 calls/dia grátis - dados oficiais do governo americano
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class AlphaVantageDataPoint:
    """Ponto de dados da Alpha Vantage"""
    indicator: str
    date: datetime
    value: float
    unit: str
    source: str = "AlphaVantage"

class AlphaVantageIngestor:
    """Integração com Alpha Vantage API para dados econômicos"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
        self.session = None
        
        # Mapping de indicadores para funções Alpha Vantage
        self.indicator_mapping = {
            'NFP': 'NONFARM_PAYROLL',
            'UNEMPLOYMENT': 'UNEMPLOYMENT',
            'CPI': 'CPI',
            'RETAIL_SALES': 'RETAIL_SALES', 
            'GDP': 'REAL_GDP',
            'FEDERAL_FUNDS_RATE': 'FEDERAL_FUNDS_RATE',
            'CONSUMER_SENTIMENT': 'CONSUMER_SENTIMENT',
            'DURABLE_GOODS': 'DURABLE',
            'INFLATION': 'INFLATION',
            'TREASURY_YIELD': 'TREASURY_YIELD'
        }
    
    async def initialize(self):
        """Inicializa sessão HTTP"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        logger.info("Alpha Vantage Ingestor inicializado")
    
    async def close(self):
        """Fecha sessão HTTP"""
        if self.session:
            await self.session.close()
    
    async def get_economic_indicator(self, indicator: str) -> List[AlphaVantageDataPoint]:
        """Busca indicador econômico específico"""
        try:
            function_name = self.indicator_mapping.get(indicator)
            if not function_name:
                logger.warning(f"Indicador {indicator} não mapeado na Alpha Vantage")
                return []
            
            params = {
                'function': function_name,
                'apikey': self.api_key,
                'datatype': 'json'
            }
            
            # Adiciona intervalo se necessário
            if indicator in ['TREASURY_YIELD']:
                params['interval'] = 'monthly'
                params['maturity'] = '10year'
            
            async with self.session.get(self.base_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_response(data, indicator)
                else:
                    logger.error(f"Alpha Vantage API error: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Erro ao buscar {indicator} na Alpha Vantage: {e}")
            return []
    
    def _parse_response(self, data: Dict, indicator: str) -> List[AlphaVantageDataPoint]:
        """Parse da resposta da Alpha Vantage"""
        try:
            data_points = []
            
            # Alpha Vantage tem estruturas diferentes para cada endpoint
            if 'data' in data:
                # Formato padrão dos indicadores econômicos
                for item in data['data'][:10]:  # Últimos 10 pontos
                    try:
                        date_str = item.get('date')
                        value_str = item.get('value')
                        
                        if date_str and value_str and value_str != '.':
                            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                            value = float(value_str)
                            
                            data_point = AlphaVantageDataPoint(
                                indicator=indicator,
                                date=date_obj,
                                value=value,
                                unit=self._get_unit(indicator)
                            )
                            
                            data_points.append(data_point)
                            
                    except (ValueError, KeyError) as e:
                        logger.warning(f"Erro ao parsear item {item}: {e}")
                        continue
            
            elif 'Annual Time Series' in data:
                # GDP e outros anuais
                time_series = data['Annual Time Series']
                for date_str, values in list(time_series.items())[:5]:
                    try:
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                        value = float(values['value'])
                        
                        data_point = AlphaVantageDataPoint(
                            indicator=indicator,
                            date=date_obj,
                            value=value,
                            unit=self._get_unit(indicator)
                        )
                        
                        data_points.append(data_point)
                        
                    except (ValueError, KeyError) as e:
                        continue
            
            logger.info(f"Alpha Vantage: {len(data_points)} pontos obtidos para {indicator}")
            return sorted(data_points, key=lambda x: x.date, reverse=True)
            
        except Exception as e:
            logger.error(f"Erro no parse da resposta Alpha Vantage: {e}")
            return []
    
    def _get_unit(self, indicator: str) -> str:
        """Retorna unidade do indicador"""
        units = {
            'NFP': 'thousands',
            'UNEMPLOYMENT': 'percent',
            'CPI': 'index',
            'RETAIL_SALES': 'millions_usd',
            'GDP': 'billions_usd',
            'FEDERAL_FUNDS_RATE': 'percent',
            'CONSUMER_SENTIMENT': 'index',
            'DURABLE_GOODS': 'millions_usd',
            'INFLATION': 'percent',
            'TREASURY_YIELD': 'percent'
        }
        return units.get(indicator, 'units')
    
    async def get_multiple_indicators(self, indicators: List[str]) -> Dict[str, List[AlphaVantageDataPoint]]:
        """Busca múltiplos indicadores"""
        results = {}
        
        for indicator in indicators:
            try:
                data = await self.get_economic_indicator(indicator)
                results[indicator] = data
                
                # Rate limiting - Alpha Vantage permite 5 calls/minuto
                await asyncio.sleep(12)  # 12 seconds between calls
                
            except Exception as e:
                logger.error(f"Erro ao buscar {indicator}: {e}")
                results[indicator] = []
        
        return results
    
    async def test_api_connection(self) -> bool:
        """Testa conexão com Alpha Vantage"""
        try:
            # Testa com GDP (simples e confiável)
            params = {
                'function': 'REAL_GDP',
                'apikey': self.api_key,
                'datatype': 'json'
            }
            
            async with self.session.get(self.base_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Verifica se não há erro de API key
                    if 'Error Message' in data:
                        logger.error(f"Alpha Vantage API Error: {data['Error Message']}")
                        return False
                    
                    if 'Note' in data:
                        logger.warning(f"Alpha Vantage Rate Limit: {data['Note']}")
                        return False
                    
                    if 'data' in data or 'Annual Time Series' in data:
                        logger.info("✅ Alpha Vantage API conectada com sucesso!")
                        return True
                    
                    return False
                else:
                    logger.error(f"HTTP Error: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Erro ao testar Alpha Vantage: {e}")
            return False
    
    async def get_latest_economic_summary(self) -> Dict[str, Any]:
        """Busca resumo dos últimos dados econômicos"""
        try:
            # Indicadores principais para resumo
            key_indicators = ['NFP', 'UNEMPLOYMENT', 'CPI', 'GDP']
            
            results = {}
            for indicator in key_indicators:
                data = await self.get_economic_indicator(indicator)
                if data:
                    latest = data[0]  # Mais recente
                    results[indicator] = {
                        'value': latest.value,
                        'date': latest.date.strftime('%Y-%m-%d'),
                        'unit': latest.unit
                    }
                
                # Rate limiting
                await asyncio.sleep(12)
            
            return results
            
        except Exception as e:
            logger.error(f"Erro ao buscar resumo econômico: {e}")
            return {}