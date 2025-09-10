#!/bin/bash

# Script robusto para iniciar o bot e garantir que rode 24/7
# Uso: ./start_bot_robust.sh

echo "🚀 Iniciando Bot Macroeconômico USD - Modo Robusto"
echo "=================================================="

cd /app/telegram_bot

# Kill processos antigos
echo "🧹 Limpando processos antigos..."
pkill -f "enhanced_bot.py" 2>/dev/null || true
pkill -f "simple_bot.py" 2>/dev/null || true
sleep 3

# Verifica dependências
echo "🔍 Verificando dependências..."
python3 -c "import telegram, aiohttp, pytz; print('✅ Dependências OK')" || {
    echo "❌ Erro nas dependências!"
    exit 1
}

# Verifica arquivo .env
echo "🔑 Verificando configurações..."
if [ ! -f ".env" ]; then
    echo "❌ Arquivo .env não encontrado!"
    exit 1
fi

source .env
if [ -z "$BOT_TOKEN" ] || [ -z "$FRED_API_KEY" ] || [ -z "$ALPHA_VANTAGE_API_KEY" ]; then
    echo "❌ Variáveis de ambiente obrigatórias não configuradas!"
    exit 1
fi

echo "✅ Configurações OK"

# Testa APIs rapidamente
echo "🧪 Testando APIs..."
python3 -c "
import asyncio
import aiohttp
import os
from dotenv import load_dotenv

async def test_apis():
    load_dotenv()
    
    # Test Telegram
    bot_token = os.getenv('BOT_TOKEN')
    url = f'https://api.telegram.org/bot{bot_token}/getMe'
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                print('✅ Telegram OK')
            else:
                print('❌ Telegram Erro')
                return False
    
    # Test Alpha Vantage  
    av_key = os.getenv('ALPHA_VANTAGE_API_KEY')
    av_url = f'https://www.alphavantage.co/query?function=REAL_GDP&apikey={av_key}'
    
    async with aiohttp.ClientSession() as session:
        async with session.get(av_url) as resp:
            if resp.status == 200:
                print('✅ Alpha Vantage OK')
            else:
                print('❌ Alpha Vantage Erro')
    
    return True

asyncio.run(test_apis())
" || {
    echo "⚠️ Alguns testes falharam, mas continuando..."
}

# Backup dos logs antigos
echo "📋 Fazendo backup dos logs..."
if [ -f "bot_enhanced.log" ]; then
    mv bot_enhanced.log "bot_enhanced.log.$(date +%Y%m%d_%H%M%S)"
fi

# Inicia o bot
echo "🚀 Iniciando bot enhanced..."
echo "Logs em: $(pwd)/bot_enhanced.log"
echo "KeepAlive em: $(pwd)/keepalive.log"

# Inicia com nohup e redireciona logs
nohup python3 enhanced_bot.py > bot_enhanced.log 2>&1 &
BOT_PID=$!

# Aguarda inicialização
echo "⏳ Aguardando inicialização (10s)..."
sleep 10

# Verifica se iniciou
if ps -p $BOT_PID > /dev/null; then
    echo "✅ Bot iniciado com sucesso! PID: $BOT_PID"
    
    # Teste básico
    tail -5 bot_enhanced.log | grep -q "Application started" && {
        echo "✅ Bot conectou ao Telegram!"
    } || {
        echo "⚠️ Bot pode não ter conectado - verifique logs"
    }
else
    echo "❌ Bot falhou ao iniciar!"
    echo "📋 Últimas linhas do log:"
    tail -10 bot_enhanced.log
    exit 1
fi

# Configura cron para KeepAlive (a cada 5 minutos)
echo "⚙️ Configurando monitoramento automático..."

# Adiciona ao crontab se não existe
CRON_JOB="*/5 * * * * /usr/bin/python3 /app/telegram_bot/keepalive.py"
(crontab -l 2>/dev/null | grep -F "$CRON_JOB") || {
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "✅ KeepAlive configurado (executa a cada 5 min)"
}

# Status final
echo "=================================================="
echo "🎉 BOT CONFIGURADO PARA RODAR 24/7!"
echo "📊 Status:"
echo "  • Bot PID: $BOT_PID"
echo "  • Logs: bot_enhanced.log"
echo "  • KeepAlive: a cada 5 minutos"
echo "  • Reinício automático: ✅ Ativo"
echo ""
echo "📱 Teste no Telegram: /start"
echo "📋 Ver logs: tail -f bot_enhanced.log"
echo "🔍 Ver KeepAlive: tail -f keepalive.log"
echo "=================================================="