def distribute_shares(count: int) -> list[int]:
    """Доли в процентах: сумма всегда 100, разница не больше 1."""
    if count <= 0:
        return []
    if count > 100:
        raise ValueError("больше 100 офферов в потоке нельзя")
    base, rest = divmod(100, count)
    return [base + (1 if i < rest else 0) for i in range(count)]
