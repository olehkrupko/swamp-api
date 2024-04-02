import random
from datetime import timedelta


class Frequencies:
    OPTIONS = (
        "minutes",
        "hours",
        "days",
        "weeks",
        "months",
        "years",
        "never",  # disabled
    )

    @classmethod
    def get_options(cls):
        return cls.OPTIONS

    @classmethod
    def validate(cls, val):
        return val in cls.OPTIONS

    @classmethod
    def delay(cls, frequency):
        if not cls.validate(frequency):
            raise ValueError(f"Wrong value {frequency=}")

        if frequency == "minutes":
            return timedelta(
                minutes=random.randint(3, 60),
            )
        elif frequency == "hours":
            return timedelta(
                minutes=random.randint(-15, 15),
                hours=random.randint(3, 12),
            )
        elif frequency == "days":
            return timedelta(
                minutes=random.randint(-15, 15),
                hours=random.randint(-6, 6),
                days=random.randint(2, 7),
            )
        elif frequency == "weeks":
            return timedelta(
                minutes=random.randint(-15, 15),
                hours=random.randint(-6, 6),
                days=random.randint(-7, 7),
                weeks=random.randint(2, 6),
            )
        elif frequency == "months":
            return timedelta(
                minutes=random.randint(-15, 15),
                hours=random.randint(-6, 6),
                days=random.randint(-7, 7),
                weeks=random.randint(6, 37),
            )
        elif frequency == "years":
            return timedelta(
                minutes=random.randint(-15, 15),
                hours=random.randint(-6, 6),
                days=random.randint(-7, 7),
                weeks=random.randint(42, 150),
            )
        elif frequency == "never":
            raise ValueError("You cannot delay if it's never updated")
        else:
            raise Exception("It's not expected to happen")
