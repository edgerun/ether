import re

__size_conversions = {
    'K': 10 ** 3,
    'M': 10 ** 6,
    'G': 10 ** 9,
    'T': 10 ** 12,
    'P': 10 ** 15,
    'E': 10 ** 18,
    'Ki': 2 ** 10,
    'Mi': 2 ** 20,
    'Gi': 2 ** 30,
    'Ti': 2 ** 40,
    'Pi': 2 ** 50,
    'Ei': 2 ** 60
}

__size_pattern = re.compile(r"([0-9]+)([a-zA-Z]*)")


def parse_size_string(size_string: str) -> int:
    m = __size_pattern.match(size_string)
    if len(m.groups()) > 1:
        number = m.group(1)
        unit = m.group(2)
        return int(number) * __size_conversions.get(unit, 1)
    else:
        return int(m.group(1))


def to_size_string(num_bytes, unit='M', precision=1) -> str:
    factor = __size_conversions[unit]
    value = num_bytes / factor

    fmt = f'%0.{precision}f{unit}'

    return fmt % value
