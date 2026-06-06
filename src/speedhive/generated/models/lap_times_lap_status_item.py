from enum import Enum


class LapTimesLapStatusItem(str, Enum):
    GREEN = "GREEN"
    RED = "RED"
    YELLOW = "YELLOW"

    def __str__(self) -> str:
        return str(self.value)
