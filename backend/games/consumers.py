"""WebSocket d'une partie : les deux joueurs reçoivent la nouvelle position et les messages
dès qu'ils changent. La connexion est en lecture seule : les actions passent par l'API."""

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from . import services
from .models import Game

FORBIDDEN = 4403


class GameConsumer(AsyncJsonWebsocketConsumer):
    group: str | None = None

    async def connect(self):
        self.code = services.normalize_code(self.scope["url_route"]["kwargs"]["code"])
        user = self.scope.get("user")
        await self.accept()
        if user is None or not user.is_authenticated or not await self.is_player(user):
            await self.close(code=FORBIDDEN)
            return
        self.group = services.group_name(self.code)
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.send_state()

    async def disconnect(self, code):
        if self.group:
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def receive_json(self, content, **kwargs):
        """Rien à faire : le navigateur n'envoie rien sur cette connexion."""

    async def game_update(self, event):
        await self.send_state()

    async def chat_message(self, event):
        await self.send_json({"type": "message", "message": event["message"]})

    async def send_state(self):
        state = await self.state(self.scope["user"])
        if state is None:
            # Partie supprimée entre-temps (annulée par son créateur).
            await self.close(code=FORBIDDEN)
            return
        await self.send_json({"type": "partie", "partie": state})

    @database_sync_to_async
    def is_player(self, user) -> bool:
        game = Game.objects.filter(code=self.code).first()
        return game is not None and game.color_of(user) is not None

    @database_sync_to_async
    def state(self, user) -> dict | None:
        game = Game.objects.select_related("white", "black", "creator").filter(code=self.code).first()
        if game is None or game.color_of(user) is None:
            return None
        return services.game_state(game, user)
