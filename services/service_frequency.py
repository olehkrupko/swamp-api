import random
from datetime import timedelta
from enum import Enum


class Frequency(Enum):
    # TODO: it seems that the values are not used, Enum names are used instead

    # active:
    MINUTES = None
    HOURS = None
    DAYS = None
    WEEKS = None
    MONTHS = None
    YEARS = None
    # disabled:
    NEVER = None

    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))

    # def __str__(self):
    #     return self.value

    # def __repr__(self):
    #     return f"Frequency.{self.value.upper()}"

    def delay(self):
        if self == self.MINUTES:
            return timedelta(
                minutes=random.randint(3, 60),
            )
        elif self == self.HOURS:
            return timedelta(
                minutes=random.randint(-15, 15),
                hours=random.randint(3, 12),
            )
        elif self == self.DAYS:
            return timedelta(
                minutes=random.randint(-15, 15),
                hours=random.randint(-6, 6),
                days=random.randint(2, 7),
            )
        elif self == self.WEEKS:
            return timedelta(
                minutes=random.randint(-15, 15),
                hours=random.randint(-6, 6),
                days=random.randint(-7, 7),
                weeks=random.randint(2, 6),
            )
        elif self == self.MONTHS:
            return timedelta(
                minutes=random.randint(-15, 15),
                hours=random.randint(-6, 6),
                days=random.randint(-7, 7),
                weeks=random.randint(6, 37),
            )
        elif self == self.YEARS:
            return timedelta(
                minutes=random.randint(-15, 15),
                hours=random.randint(-6, 6),
                days=random.randint(-7, 7),
                weeks=random.randint(42, 150),
            )
        elif self == self.NEVER:
            return timedelta(0)
        else:
            raise Exception(f"It's not expected to happen, frequency={self}")
