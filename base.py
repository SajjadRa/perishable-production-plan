from dataclasses import dataclass


@dataclass(frozen=True)
class PlantLine:
    index: int
    plant: "Plant"

    @classmethod
    def next_line(cls, plant: "Plant"):
        return cls(len(plant.lines) + 1, plant)

    def __repr__(self):
        return f"P{self.plant}-L{self.index}"

    def __str__(self):
        return self.__repr__()


class Plant:
    id: int
    lines: list[PlantLine]

    def __init__(self, idd, number_of_lines):
        self.id = idd
        self.lines = [PlantLine(i, self) for i in range(number_of_lines)]

    def __repr__(self):
        return f"P{self.id}"

    def __str__(self):
        return self.__repr__()


@dataclass(frozen=True)
class Product:
    id: int

    def __repr__(self):
        return f"Product{self.id}"

    def __str__(self):
        return self.__repr__()
