from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from num2words import num2words


def amount_to_words(amount) -> str:
    """
    Convert an INR amount into words using the Indian
    lakh/crore numbering system.

    Example:
    125430.75
    -> Rupees One Lakh Twenty-Five Thousand Four Hundred
       And Thirty And Seventy-Five Paise Only
    """

    try:
        normalized_amount = Decimal(
            str(amount)
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

    except (
        InvalidOperation,
        TypeError,
        ValueError
    ) as error:
        raise ValueError("Invalid amount") from error

    if normalized_amount < 0:
        raise ValueError(
            "Amount cannot be negative"
        )

    rupees = int(normalized_amount)

    paise = int(
        (
            normalized_amount -
            Decimal(rupees)
        ) * Decimal("100")
    )

    rupees_words = num2words(
        rupees,
        lang="en_IN"
    ).title()

    if paise > 0:
        paise_words = num2words(
            paise,
            lang="en_IN"
        ).title()

        return (
            f"Rupees {rupees_words} "
            f"And {paise_words} Paise Only"
        )

    return f"Rupees {rupees_words} Only"