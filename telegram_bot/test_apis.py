#!/usr/bin/env python3
"""
Script de teste para validar APIs antes de executar o bot
Execute: python test_apis.py
"""

import asyncio
import aiohttp
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
ROOT_DIR = Path(__file__).parent  
load_dotenv(ROOT_DIR / '.env')

class APITester:
    """Testa todas as APIs necessárias"""
    
    def __init__(self):
        self.bot_token = os.getenv('BOT_TOKEN')
        self.default_chat_id = os.getenv('DEFAULT_CHAT_ID')
        self.te_api_key = os.getenv('TE_API_KEY')
        self.fred_api_key = os.getenv('FRED_API_KEY')
        
    async def test_all_apis(self):
        """Testa todas as APIs"""
        print("🧪 Testando APIs do Bot Macroeconômico...")
        print("=" * 50)
        
        results = {}
        
        # Test Telegram Bot API
        print("\n📱 Testando Telegram Bot API...")
        results['telegram'] = await self.test_telegram_api()
        
        # Test TradingEconomics API
        print("\n📈 Testando TradingEconomics API...")
        results['trading_economics'] = await self.test_trading_economics_api()
        
        # Test FRED API
        print("\n🏦 Testando FRED API...")
        results['fred'] = await self.test_fred_api()
        
        # Test Yahoo Finance (DXY)
        print("\n💱 Testando Yahoo Finance (DXY)...")
        results['yahoo_finance'] = await self.test_yahoo_finance_api()
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 RESUMO DOS TESTES:")
        print("=" * 50)
        
        for api, status in results.items():
            status_icon = "✅" if status else "❌"
            print(f"{status_icon} {api.replace('_', ' ').title()}: {'OK' if status else 'FALHOU'}")
        
        all_passed = all(results.values())
        
        if all_passed:
            print("\n🎉 Todos os testes passaram! O bot está pronto para execução.")
        else:
            print("\n⚠️  Alguns testes falharam. Verifique as configurações antes de executar o bot.")
        
        return all_passed
    
    async def test_telegram_api(self):
        """Testa API do Telegram"""
        try:
            if not self.bot_token:
                print("❌ BOT_TOKEN não configurado")
                return False
            
            url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('ok'):
                            bot_info = data.get('result', {})
                            print(f"✅ Bot conectado: @{bot_info.get('username')}")
                            
                            # Test sending message if chat_id is provided
                            if self.default_chat_id:
                                await self.test_send_message()
                            
                            return True
                        else:
                            print(f"❌ Resposta da API: {data}")
                            return False
                    else:
                        print(f"❌ Status HTTP: {response.status}")
                        return False
                        
        except Exception as e:
            print(f"❌ Erro na API Telegram: {e}")
            return False
    
    async def test_send_message(self):
        """Testa envio de mensagem"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                'chat_id': self.default_chat_id,
                'text': '🧪 Teste de conectividade do Bot Macroeconômico USD\n\nSe você está vendo esta mensagem, a configuração está correta!'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get('ok'):
                            print(f"✅ Mensagem teste enviada para chat {self.default_chat_id}")
                        else:
                            print(f"❌ Erro ao enviar mensagem: {result}")
                    else:
                        print(f"❌ Erro HTTP ao enviar mensagem: {response.status}")
                        
        except Exception as e:
            print(f"❌ Erro ao testar envio: {e}")
    
    async def test_trading_economics_api(self):
        """Testa API do TradingEconomics"""
        try:
            if not self.te_api_key:
                print("❌ TE_API_KEY não configurado")
                return False
            
            # Test calendar endpoint
            url = "https://api.tradingeconomics.com/calendar"
            params = {
                'c': 'united states',
                'f': 'json',
                'key': self.te_api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if isinstance(data, list) and len(data) > 0:
                            print(f"✅ TradingEconomics OK - {len(data)} eventos no calendário")
                            
                            # Show sample events
                            for event in data[:3]:
                                event_name = event.get('Event', 'N/A')
                                event_date = event.get('Date', 'N/A')
                                print(f"   📅 {event_date}: {event_name}")
                            
                            return True
                        else:
                            print(f"❌ Resposta vazia ou inválida: {data}")
                            return False
                    else:
                        error_text = await response.text()
                        print(f"❌ Status HTTP: {response.status}")
                        print(f"   Resposta: {error_text}")
                        return False
                        
        except Exception as e:
            print(f"❌ Erro na API TradingEconomics: {e}")
            return False
    
    async def test_fred_api(self):
        """Testa API do FRED"""
        try:
            if not self.fred_api_key:
                print("❌ FRED_API_KEY não configurado")
                return False
            
            # Test with PAYEMS (Nonfarm Payrolls)
            url = "https://api.stlouisfed.org/fred/series/observations"
            params = {
                'series_id': 'PAYEMS',
                'api_key': self.fred_api_key,
                'file_type': 'json',
                'limit': 5,
                'sort_order': 'desc'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        observations = data.get('observations', [])
                        
                        if observations:
                            print(f"✅ FRED OK - {len(observations)} observações de PAYEMS")
                            
                            # Show recent data
                            for obs in observations[:2]:
                                date = obs.get('date', 'N/A')
                                value = obs.get('value', 'N/A')
                                print(f"   📊 {date}: {value}")
                            
                            return True
                        else:
                            print(f"❌ Nenhuma observação encontrada: {data}")
                            return False
                    else:
                        error_text = await response.text()
                        print(f"❌ Status HTTP: {response.status}")
                        print(f"   Resposta: {error_text}")
                        return False
                        
        except Exception as e:
            print(f"❌ Erro na API FRED: {e}")
            return False
    
    async def test_yahoo_finance_api(self):
        """Testa API do Yahoo Finance para DXY"""
        try:
            symbol = 'DX-Y.NYB'  # DXY symbol
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            
            params = {
                'interval': '1d',
                'range': '5d'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        result = data.get('chart', {}).get('result', [])
                        
                        if result:
                            meta = result[0].get('meta', {})
                            current_price = meta.get('regularMarketPrice')
                            currency = meta.get('currency', 'USD')
                            
                            print(f"✅ Yahoo Finance OK - DXY: {current_price} {currency}")
                            return True
                        else:
                            print(f"❌ Dados DXY não encontrados: {data}")
                            return False
                    else:
                        print(f"❌ Status HTTP: {response.status}")
                        return False
                        
        except Exception as e:
            print(f"❌ Erro na API Yahoo Finance: {e}")
            return False

async def main():
    """Função principal"""
    tester = APITester()
    success = await tester.test_all_apis()
    
    if success:
        print("\n🚀 Para executar o bot, use:")
        print("   python main.py")
        print("\n🐳 Ou com Docker:")
        print("   docker-compose up -d")
    else:
        print("\n🔧 Configure as chaves no arquivo .env e tente novamente.")
        print("   Veja .env.example para referência.")

if __name__ == "__main__":
    asyncio.run(main())