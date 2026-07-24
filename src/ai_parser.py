import json
import os

from openai import OpenAI


def extract_invoice_fields_with_ai(text: str) -> dict:
    """Use an AI model to extract structured fields from invoice text."""

    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError(
            "OPENAI_API_KEY is missing. "
            "Set it in your terminal before running the program."
        )

    client = OpenAI()

    response = client.responses.create(
        model="gpt-5",
        instructions=(
            "You extract structured financial data from invoices. "
            "Do not guess missing information. "
            "Use null when a value is unavailable."
        ),
        input=(
            "Extract the invoice information from the text below.\n\n"
            f"{text}"
        ),
        text={
            "format": {
                "type": "json_schema",
                "name": "invoice_data",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "vendor": {
                            "type": ["string", "null"],
                        },
                        "invoice_number": {
                            "type": ["string", "null"],
                        },
                        "invoice_date": {
                            "type": ["string", "null"],
                        },
                        "due_date": {
                            "type": ["string", "null"],
                        },
                        "description": {
                            "type": ["string", "null"],
                        },
                        "subtotal": {
                            "type": ["number", "null"],
                        },
                        "tax": {
                            "type": ["number", "null"],
                        },
                        "shipping": {
                            "type": ["number", "null"],
                        },
                        "total_due": {
                            "type": ["number", "null"],
                        },
                    },
                    "required": [
                        "vendor",
                        "invoice_number",
                        "invoice_date",
                        "due_date",
                        "description",
                        "subtotal",
                        "tax",
                        "shipping",
                        "total_due",
                    ],
                    "additionalProperties": False,
                },
            }
        },
    )

    return json.loads(response.output_text)