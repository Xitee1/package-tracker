from app.core.module_base import ModuleInfo
from app.modules.analysers.llm.router import router
from app.modules.analysers.llm.models import LLMConfig

MODULE_INFO = ModuleInfo(
    key="llm",
    name="LLM Analyser",
    type="analyser",
    version="1.0.0",
    description="Analyse emails using LLM (via LiteLLM) to extract order information",
    router=router,
    models=[LLMConfig],
)
