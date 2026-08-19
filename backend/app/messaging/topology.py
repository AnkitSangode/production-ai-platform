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
        arguments: dict[str, object] | None = None,
    ) -> AbstractQueue:

        return await self.channel.declare_queue(
            name=queue_name,
            durable=True,
            arguments=arguments,
        )

    async def declare_processing_queue(
        self,
        *,
        queue_name: str,
        dead_letter_exchange: str,
        dead_letter_routing_key: str,
    ) -> AbstractQueue:

        arguments = {
            "x-queue-type": "quorum",
            "x-dead-letter-exchange": dead_letter_exchange,
            "x-dead-letter-routing-key": dead_letter_routing_key,
            "x-delivery-limit": 5,
            "x-delayed-retry-type": "all",
            "x-delayed-retry-min": 5000,
            "x-delayed-retry-max": 30000,
        }

        return await self.declare_queue(
            queue_name=queue_name,
            arguments=arguments,
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

    async def declare_dead_letter_exchange(
        self,
        *,
        exchange_name: str,
    ) -> AbstractExchange:

        return await self.declare_exchange(
            exchange_name=exchange_name,
        )

    async def declare_dead_letter_queue(
        self,
        *,
        queue_name: str,
        exchange: AbstractExchange,
        routing_key: str,
    ) -> AbstractQueue:

        queue = await self.declare_queue(
            queue_name=queue_name,
        )

        await self.bind_queue(
            queue=queue,
            exchange=exchange,
            routing_key=routing_key,
        )

        return queue
