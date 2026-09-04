from app.services.parser.siemens_parser import (
    is_siemens_reference,
)


def test_siemens_reference():
    assert is_siemens_reference(
        "5SL41020RC"
    )


def test_siemens_reference_with_suffix():
    assert is_siemens_reference(
        "5SU13247RC32"
    )


def test_invalid_siemens_reference():
    assert not is_siemens_reference(
        "16A"
    )