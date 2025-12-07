from enum import Enum


class OrganizationSport(str, Enum):
    BIKE = "Bike"
    CAR = "Car"
    CYCLING = "Cycling"
    EQUINE = "Equine"
    ICESKATING = "IceSkating"
    INLINESKATING = "InlineSkating"
    KARTING = "Karting"
    MODELBOATRACING = "ModelBoatRacing"
    MX = "MX"
    OTHER = "Other"
    RC = "RC"
    RUNNING = "Running"
    STOCKCAR = "StockCar"
    SWIMMING = "Swimming"
    UNKNOWN = "Unknown"

    def __str__(self) -> str:
        return str(self.value)
