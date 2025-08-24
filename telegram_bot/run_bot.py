#!/usr/bin/env python3
"""
Executor simples do bot para teste
"""

import asyncio
import logging
import sys
from main import MacroEconomicBot

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    bot = MacroEconomicBot()
    try:
        await bot.run()
    except KeyboardInterrupt:
        print("\n🛑 Bot finalizado pelo usuário")
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot finalizado!")