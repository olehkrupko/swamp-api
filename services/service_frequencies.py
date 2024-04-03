import random
from datetime import timedelta
from enum import Enum


class Frequencies(Enum):
    # active:
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"
    YEARS = "years"
    # disabled:
    NEVER = "never"

    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))

    @classmethod
    def validate(cls, frequency):
        if frequency in cls.list():
            return True
        else:
            raise ValueError(f"{frequency=} is not in {Frequencies.list()}")

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
            raise ValueError("You cannot delay if it's never updated")
        else:
            raise Exception(f"It's not expected to happen, frequency={self}")
