#!/usr/bin/env python3
"""
Bot Daemon - Versão indestrutível que monitora e reinicia automaticamente
Roda em thread separada para garantir funcionamento 24/7
"""

import asyncio
import threading
import time
import subprocess
import psutil
import os
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - DAEMON - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/telegram_bot/daemon.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BotDaemon:
    """Daemon que mantém o bot funcionando 24/7"""
    
    def __init__(self):
        self.bot_script = "/app/telegram_bot/enhanced_bot.py"
        self.bot_process = None
        self.running = True
        self.check_interval = 60  # Check every 60 seconds
        self.restart_count = 0
        self.last_restart = None
        
    def is_bot_healthy(self):
        """Verifica se o bot está saudável"""
        try:
            # Check if process is alive
            if not self.bot_process or self.bot_process.poll() is not None:
                return False
            
            # Check if process is responding (not zombie)
            try:
                process = psutil.Process(self.bot_process.pid)
                if process.status() == psutil.STATUS_ZOMBIE:
                    logger.warning("⚠️ Bot process is zombie")
                    return False
            except psutil.NoSuchProcess:
                return False
            
            # Check log file for recent activity (last 5 minutes)
            log_file = "/app/telegram_bot/bot_enhanced.log"
            if os.path.exists(log_file):
                stat = os.stat(log_file)
                last_modified = datetime.fromtimestamp(stat.st_mtime)
                time_diff = (datetime.now() - last_modified).total_seconds()
                
                if time_diff > 300:  # 5 minutes without activity
                    logger.warning(f"⚠️ Bot inactive for {time_diff:.0f} seconds")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking bot health: {e}")
            return False
    
    def kill_existing_bots(self):
        """Mata todos os processos do bot existentes"""
        try:
            killed = 0
            for process in psutil.process_iter(['pid', 'cmdline']):
                cmdline = ' '.join(process.info['cmdline']) if process.info['cmdline'] else ''
                if ('enhanced_bot.py' in cmdline or 'simple_bot.py' in cmdline) and process.pid != os.getpid():
                    logger.info(f"🔫 Killing existing bot: PID {process.pid}")
                    try:
                        process.terminate()
                        process.wait(timeout=5)
                        killed += 1
                    except:
                        try:
                            process.kill()
                            killed += 1
                        except:
                            pass
            
            if killed > 0:
                logger.info(f"🧹 Killed {killed} existing bot processes")
                time.sleep(3)
                
        except Exception as e:
            logger.error(f"Error killing existing bots: {e}")
    
    def start_bot(self):
        """Inicia o bot"""
        try:
            logger.info("🚀 Starting bot process...")
            
            # Kill existing processes first
            self.kill_existing_bots()
            
            # Start new process
            env = os.environ.copy()
            env['PYTHONPATH'] = '/app/telegram_bot'
            
            self.bot_process = subprocess.Popen(
                ['python3', self.bot_script],
                cwd='/app/telegram_bot',
                stdout=open('/app/telegram_bot/bot_enhanced.log', 'a'),
                stderr=subprocess.STDOUT,
                env=env,
                preexec_fn=os.setsid
            )
            
            # Wait for startup
            time.sleep(10)
            
            if self.is_bot_healthy():
                self.restart_count += 1
                self.last_restart = datetime.now()
                logger.info(f"✅ Bot started successfully! PID: {self.bot_process.pid}")
                return True
            else:
                logger.error("❌ Bot failed to start properly")
                return False
                
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            return False
    
    def stop_bot(self):
        """Para o bot gracefully"""
        try:
            if self.bot_process:
                logger.info("🛑 Stopping bot process...")
                
                # Try graceful shutdown first
                self.bot_process.terminate()
                try:
                    self.bot_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown fails
                    self.bot_process.kill()
                    self.bot_process.wait()
                
                logger.info("✅ Bot stopped")
                
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")
    
    def monitor_loop(self):
        """Loop principal de monitoramento"""
        logger.info("🔍 Starting monitoring loop...")
        
        while self.running:
            try:
                if not self.is_bot_healthy():
                    logger.warning("❌ Bot is not healthy - restarting...")
                    
                    # Stop current process if exists
                    if self.bot_process:
                        self.stop_bot()
                    
                    # Start new process
                    success = self.start_bot()
                    if not success:
                        logger.error("💥 Failed to restart bot - will try again in 60 seconds")
                else:
                    logger.info("✅ Bot is healthy")
                
                # Log system stats
                memory = psutil.virtual_memory()
                cpu = psutil.cpu_percent(interval=1)
                logger.info(f"📊 System: RAM {memory.percent:.1f}% | CPU {cpu:.1f}% | Restarts: {self.restart_count}")
                
                # Sleep before next check
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                logger.info("🛑 Daemon interrupted by user")
                self.running = False
                break
            except Exception as e:
                logger.error(f"💥 Error in monitoring loop: {e}")
                time.sleep(30)  # Wait longer on error
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"📡 Received signal {signum} - shutting down daemon...")
        self.running = False
        self.stop_bot()
    
    def run(self):
        """Executa o daemon"""
        try:
            logger.info("🚀 Bot Daemon starting...")
            
            # Setup signal handlers
            signal.signal(signal.SIGTERM, self.signal_handler)
            signal.signal(signal.SIGINT, self.signal_handler)
            
            # Start initial bot
            if not self.start_bot():
                logger.error("💥 Failed to start initial bot!")
                return False
            
            # Start monitoring loop
            self.monitor_loop()
            
            logger.info("👋 Bot Daemon stopped")
            return True
            
        except Exception as e:
            logger.error(f"💥 Fatal daemon error: {e}")
            return False

def main():
    """Função principal"""
    try:
        daemon = BotDaemon()
        daemon.run()
    except KeyboardInterrupt:
        logger.info("👋 Daemon stopped by user")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()