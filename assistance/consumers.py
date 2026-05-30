from channels.generic.websocket import AsyncJsonWebsocketConsumer


class HelpRequestConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.help_request_id = self.scope["url_route"]["kwargs"]["help_request_id"]
        self.group_name = f"help_request_{self.help_request_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def help_event(self, event):
        await self.send_json(event["data"])


class HelpPresenceConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.group_name = "help_presence"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def help_presence_event(self, event):
        await self.send_json(event["data"])
