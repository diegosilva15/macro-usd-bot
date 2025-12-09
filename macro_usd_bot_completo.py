import os
import logging
import requests
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

# --- Configurações ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
JB_NEWS_API_KEY = os.getenv("JB_NEWS_API_KEY") # Nova chave da JB-News

# Configuração de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Cliente JB-News API ---
class JBNewsClient:
    BASE_URL = "https://jblanked.com/api" # Exemplo, verifique a URL correta na documentação deles

    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Api-Key {self.api_key}"
        }

    def _make_request(self, endpoint, params=None):
        url = f"{self.BASE_URL}/{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status() # Levanta um erro para status de resposta HTTP ruins (4xx ou 5xx)
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao chamar JB-News API {endpoint}: {e}")
            return None

    def get_calendar_events(self, start_date=None, end_date=None):
        """Busca eventos do calendário."""
        params = {}
        if start_date:
            params['start_date'] = start_date.strftime('%Y-%m-%d')
        if end_date:
            params['end_date'] = end_date.strftime('%Y-%m-%d')
        return self._make_request("calendar", params) # Verifique o endpoint correto para calendário

    def get_news_sentiment(self, symbol="USD"):
        """Busca sentimento de notícias para um símbolo."""
        params = {'symbol': symbol}
        return self._make_request("sentiment", params) # Verifique o endpoint correto para sentimento

# --- Funções de API de Dados (Twelve Data, Alpha Vantage) ---
class DataAPIClient:
    def __init__(self, twelve_data_key, alpha_vantage_key):
        self.twelve_data_key = twelve_data_key
        self.alpha_vantage_key = alpha_vantage_key
        self.symbols_macro = {
            "DXY": ["DX", "EUR/USD", "USD/JPY", "GBP/USD", "USD/CAD", "USD/CHF", "USD/SEK", "USD/NOK"], # DX para futuro, e pares para cálculo
            "GOLD": ["XAU/USD"],
            "WTI": ["WTI"],
            "SPX": ["SPX"],
            "NDX": ["NDX"],
            "VIX": ["VIX"]
        }

    def get_twelve_data_quote(self, symbol):
        url = f"https://api.twelvedata.com/quote?symbol={symbol}&apikey={self.twelve_data_key}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            if data and data.get('status') == 'ok':
                return data
            logger.warning(f"Twelve Data quote para {symbol} falhou ou status não é 'ok': {data}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao buscar Twelve Data quote para {symbol}: {e}")
            return None

    def get_dxy_price(self):
        # 1. Tenta pegar DX (futuro) da Twelve Data
        dxy_data = self.get_twelve_data_quote("DX")
        if dxy_data and dxy_data.get('close'):
            logger.info("DXY obtido via DX (futuro) da Twelve Data.")
            return float(dxy_data['close']), float(dxy_data['change_percent'])

        logger.warning("Falha ao obter DXY via DX. Tentando cálculo aproximado.")

        # 2. Fallback: Cálculo aproximado do DXY usando pares de moedas
        # Pesos aproximados do DXY oficial
        weights = {
            "EUR/USD": 0.576,
            "USD/JPY": 0.136,
            "GBP/USD": 0.119,
            "USD/CAD": 0.091,
            "USD/CHF": 0.042,
            "USD/SEK": 0.042,
            # USD/NOK e outros são menores, podemos simplificar para os principais
        }
        
        # Valores base (inversos para USD/XXX)
        base_values = {
            "EUR/USD": 1.2000, # Exemplo de valor base, pode ser ajustado
            "USD/JPY": 100.00,
            "GBP/USD": 1.3000,
            "USD/CAD": 1.2500,
            "USD/CHF": 0.9000,
            "USD/SEK": 8.5000,
        }

        current_dxy_sum = 0
        previous_dxy_sum = 0
        
        for pair, weight in weights.items():
            data = self.get_twelve_data_quote(pair)
            if data and data.get('close') and data.get('open'):
                current_price = float(data['close'])
                open_price = float(data['open'])

                # DXY é um índice do USD contra outras moedas.
                # Para EUR/USD, GBP/USD, etc., o USD está no denominador, então usamos 1/price
                # Para USD/JPY, USD/CAD, etc., o USD está no numerador, então usamos price
                if pair in ["EUR/USD", "GBP/USD", "AUD/USD", "NZD/USD"]: # Adicione outros se necessário
                    current_dxy_sum += weight * (1 / current_price)
                    previous_dxy_sum += weight * (1 / open_price)
                else:
                    current_dxy_sum += weight * current_price
                    previous_dxy_sum += weight * open_price
            else:
                logger.warning(f"Não foi possível obter dados para o par {pair} para cálculo do DXY.")
                # Se um par essencial falhar, o cálculo pode ser impreciso.
                # Poderíamos retornar None aqui ou continuar com os pares disponíveis.
                # Por simplicidade, vamos continuar e aceitar a imprecisão se faltar um par.

        if current_dxy_sum > 0 and previous_dxy_sum > 0:
            # A fórmula exata do DXY é complexa, mas essa é uma aproximação para variação
            # O valor base do DXY é 100.00 em 1973.
            # Podemos normalizar a soma para um valor próximo do DXY real.
            # Isso é uma simplificação, o DXY real tem uma base e uma potência.
            # Para fins de variação percentual, a proporção é mais importante.
            
            # Uma forma simples de normalizar para um valor próximo do DXY real:
            # Encontramos um fator de ajuste que leve a soma para a faixa do DXY (ex: 100)
            # Isso é um chute, o ideal seria calibrar com dados históricos.
            adjustment_factor = 100 / (sum(weights.values()) * (1/base_values["EUR/USD"] + base_values["USD/JPY"] + ...)) # Isso é complexo de calibrar sem dados
            
            # Para simplificar e focar na variação:
            # Vamos usar a soma direta e calcular a variação percentual.
            # O valor absoluto pode não ser exato, mas a variação será mais precisa.
            
            # Uma aproximação mais robusta seria:
            # DXY = 50.14348112 * EURUSD^(-0.576) * USDJPY^(0.136) * GBPUSD^(-0.119) * USDCAD^(0.091) * USDCHF^(0.042) * USDSEK^(0.042)
            # Mas isso requer os valores base e a potência, que não temos facilmente.
            
            # Para o propósito do bot, vamos usar uma soma ponderada e uma normalização simples
            # para que o valor fique na faixa de 90-110.
            # Isso é uma heurística, não a fórmula oficial.
            
            # Vamos usar uma abordagem mais simples para o cálculo aproximado:
            # Apenas a variação percentual é mais fácil de obter de forma confiável.
            # Se o DX falhou, vamos retornar None para o valor e tentar apenas a variação.
            
            # Para ter um valor aproximado, podemos usar uma média ponderada e ajustar.
            # Isso é um placeholder, o ideal seria uma API de DXY spot.
            
            # Se não conseguimos o DX, e o cálculo é muito complexo para ser preciso,
            # vamos retornar None para o valor e tentar apenas a variação se possível.
            
            # Para simplificar, se DX falhou, vamos retornar None para o valor e 0 para a variação
            # ou tentar uma fonte alternativa para DXY spot se tivermos uma.
            
            # Por enquanto, se DX falhou, vamos retornar None para o valor e 0 para a variação
            # para evitar valores muito imprecisos.
            logger.warning("Cálculo aproximado do DXY é complexo e pode ser impreciso sem a fórmula exata. Retornando None.")
            return None, 0.0 # Retorna None para o valor se o cálculo for muito incerto
        
        return None, 0.0 # Se nada funcionou

    def get_alpha_vantage_quote(self, symbol):
        # Alpha Vantage é mais para dados históricos e fundamentalistas, não tanto para cotações em tempo real
        # Mas podemos usar para um fallback se Twelve Data falhar para alguns ativos
        # Exemplo: url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={self.alpha_vantage_key}"
        return None # Por enquanto, focamos em Twelve Data para cotações

# --- Funções Auxiliares ---
def format_price_change(price, change_percent):
    if price is None:
        return "N/D"
    
    sign = "+" if change_percent >= 0 else ""
    return f"{price:,.2f} ({sign}{change_percent:,.2f}%)"

# --- Comandos do Bot ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        'Olá! Eu sou o Bot Macroeconômico USD. Use /macro para um resumo ou /calendario para eventos.'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        'Comandos disponíveis:\n'
        '/start - Inicia o bot\n'
        '/help - Mostra esta mensagem de ajuda\n'
        '/macro - Gera um briefing macroeconômico do USD\n'
        '/calendario - Mostra os eventos econômicos importantes\n'
        '/dxy - Cotação do DXY\n'
        '/gold - Cotação do Ouro\n'
        '/wti - Cotação do Petróleo WTI\n'
        '/spx - Cotação do S&P 500\n'
        '/ndx - Cotação do Nasdaq 100\n'
        '/vix - Cotação do VIX'
    )

async def calendario(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    jb_news_client = JBNewsClient(JB_NEWS_API_KEY)
    today = datetime.now()
    events = jb_news_client.get_calendar_events(start_date=today, end_date=today)

    if events and events.get('data'): # Assumindo que a resposta tem uma chave 'data' com a lista de eventos
        message = "🗓️ **Eventos Econômicos de Hoje:**\n\n"
        for event in events['data']:
            # Adapte conforme a estrutura real do JSON da JB-News
            event_time = event.get('time', 'N/D')
            event_name = event.get('event_name', 'N/D')
            country = event.get('country', 'N/D')
            impact = event.get('impact', 'N/D')
            forecast = event.get('forecast', 'N/D')
            previous = event.get('previous', 'N/D')

            message += f"⏰ {event_time} ({country}) - **{event_name}**\n"
            message += f"  Impacto: {impact} | Consenso: {forecast} | Anterior: {previous}\n\n"
        await update.message.reply_text(message, parse_mode='Markdown')
    else:
        await update.message.reply_text("Não foi possível obter os eventos do calendário hoje. Tente novamente mais tarde.")

async def macro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Gerando briefing macroeconômico... 📊")

    data_client = DataAPIClient(TWELVE_DATA_API_KEY, ALPHA_VANTAGE_API_KEY)
    jb_news_client = JBNewsClient(JB_NEWS_API_KEY)

    # --- 1. Cotações de Ativos ---
    dxy_price, dxy_change = data_client.get_dxy_price()
    gold_data = data_client.get_twelve_data_quote("XAU/USD")
    wti_data = data_client.get_twelve_data_quote("WTI")
    spx_data = data_client.get_twelve_data_quote("SPX")

    dxy_str = format_price_change(dxy_price, dxy_change)
    gold_str = format_price_change(float(gold_data['close']), float(gold_data['change_percent'])) if gold_data else "N/D"
    wti_str = format_price_change(float(wti_data['close']), float(wti_data['change_percent'])) if wti_data else "N/D"
    spx_str = format_price_change(float(spx_data['close']), float(spx_data['change_percent'])) if spx_data else "N/D"

    briefing = "✨ **Briefing Macroeconômico USD** ✨\n\n"
    briefing += "📈 **Cotações Atuais:**\n"
    briefing += f"  DXY: {dxy_str}\n"
    briefing += f"  Ouro (XAU/USD): {gold_str}\n"
    briefing += f"  Petróleo (WTI): {wti_str}\n"
    briefing += f"  S&P 500 (SPX): {spx_str}\n\n"

    # --- 2. Eventos do Calendário (JB-News) ---
    today = datetime.now()
    events = jb_news_client.get_calendar_events(start_date=today, end_date=today)
    
    briefing += "🗓️ **Eventos Chave de Hoje (USD):**\n"
    if events and events.get('data'):
        usd_events = [e for e in events['data'] if e.get('country') == 'US'] # Filtrar por eventos dos EUA
        if usd_events:
            for event in usd_events:
                event_time = event.get('time', 'N/D')
                event_name = event.get('event_name', 'N/D')
                impact = event.get('impact', 'N/D')
                forecast = event.get('forecast', 'N/D')
                previous = event.get('previous', 'N/D')
                briefing += f"  ⏰ {event_time} - **{event_name}** (Impacto: {impact})\n"
                briefing += f"    Consenso: {forecast} | Anterior: {previous}\n"
        else:
            briefing += "  Nenhum evento significativo dos EUA agendado para hoje.\n"
    else:
        briefing += "  Não foi possível obter eventos do calendário.\n"
    briefing += "\n"

    # --- 3. Sentimento de Notícias (JB-News) ---
    sentiment_data = jb_news_client.get_news_sentiment(symbol="USD")
    briefing += "📰 **Sentimento de Notícias (USD):**\n"
    if sentiment_data and sentiment_data.get('sentiment'): # Adapte conforme a resposta da API
        sentiment = sentiment_data['sentiment'] # Ex: 'positive', 'negative', 'neutral'
        score = sentiment_data.get('score', 'N/D') # Ex: 0.75
        briefing += f"  O sentimento geral das notícias para o USD é **{sentiment.upper()}** (Score: {score}).\n"
        briefing += f"  Principais drivers: {sentiment_data.get('drivers', 'N/D')}.\n" # Ex: 'inflação, Fed, payroll'
    else:
        briefing += "  Não foi possível obter o sentimento das notícias para o USD.\n"
    briefing += "\n"

    # --- 4. Análise e Cenário (Exemplo - pode ser expandido com mais lógica) ---
    briefing += "💡 **Análise e Cenário:**\n"
    
    # Lógica para determinar o viés do DXY com base em dados e sentimento
    dxy_bias = "neutro"
    if dxy_change is not None:
        if dxy_change > 0.2: # Exemplo: subida significativa
            dxy_bias = "altista"
        elif dxy_change < -0.2: # Exemplo: queda significativa
            dxy_bias = "baixista"

    if sentiment_data and sentiment_data.get('sentiment') == 'positive':
        dxy_bias = "altista" # Sentimento positivo reforça alta
    elif sentiment_data and sentiment_data.get('sentiment') == 'negative':
        dxy_bias = "baixista" # Sentimento negativo reforça baixa

    briefing += f"  O DXY apresenta um viés **{dxy_bias}** no momento.\n"
    briefing += "  Atenção aos próximos dados de inflação e discursos de membros do FOMC.\n"
    briefing += "  *Recomendação:* Manter cautela e observar a reação do mercado aos dados.\n\n"

    briefing += "--- Fim do Briefing ---"
    await update.message.reply_text(briefing, parse_mode='Markdown')

# --- Comandos de Cotação Individual ---
async def get_quote(update: Update, context: ContextTypes.DEFAULT_TYPE, symbol_key: str) -> None:
    data_client = DataAPIClient(TWELVE_DATA_API_KEY, ALPHA_VANTAGE_API_KEY)
    
    if symbol_key == "DXY":
        price, change_percent = data_client.get_dxy_price()
        if price is not None:
            message = f"📊 **DXY (Índice Dólar):**\n"
            message += f"  Último: {format_price_change(price, change_percent)}\n"
            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            await update.message.reply_text("Não foi possível obter a cotação do DXY no momento.")
        return

    symbols = data_client.symbols_macro.get(symbol_key)
    if not symbols:
        await update.message.reply_text(f"Símbolo {symbol_key} não configurado.")
        return

    data = None
    for symbol in symbols:
        data = data_client.get_twelve_data_quote(symbol)
        if data:
            break
    
    if data and data.get('close'):
        price = float(data['close'])
        change_percent = float(data['change_percent'])
        message = f"📊 **{symbol_key}:**\n"
        message += f"  Último: {format_price_change(price, change_percent)}\n"
        await update.message.reply_text(message, parse_mode='Markdown')
    else:
        await update.message.reply_text(f"Não foi possível obter a cotação para {symbol_key} no momento.")

async def dxy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await get_quote(update, context, "DXY")

async def gold_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await get_quote(update, context, "GOLD")

async def wti_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await get_quote(update, context, "WTI")

async def spx_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await get_quote(update, context, "SPX")

async def ndx_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await get_quote(update, context, "NDX")

async def vix_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await get_quote(update, context, "VIX")

# --- Main ---
def main() -> None:
    application = Application.builder().token(TOKEN).build()

    # Comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("macro", macro))
    application.add_handler(CommandHandler("calendario", calendario))
    application.add_handler(CommandHandler("dxy", dxy_command))
    application.add_handler(CommandHandler("gold", gold_command))
    application.add_handler(CommandHandler("wti", wti_command))
    application.add_handler(CommandHandler("spx", spx_command))
    application.add_handler(CommandHandler("ndx", ndx_command))
    application.add_handler(CommandHandler("vix", vix_command))

    # Iniciar o bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN não configurado. Por favor, defina a variável de ambiente.")
    if not TWELVE_DATA_API_KEY:
        logger.error("TWELVE_DATA_API_KEY não configurado. Por favor, defina a variável de ambiente.")
    if not JB_NEWS_API_KEY:
        logger.error("JB_NEWS_API_KEY não configurado. Por favor, defina a variável de ambiente.")
    
    if TOKEN and TWELVE_DATA_API_KEY and JB_NEWS_API_KEY:
        main()
    else:
        logger.error("Uma ou mais chaves de API estão faltando. O bot não será iniciado.")
