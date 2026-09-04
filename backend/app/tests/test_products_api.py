from app.main import app


def test_products_endpoint_exists():
    paths = set(
        app.openapi()["paths"].keys()
    )

    assert "/api/v1/products" in paths
    assert "/api/v1/products/{product_id}" in paths