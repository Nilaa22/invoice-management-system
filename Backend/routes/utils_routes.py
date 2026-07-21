from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from flask import Blueprint, jsonify, request

from utils.amount_to_words import amount_to_words


utils_bp = Blueprint(
    "utils_bp",
    __name__
)


@utils_bp.route(
    "/amount-to-words",
    methods=["POST"]
)
def convert_amount():
    data = request.get_json(
        silent=True
    ) or {}

    raw_amount = data.get("amount")

    if raw_amount is None:
        return jsonify({
            "message": "Amount is required"
        }), 400

    try:
        amount = Decimal(
            str(raw_amount)
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        if amount < 0:
            return jsonify({
                "message": (
                    "Amount cannot be negative"
                )
            }), 400

        return jsonify({
            "amount": str(amount),
            "amount_in_words":
                amount_to_words(amount)
        }), 200

    except (
        InvalidOperation,
        TypeError,
        ValueError
    ):
        return jsonify({
            "message": "Invalid amount"
        }), 400