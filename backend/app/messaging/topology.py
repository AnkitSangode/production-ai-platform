from aio_pika import Channel, ExchangeType
from aio_pika.abc import AbstractExchange, AbstractQueue


class BrokerTopology:

    def __init__(
        self,
        channel: Channel,
    ) -> None:
        self.channel = channel

    async def declare_exchange(
        self,
        *,
        exchange_name: str,
    ) -> AbstractExchange:

        return await self.channel.declare_exchange(
            name=exchange_name,
            type=ExchangeType.TOPIC,
            durable=True,
        )

    async def declare_queue(
        self,
        *,
        queue_name: str,
    ) -> AbstractQueue:

        return await self.channel.declare_queue(
            name=queue_name,
            durable=True,
        )

    async def bind_queue(
        self,
        *,
        queue: AbstractQueue,
        exchange: AbstractExchange,
        routing_key: str,
    ) -> None:

        await queue.bind(
            exchange,
            routing_key=routing_key,
        )
