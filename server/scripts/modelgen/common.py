def snake_to_camel(name: str) -> str:
    return "".join(word.capitalize() for word in name.split("_"))


def next_power_of_2(n: int) -> int:
    return 1 if n == 0 else 2 ** (n - 1).bit_length()
