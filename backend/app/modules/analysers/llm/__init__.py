from app.core.module_base import ModuleInfo
from app.modules.analysers.llm.router import router
from app.modules.analysers.llm.models import LLMConfig
from app.modules.analysers.llm.service import get_status, check_configured, analyze

MODULE_INFO = ModuleInfo(
    key="llm",
    name="LLM Analyser",
    type="analyser",
    version="1.0.0",
    description="Analyse data using LLM (via LiteLLM) to extract order information",
    router=router,
    models=[LLMConfig],
    status=get_status,
    is_configured=check_configured,
    analyze=analyze,
)
