from decimal import Decimal


def money(value) -> str:
    """'$1,234.56'."""
    return f"${Decimal(value):,.2f}"


def money_whole(value) -> str:
    """'$1,200' — for Dividend's round-dollar variables, which the handoff shows with no
    cents (docs/design/loop-6/benefits/dividend.html)."""
    return f"${Decimal(value):,.0f}"
