import aio_pika

from app.core.config import settings


async def get_connection():
    connection = await aio_pika.connect_robust(
        settings.rabbitmq_url
    )

    return connection


class RabbitMQManager:

    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange = None