"""
Configurações do Bot Macroeconômico USD
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

class Config:
    """Configurações centralizadas do bot"""
    
    def __init__(self):
        # Telegram Bot Configuration
        self.bot_token = os.getenv('BOT_TOKEN')
        self.default_chat_id = os.getenv('DEFAULT_CHAT_ID')
        
        # API Keys
        self.te_api_key = os.getenv('TE_API_KEY')  # TradingEconomics
        self.fred_api_key = os.getenv('FRED_API_KEY')  # FRED
        
        # Database Configuration
        self.db_path = os.getenv('DB_PATH', 'macro_bot.db')
        
        # API Endpoints
        self.te_base_url = "https://api.tradingeconomics.com"
        self.fred_base_url = "https://api.stlouisfed.org/fred"
        self.yahoo_finance_base = "https://query1.finance.yahoo.com/v8/finance/chart"
        
        # Request Configuration
        self.request_timeout = int(os.getenv('REQUEST_TIMEOUT', '30'))
        self.max_retries = int(os.getenv('MAX_RETRIES', '3'))
        self.retry_backoff = float(os.getenv('RETRY_BACKOFF', '1.0'))
        
        # Economic Indicators Configuration
        self.indicators_config = self._load_indicators_config()
        
        # Validate required configuration
        self._validate_config()
    
    def _load_indicators_config(self) -> Dict:
        """Carrega configuração dos indicadores econômicos"""
        return {
            # Employment Indicators
            'NFP': {
                'weight': 1.2,
                'te_code': 'UNITEDSTANONNFAR',
                'fred_code': 'PAYEMS',
                'category': 'employment',
                'release_day': 'first_friday',
                'release_time': '08:30',
                'surprise_thresholds': {
                    'strong_negative': -0.30,
                    'negative': -0.10,
                    'neutral_low': -0.10,
                    'neutral_high': 0.10,
                    'positive': 0.10,
                    'strong_positive': 0.30
                }
            },
            'UNEMPLOYMENT': {
                'weight': 1.0,
                'te_code': 'UNITEDSTAUNE',
                'fred_code': 'UNRATE',
                'category': 'employment',
                'release_day': 'first_friday',
                'release_time': '08:30',
                'inversion': True,  # Lower unemployment = USD positive
                'surprise_thresholds': {
                    'strong_negative': 0.20,  # Inverted
                    'negative': 0.10,
                    'neutral_low': -0.09,
                    'neutral_high': 0.09,
                    'positive': -0.10,
                    'strong_positive': -0.20
                }
            },
            'AHE': {
                'weight': 0.6,
                'te_code': 'UNITEDSTAAHEMOM',
                'fred_code': 'AHETPI',
                'category': 'employment',
                'release_day': 'first_friday',
                'release_time': '08:30',
                'surprise_thresholds': {
                    'strong_negative': -0.20,
                    'negative': -0.10,
                    'neutral_low': -0.09,
                    'neutral_high': 0.09,
                    'positive': 0.10,
                    'strong_positive': 0.20
                }
            },
            'ADP': {
                'weight': 0.5,
                'te_code': 'UNITEDSTAADP',
                'category': 'employment',
                'release_day': 'wednesday',
                'release_time': '08:15'
            },
            
            # Inflation Indicators
            'CPI': {
                'weight': 1.0,
                'te_code': 'UNITEDSTACPI',
                'fred_code': 'CPIAUCSL',
                'category': 'inflation',
                'release_day': 'mid_month',
                'release_time': '08:30',
                'surprise_thresholds': {
                    'strong_negative': -0.20,
                    'negative': -0.10,
                    'neutral_low': -0.09,
                    'neutral_high': 0.09,
                    'positive': 0.10,
                    'strong_positive': 0.20
                }
            },
            'CORE_CPI': {
                'weight': 1.2,
                'te_code': 'UNITEDSTACORECPI',
                'fred_code': 'CPILFESL',
                'category': 'inflation',
                'release_day': 'mid_month',
                'release_time': '08:30'
            },
            'PCE': {
                'weight': 0.8,
                'te_code': 'UNITEDSTAPCE',
                'fred_code': 'PCE',
                'category': 'inflation',
                'release_day': 'end_month',
                'release_time': '08:30'
            },
            'CORE_PCE': {
                'weight': 1.2,  # Higher weight as Fed's preferred
                'te_code': 'UNITEDSTACOREPCE',
                'fred_code': 'PCEPILFE',
                'category': 'inflation',
                'release_day': 'end_month',
                'release_time': '08:30'
            },
            
            # Activity Indicators
            'ISM_MFG': {
                'weight': 0.6,
                'te_code': 'UNITEDSTAISM',
                'category': 'activity',
                'release_day': 'first_business_day',
                'release_time': '10:00'
            },
            'ISM_SERVICES': {
                'weight': 0.8,
                'te_code': 'UNITEDSTAISMNMI',
                'category': 'activity',
                'release_day': 'third_business_day',
                'release_time': '10:00'
            },
            'CLAIMS': {
                'weight': 0.3,
                'te_code': 'UNITEDSTACLAIMS',
                'fred_code': 'ICSA',
                'category': 'employment',
                'release_day': 'thursday',
                'release_time': '08:30',
                'inversion': True  # Higher claims = USD negative
            },
            
            # Fed Policy
            'FOMC': {
                'weight': 1.4,
                'category': 'monetary_policy',
                'release_time': '14:00'
            },
            'POWELL_SPEECH': {
                'weight': 1.2,
                'category': 'monetary_policy'
            }
        }
    
    def _validate_config(self):
        """Valida configurações obrigatórias"""
        required_vars = [
            ('BOT_TOKEN', self.bot_token),
            ('DEFAULT_CHAT_ID', self.default_chat_id),
            ('TE_API_KEY', self.te_api_key),
            ('FRED_API_KEY', self.fred_api_key)
        ]
        
        missing_vars = []
        for var_name, var_value in required_vars:
            if not var_value:
                missing_vars.append(var_name)
        
        if missing_vars:
            raise ValueError(f"Variáveis de ambiente obrigatórias não configuradas: {', '.join(missing_vars)}")
    
    def get_indicator_config(self, indicator: str) -> Dict:
        """Retorna configuração de um indicador específico"""
        return self.indicators_config.get(indicator, {})
    
    def get_indicators_by_category(self, category: str) -> List[str]:
        """Retorna lista de indicadores por categoria"""
        return [
            indicator for indicator, config in self.indicators_config.items()
            if config.get('category') == category
        ]
    
    def get_weighted_indicators(self) -> Dict[str, float]:
        """Retorna mapeamento indicador -> peso"""
        return {
            indicator: config.get('weight', 1.0)
            for indicator, config in self.indicators_config.items()
            if 'weight' in config
        }

# Global configuration instance
config = Config()