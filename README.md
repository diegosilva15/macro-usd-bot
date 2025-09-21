# 🚀 Bot Macroeconômico USD - Deploy Render.com

Bot profissional para análise macroeconômica do dólar americano, otimizado para rodar 24/7 no Render.com.

## ⚡ Deploy Rápido (20 minutos)

### 1. 📁 Preparar Repositório GitHub

```bash
# Criar novo repositório no GitHub
# Nome sugerido: macro-usd-bot

# Arquivos necessários:
├── render_bot.py          # Bot principal
├── requirements_render.txt # Dependências
├── README.md              # Documentação
└── .env.example           # Template variáveis
```

### 2. 🌐 Configurar Render.com

1. **Acesse:** https://render.com
2. **Clique:** "Sign Up" → Conecte com GitHub
3. **Autorize:** Render a acessar seus repositórios
4. **Dashboard:** Clique "New +"

### 3. 🔧 Criar Web Service

1. **New Web Service** 
2. **Connect Repository:** Escolha `macro-usd-bot`
3. **Configurações:**
   ```
   Name: macro-usd-bot
   Environment: Python 3
   Build Command: pip install -r requirements_render.txt
   Start Command: python render_bot.py
   ```

### 4. 🔑 Environment Variables

No painel do Render, adicione:

```
BOT_TOKEN = 7487750473:AAFMuwnwDn6ExY5XEbB0kR1L04YumGNniS0
DEFAULT_CHAT_ID = -4904487675
FRED_API_KEY = 92fcf288dd543b2ebcdd37241fd30257
ALPHA_VANTAGE_API_KEY = 5U0YFWPYQSNKG8RT
```

### 5. 🚀 Deploy Automático

1. **Save & Deploy** - Render vai:
   - ✅ Baixar código do GitHub
   - ✅ Instalar dependências  
   - ✅ Iniciar bot automaticamente
   - ✅ Gerar URL pública

2. **Aguardar** ~3-5 minutos para primeiro deploy

3. **Verificar logs** na interface do Render

## ✅ Funcionamento 24/7

### 🛡️ Render Cuida de:
- **Auto-restart** se bot parar
- **Health checks** automáticos
- **Scaling** conforme necessário  
- **Backup** e recovery
- **SSL/HTTPS** automático
- **Logs** completos na interface

### 📊 Monitoramento:
- **Logs:** Tempo real no painel Render
- **Métricas:** CPU, RAM, requests
- **Alerts:** Email se houver problemas  
- **Uptime:** 99.9% garantido

## 🎯 Comandos Disponíveis

- `/start` - Inicializar bot
- `/status` - Status do sistema  
- `/score` - Análise USD Score
- `/summary` - Resumo econômico
- `/help` - Manual completo

## 🔧 Manutenção

### Deploy Automático:
- **Push no GitHub** → Deploy automático no Render
- **Zero downtime** durante updates
- **Rollback** fácil se necessário

### Configuração:
- **Environment vars:** Painel Render
- **Logs:** Interface web
- **Scaling:** Automático

## 💰 Custos

### Free Tier (750h/mês):
- ✅ **Suficiente** para bot 24/7
- ✅ **0 custo** mensal
- ✅ **Sem cartão** necessário

### Paid Tier ($7/mês):
- ✅ **Uptime garantido** 100%
- ✅ **Sem sleep** automático
- ✅ **Suporte prioritário**

## 🆘 Troubleshooting

### Bot não responde:
1. Verificar logs no Render
2. Conferir environment variables  
3. Testar token do Telegram
4. Restart manual se necessário

### Deploy falha:
1. Verificar requirements_render.txt
2. Conferir sintaxe do Python
3. Logs de build no Render
4. Contactar suporte se persistir

## 📞 Suporte

- **Render Docs:** https://render.com/docs
- **Status Page:** https://status.render.com  
- **Community:** https://community.render.com

---

**🎉 Com Render.com seu bot roda 24/7 sem dor de cabeça!** 🚀
