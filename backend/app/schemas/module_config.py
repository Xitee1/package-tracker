from pydantic import BaseModel


class ModuleResponse(BaseModel):
    module_key: str
    enabled: bool

    model_config = {"from_attributes": True}


class UpdateModuleRequest(BaseModel):
    enabled: bool
