FREQUENCIES = (
    "minutes",
    "hours",
    "days",
    "weeks",
    "months",
    "years",
    "never",  # disabled
)

def frequency_validate(val):
    return val in FREQUENCIES
