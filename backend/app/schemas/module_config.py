from pydantic import BaseModel


class ModuleResponse(BaseModel):
    module_key: str
    enabled: bool
    configured: bool = True
    priority: int = 0
    name: str | None = None
    type: str | None = None
    description: str | None = None

    model_config = {"from_attributes": True}


class UpdateModuleRequest(BaseModel):
    enabled: bool


class ReorderModulesRequest(BaseModel):
    module_keys: list[str]
