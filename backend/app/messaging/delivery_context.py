from dataclasses import dataclass


@dataclass(frozen=True)
class DeliveryContext:
    final_attempt: bool = False