from abc import ABC, abstractmethod
from typing import BinaryIO


class ParserService(ABC):

    @abstractmethod
    def parse(self, file: BinaryIO) -> list[str]:
        pass