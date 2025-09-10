#!/usr/bin/env python3
"""
KeepAlive Monitor - Garante que o bot esteja sempre rodando
Executa a cada 5 minutos via cron
"""

import subprocess
import time
import logging
import sys
from datetime import datetime
import psutil
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - KEEPALIVE - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/telegram_bot/keepalive.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BotKeepAlive:
    def __init__(self):
        self.bot_script = "/app/telegram_bot/enhanced_bot.py"
        self.bot_log = "/app/telegram_bot/bot_enhanced.log"
        
    def is_bot_running(self):
        """Verifica se o bot está rodando"""
        try:
            for process in psutil.process_iter(['pid', 'name', 'cmdline']):
                cmdline = ' '.join(process.info['cmdline']) if process.info['cmdline'] else ''
                if 'enhanced_bot.py' in cmdline:
                    logger.info(f"✅ Bot encontrado rodando: PID {process.info['pid']}")
                    return True
            return False
        except Exception as e:
            logger.error(f"Erro ao verificar processos: {e}")
            return False
    
    def test_bot_response(self):
        """Testa se o bot está respondendo (verifica log recente)"""
        try:
            if not os.path.exists(self.bot_log):
                return False
            
            # Verifica se houve atividade nos últimos 2 minutos
            stat = os.stat(self.bot_log)
            last_modified = datetime.fromtimestamp(stat.st_mtime)
            now = datetime.now()
            
            time_diff = (now - last_modified).total_seconds()
            
            if time_diff < 120:  # 2 minutes
                logger.info(f"✅ Bot ativo (última atividade: {time_diff:.0f}s atrás)")
                return True
            else:
                logger.warning(f"⚠️ Bot inativo (última atividade: {time_diff:.0f}s atrás)")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao verificar resposta do bot: {e}")
            return False
    
    def start_bot(self):
        """Inicia o bot"""
        try:
            logger.info("🚀 Iniciando bot...")
            
            # Kill processos antigos primeiro
            self.kill_old_processes()
            
            # Inicia novo processo
            cmd = ['nohup', 'python3', self.bot_script]
            with open(self.bot_log, 'a') as log_file:
                process = subprocess.Popen(
                    cmd,
                    cwd='/app/telegram_bot',
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    preexec_fn=os.setsid
                )
            
            time.sleep(5)  # Wait for startup
            
            if self.is_bot_running():
                logger.info("✅ Bot iniciado com sucesso!")
                return True
            else:
                logger.error("❌ Falha ao iniciar bot")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao iniciar bot: {e}")
            return False
    
    def kill_old_processes(self):
        """Mata processos antigos do bot"""
        try:
            killed_count = 0
            for process in psutil.process_iter(['pid', 'name', 'cmdline']):
                cmdline = ' '.join(process.info['cmdline']) if process.info['cmdline'] else ''
                if 'enhanced_bot.py' in cmdline or 'simple_bot.py' in cmdline:
                    logger.info(f"🔫 Matando processo antigo: PID {process.info['pid']}")
                    process.kill()
                    killed_count += 1
            
            if killed_count > 0:
                time.sleep(3)  # Wait for processes to die
                logger.info(f"🧹 {killed_count} processos antigos removidos")
                
        except Exception as e:
            logger.error(f"Erro ao matar processos: {e}")
    
    def check_system_resources(self):
        """Verifica recursos do sistema"""
        try:
            # Memory usage
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)
            
            logger.info(f"📊 Sistema - RAM: {memory.percent:.1f}% | CPU: {cpu_percent:.1f}%")
            
            # Alert se recursos muito altos
            if memory.percent > 90:
                logger.warning("⚠️ Memória alta! Pode causar instabilidade")
            
            if cpu_percent > 95:
                logger.warning("⚠️ CPU alta! Pode causar lentidão")
                
        except Exception as e:
            logger.error(f"Erro ao verificar recursos: {e}")
    
    def run_check(self):
        """Executa verificação completa"""
        logger.info("=" * 50)
        logger.info("🔍 KEEPALIVE CHECK - Verificando bot...")
        
        # Check system resources
        self.check_system_resources()
        
        # Check if bot is running
        is_running = self.is_bot_running()
        is_responding = self.test_bot_response() if is_running else False
        
        if is_running and is_responding:
            logger.info("✅ Bot funcionando perfeitamente!")
            return True
        
        elif is_running and not is_responding:
            logger.warning("⚠️ Bot rodando mas não respondendo - reiniciando...")
            self.kill_old_processes()
            return self.start_bot()
        
        else:
            logger.warning("❌ Bot não está rodando - iniciando...")
            return self.start_bot()

def main():
    """Função principal"""
    try:
        keepalive = BotKeepAlive()
        success = keepalive.run_check()
        
        if success:
            logger.info("🎉 KeepAlive concluído com sucesso!")
            sys.exit(0)
        else:
            logger.error("💥 KeepAlive falhou!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("👋 KeepAlive interrompido pelo usuário")
        sys.exit(0)
    except Exception as e:
        logger.error(f"💥 Erro crítico no KeepAlive: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()