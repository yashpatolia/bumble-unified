def condense(num) -> str:
    """Return the condensed number with appropriate suffix."""
    if type(num) is str:
        return num

    num = float("{:.4g}".format(num))
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return "{}{}".format("{:f}".format(num).rstrip("0").rstrip("."), ["", "K", "M", "B", "T"][magnitude])
