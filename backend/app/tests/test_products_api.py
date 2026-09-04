def test_products_endpoint_exists():
    # Basic routing contract test.
    # Full DB integration should use a test PostgreSQL database.
    from app.main import app

    routes = {
        route.path
        for route in app.routes
    }

    assert "/api/v1/products" in routes
    assert "/api/v1/products/{product_id}" in routes