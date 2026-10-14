from mim_ai import anonymizer


if __name__ == "__main__":
    sample = "My CIN is AB123456. Please call 0612345678 or +212612345678. Email: hello@example.com. Ref: ORDER-123456."

    result = anonymizer.anonymize(
        sample,
        config={
            "custom_patterns": [
                {
                    "name": "ORDER_ID",
                    "pattern": r"ORDER-[0-9]{6}",
                    "operator": "replace",
                    "params": {"new_value": "[ORDER]"},
                }
            ]
        },
    )

    print(result.text)
    print(result.entities_found)
    print(result.operators_applied)
