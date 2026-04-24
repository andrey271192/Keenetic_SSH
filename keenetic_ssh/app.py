import asyncio, logging, sys

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )
    from .bot import telegram_loop
    asyncio.run(telegram_loop())
