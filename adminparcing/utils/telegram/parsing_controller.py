# parsing_controller.py
import asyncio
import threading
from adminparcing.utils.nlp.NLPModel import reload_nlp_data
from adminparcing.utils.telegram.script import client, main as telethon_main

class ParserController:
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = None
        self.running = False

        def run_loop():
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()

        self.thread = threading.Thread(target=run_loop, daemon=True)
        self.thread.start()

    def start(self):
        if self.running:
            return False
        reload_nlp_data()
        asyncio.run_coroutine_threadsafe(
            telethon_main(),
            self.loop
        )
        self.running = True
        return True

    def stop(self):
        if not self.running:
            return False

        async def shutdown():
            await client.disconnect()

        asyncio.run_coroutine_threadsafe(shutdown(), self.loop)
        self.running = False
        return True


parser_controller = ParserController()