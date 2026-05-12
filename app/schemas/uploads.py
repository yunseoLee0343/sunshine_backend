from pydantic import BaseModel


class PlantImageUploadResponse(BaseModel):
    image_ref: str
    content_type: str
    size_bytes: int
