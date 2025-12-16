from channels.generic.websocket import AsyncJsonWebsocketConsumer

class EventsConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("events", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("events", self.channel_name)

    async def event_created(self, event):
        await self.send_json(event["data"])