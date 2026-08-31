from pydantic import BaseModel, ConfigDict


class ProductAttributeCreate(BaseModel):
    attribute_name: str
    attribute_value: str


class ProductCodeCreate(BaseModel):
    code: str
    code_type: str
    is_primary: bool = False


class ProductCreate(BaseModel):
    name: str

    brand_id: int | None = None
    category_id: int | None = None

    description: str | None = None
    unit: str | None = None
    image_url: str | None = None

    codes: list[ProductCodeCreate] = []
    attributes: list[ProductAttributeCreate] = []


class ProductResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    name: str
    brand_id: int | None
    category_id: int | None
    description: str | None
    unit: str | None
    image_url: str | None
    is_active: bool