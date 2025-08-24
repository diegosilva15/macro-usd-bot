# 🧭 Bot Macroeconômico USD

Bot automático no Telegram que monitora indicadores macroeconômicos dos EUA para prever o direcional do dólar (USD forte/fraco/neutro). Fornece USD Score, cenários base/alternativo, confiança e sugestões de pares de moedas.

## ✨ Características Principais

- **📊 Análise Automática**: Monitora NFP, CPI, PCE, ISM, Unemployment e outros indicadores
- **🎯 USD Score Preciso**: Sistema de scoring ponderado (-2 a +2) com regras determinísticas  
- **⏰ Agendamento Inteligente**: Cron jobs em timezone NY para releases em tempo real
- **📈 Hit-Rate Tracking**: SQLite para auditoria de performance com janelas de 30/60/120 min
- **🔄 Sistema de Retry**: Backoff exponencial com jitter para APIs
- **🚀 Deploy Pronto**: Docker + docker-compose para produção

## 🏗️ Arquitetura

```
├── main.py              # Bot principal + handlers Telegram
├── config.py            # Configurações centralizadas  
├── data_ingestor.py     # APIs TradingEconomics + FRED
├── scoring_engine.py    # Regras determinísticas + USD Score
├── hit_rate_tracker.py  # SQLite tracking + métricas
├── scheduler.py         # Agendamento inteligente NY timezone
├── requirements.txt     # Dependências Python
├── Dockerfile          # Container para deploy
└── .env.example        # Template de configuração
```

## 🔧 Configuração Rápida

### 1. Clone e Configure

```bash
# Navegue para o diretório do bot
cd /app/telegram_bot

# Copie e configure o arquivo de ambiente
cp .env.example .env
# Edite .env com suas chaves (veja seção abaixo)
```

### 2. Obtenha as Chaves de API

#### 🤖 Telegram Bot Token
```bash
# 1. Abra Telegram e procure @BotFather
# 2. Digite /newbot e siga instruções
# 3. Copie o token: 1234567890:ABCdefGHI...
```

#### 📱 Chat ID do Telegram  
```bash
# 1. Crie grupo ou use chat privado
# 2. Adicione @userinfobot ao grupo
# 3. Digite /start - bot mostra Chat ID: -1001234567890
```

#### 📈 TradingEconomics API
```bash
# 1. Visite: https://tradingeconomics.com/api
# 2. Registre-se (gratuito)
# 3. Copie API Key da sua conta
```

#### 🏦 FRED API (Federal Reserve)
```bash
# 1. Visite: https://fred.stlouisfed.org/docs/api/
# 2. Clique "Request API Key"
# 3. Confirme por email e copie a chave
```

### 3. Configure o .env

```env
# Exemplo de .env configurado
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz1234567890
DEFAULT_CHAT_ID=-1001234567890
TE_API_KEY=your_te_api_key_here
FRED_API_KEY=abcd1234efgh5678ijkl9012mnop3456
```

## 🚀 Execução

### Modo Desenvolvimento
```bash
# Instalar dependências
pip install -r requirements.txt

# Executar bot
python main.py
```

### Modo Produção (Docker)
```bash
# Build e start
docker-compose up -d

# Ver logs
docker-compose logs -f

# Parar
docker-compose down
```

## 📊 Indicadores Monitorados

### 💼 Emprego (Employment)
- **NFP** (Nonfarm Payrolls) - Peso 1.2 - Primeira sexta 08:30 NY
- **Unemployment Rate** - Peso 1.0 - Primeira sexta 08:30 NY
- **AHE** (Average Hourly Earnings) - Peso 0.6 - Primeira sexta 08:30 NY
- **ADP Employment** - Peso 0.5 - Quarta 08:15 NY
- **Initial Claims** - Peso 0.3 - Quinta 08:30 NY

### 💰 Inflação (Inflation)  
- **CPI / Core CPI** - Peso 1.0/1.2 - Meio do mês 08:30 NY
- **PCE / Core PCE** - Peso 0.8/1.2 - Final do mês 08:30 NY

### 🏭 Atividade (Activity)
- **ISM Manufacturing** - Peso 0.6 - Dia 1 do mês 10:00 NY  
- **ISM Services** - Peso 0.8 - Dia 3+ do mês 10:00 NY

### 🏛️ Política Monetária
- **FOMC Rate Decision** - Peso 1.4 - 14:00 NY (datas específicas)
- **Powell Speech** - Peso 1.2 - Variável

## 🧮 Sistema de Scoring

### Cálculo do USD Score
```python
# Componente Score: -2 a +2 para cada indicador
# USD Score = Σ(score_i × weight_i) / Σ(weight_i)

# Classificação:
# ≥ +1.5  → USD Forte
# +0.5 a +1.49 → Levemente Forte  
# -0.49 a +0.49 → Neutro
# -1.49 a -0.5 → Levemente Fraco
# ≤ -1.5 → USD Fraco
```

### Regras de Interpretação

#### Inflação (CPI/PCE)
```python
delta_pp = actual - consensus  # percentage points
if delta_pp <= -0.20: score = -2
elif delta_pp <= -0.10: score = -1  
elif -0.09 <= delta_pp <= 0.09: score = 0
elif delta_pp <= 0.19: score = +1
else: score = +2
```

#### Emprego (NFP/ADP)
```python  
surprise_pct = (actual - consensus) / |consensus| * 100
if surprise_pct <= -30: score = -2
elif surprise_pct <= -10: score = -1
elif -10 <= surprise_pct <= 10: score = 0  
elif surprise_pct <= 30: score = +1
else: score = +2
```

## 📱 Comandos do Bot

- `/start` - Apresentação e comandos disponíveis
- `/status` - Status do bot + próximos releases  
- `/score` - Análise manual do USD score atual
- `/hitrate` - Performance histórica do bot

## 📈 Exemplo de Mensagem

```
🧭 Leitura Macro USD — 06/12/2024 08:35 (NY)

• NFP: 227k vs 200k → surpresa +14% | comp +1.0 (w=1.2)
• Unemp: 4.2% vs 4.1% → Δ +0.1pp | comp -1.0 (w=1.0)  
• AHE MoM: 0.4% vs 0.3% → Δ +0.1pp | comp +1.0 (w=0.6)
• CPI MoM: 0.2% vs 0.3% → Δ -0.1pp | comp -1.0 (w=1.0)

🧮 USD Score: +0.73 → Levemente Forte (Confiança: Média)

📌 Cenário base (70%): Emprego forte supera inflação baixa, Fed mantém hawkishness
📌 Alternativo (30%): CPI baixo pode acelerar cortes, emprego pode ser revisado

🎯 Direcional: Viés de venda EUR/USD, aguardar confirmação
👀 Pares/mercados: EUR/USD, GBP/USD, USD/JPY
```

## 📊 Hit-Rate & Métricas

### Critérios de Acerto
- **Score > +0.5** e **DXY > 0** → ✅ Hit
- **Score < -0.5** e **DXY < 0** → ✅ Hit  
- **|Score| ≤ 0.5** → ✅ Neutro (sempre hit)

### Janelas Temporais
- **30 minutos** - Reação imediata
- **60 minutos** - Absorção inicial  
- **120 minutos** - Tendência confirmada

### Métricas Disponíveis
- Hit-rate por janela temporal
- Performance por indicador
- Estatísticas mensais/semanais
- Exportação para CSV

## 🔧 Desenvolvimento

### Estrutura de Classes Principais

```python
# main.py
class MacroEconomicBot:
    async def process_nfp()        # Handler NFP
    async def process_cpi()        # Handler CPI  
    async def process_fomc()       # Handler FOMC

# scoring_engine.py  
class ScoringEngine:
    def calculate_usd_score()      # Cálculo principal
    def _map_surprise_to_score()   # Regras por indicador

# data_ingestor.py
class DataIngestor:
    async def get_indicator_data() # Fetch TradingEconomics/FRED
    async def get_dxy_data()       # Yahoo Finance DXY

# hit_rate_tracker.py
class HitRateTracker:
    def log_prediction()           # Registra previsão
    def get_performance_metrics()  # Calcula hit-rate
```

### Adicionando Novos Indicadores

1. **Configurar em config.py**:
```python
'NEW_INDICATOR': {
    'weight': 1.0,
    'te_code': 'INDICATOR_CODE', 
    'category': 'employment',
    'release_time': '08:30'
}
```

2. **Adicionar regra em scoring_engine.py**:
```python
def _map_surprise_to_score(self, indicator, surprise_pct, actual, consensus):
    if indicator == 'NEW_INDICATOR':
        # Sua lógica de scoring aqui
        return score
```

3. **Criar handler em main.py**:
```python
async def process_new_indicator(self):
    await self._process_indicator('NEW_INDICATOR', ['Indicator Name'])
```

## 🐛 Troubleshooting

### Bot Não Inicia
```bash
# Verificar logs
docker-compose logs macro-bot

# Comum: chaves de API inválidas
# Verificar .env e testar APIs manualmente
```

### Sem Dados de Indicadores
```bash
# Verificar APIs
curl "https://api.tradingeconomics.com/calendar?c=united%20states&f=json&key=YOUR_KEY"

# Verificar FRED
curl "https://api.stlouisfed.org/fred/series/observations?series_id=PAYEMS&api_key=YOUR_KEY&file_type=json"
```

### Hit-Rate Baixo
```bash
# Verificar dados DXY
# Ajustar thresholds de classificação
# Revisar regras de scoring
```

## 📝 Logs

Logs são salvos em:
- **Container**: `/app/macro_bot.log`  
- **Host**: `./logs/macro_bot.log`

Níveis de log configuráveis via `LOG_LEVEL` no .env.

## 🔒 Segurança

- ✅ Não-root user no container
- ✅ Chaves em variáveis de ambiente
- ✅ Rate limiting com retry
- ✅ Health checks
- ✅ Resource limits

## 📈 Roadmap

- [ ] NLP para falas do Fed
- [ ] Probabilidades logísticas  
- [ ] Dashboard web (FastAPI)
- [ ] Alertas por webhooks
- [ ] Integração com brokers
- [ ] ML para otimização de pesos

## 🤝 Contribuição

1. Fork do projeto
2. Feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit (`git commit -m 'Add AmazingFeature'`)
4. Push (`git push origin feature/AmazingFeature`)  
5. Pull Request

## 📄 Licença

MIT License - veja arquivo `LICENSE` para detalhes.

---

**⚡ Bot Macroeconômico USD - Análise profissional dos mercados financeiros em tempo real!**