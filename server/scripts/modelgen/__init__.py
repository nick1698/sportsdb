def snake_to_camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


def next_power_of_2(n: int) -> int:
    return 1 if n == 0 else 2 ** (n - 1).bit_length()
