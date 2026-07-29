import aio_pika

from aio_pika import Connection, Channel, ExchangeType

from app.messaging.broker import MessageBroker

from app.core.config import Settings


class RabbitMQBroker(MessageBroker):

    def __init__(self, settings: Settings, exchange_name: str) -> None:
        self.settings = settings
        self.exchange_name = exchange_name

        self.connection = None
        self.channel = None
        self.exchange = None

    async def connect(self):
        self.connection = await aio_pika.connect_robust(self.settings.rabbitmq_url)

        self.channel = await self.connection.channel()

        self.exchange = await self.channel.declare_exchange(
            name=self.exchange_name,
            type=ExchangeType.TOPIC,
            durable=True,
        )
