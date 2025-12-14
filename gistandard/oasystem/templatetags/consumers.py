import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from approval.models import ApprovalNode

class NotifyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        self.group_name = f'user_{self.user.id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        # 首次连接推送当前待办
        count = await self.get_pending_count()
        await self.send(text_data=json.dumps({'count': count}))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_notify(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def get_pending_count(self):
        return ApprovalNode.objects.filter(approver=None, apply_sn__isnull=False).count()