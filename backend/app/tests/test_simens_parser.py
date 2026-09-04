from app.services.parser.siemens_parser import (is_siemens_product_code)


def test_siemens_product_code():
    assert is_siemens_product_code("5SL41020RC")


def test_siemens_product_code_with_suffix():
    assert is_siemens_product_code("5SU13247RC32")


def test_invalid_product_code():
    assert not is_siemens_product_code("16A")