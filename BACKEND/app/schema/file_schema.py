from pydantic import BaseModel,Field

class RenameRequest(BaseModel):
    new_file_name:str=Field(...,min_length=1)

class UploadInitRequest(BaseModel):
    file_name:str = Field(min_length=1,max_length=255)
    file_size:int = Field(gt=0)