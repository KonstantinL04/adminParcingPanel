from channels.generic.websocket import AsyncWebsocketConsumer
import asyncio
import subprocess

class ParserConsoleConsumer(AsyncWebsocketConsumer):
    process = None

    async def connect(self):
        await self.accept()

        # Запускаем Telethon скрипт как subprocess
        self.process = await asyncio.create_subprocess_exec(
            "python", "adminparcing/utils/telegram/script.py",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        # Отправляем stdout в реальном времени
        asyncio.create_task(self.stream_output())

    async def stream_output(self):
        while True:
            line = await self.process.stdout.readline()
            if not line:
                break
            await self.send(line.decode("utf-8"))

    async def receive(self, text_data):
        """ Получаем от фронта ввод и передаём процессу """
        if self.process:
            self.process.stdin.write((text_data + "\n").encode())
            await self.process.stdin.drain()

    async def disconnect(self, close_code):
        if self.process:
            self.process.terminate()