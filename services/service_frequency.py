"""Frequency scheduling helpers.

Defines supported feed frequencies and generates randomized delay intervals.
"""

import random
from datetime import timedelta
from enum import Enum


class Frequency(Enum):
    """Feed update frequency options and helper delay calculations."""
    # active:
    MINUTES = "MINUTES"
    HOURS = "HOURS"
    DAYS = "DAYS"
    WEEKS = "WEEKS"
    MONTHS = "MONTHS"
    YEARS = "YEARS"
    # disabled:
    NEVER = "NEVER"

    @classmethod
    def list(cls):
        """Return a list of all available frequency values."""
        return list(map(lambda c: c.value, cls))

    def delay(self):
        """Return a randomized delay timedelta for the frequency."""
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
