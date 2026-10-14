from mim_ai.anonymizer import anonymize


def test_moroccan_phone_detection():
    text = "Call 0612345678 or +212612345678 for support."
    result = anonymize(text)
    assert any(item["type"] == "PHONE_MA" for item in result.entities_found)
    assert result.text != text
