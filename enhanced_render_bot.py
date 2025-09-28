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
