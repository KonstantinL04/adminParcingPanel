# parsing_controller.py
import asyncio
import threading
import time
from adminparcing.utils.nlp.NLPModel import reload_nlp_data
from adminparcing.utils.nlp.resolve_locations import process_new_messages
from adminparcing.utils.telegram.script import prepare_runtime, qr_login, start_client, stop_client
from adminparcing.services.event_client import expire_dynamic_events

class ParserController:
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = None
        self.running = False
        self.loc_thread = None
        self.loc_stop = threading.Event()

        def run_loop():
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()

        self.thread = threading.Thread(target=run_loop, daemon=True)
        self.thread.start()

    def start(self):
        if self.running:
            return False
        reload_nlp_data()
        if not prepare_runtime():
            print("❌ ParserController: не удалось подготовить данные/ключи для Telegram")
            return False
        async def run():
            await qr_login()
            await start_client()

        fut = asyncio.run_coroutine_threadsafe(run(), self.loop)

        def _log_result(f):
            try:
                f.result()
                print("✅ ParserController: парсер реально запущен")
            except Exception as e:
                print(f"❌ ParserController: ошибка запуска парсера: {e!r}")

        fut.add_done_callback(_log_result)
        self.running = True
        if self.loc_thread is None or not self.loc_thread.is_alive():
            self.loc_stop.clear()
            self.loc_thread = threading.Thread(target=self._location_loop, daemon=True)
            self.loc_thread.start()
        return True

    def stop(self):
        if not self.running:
            return False

        asyncio.run_coroutine_threadsafe(stop_client(), self.loop)
        self.loc_stop.set()
        self.running = False
        return True

    def _location_loop(self):
        while not self.loc_stop.is_set():
            try:
                process_new_messages()
                expire_dynamic_events()
            except Exception as e:
                print(f"❌ Location resolver error: {e!r}")
            time.sleep(5)


parser_controller = ParserController()
