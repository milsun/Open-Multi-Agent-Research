from src.tools.tools import Tool, ToolResult, AsyncTool, make_tool_instance
from src.tools.deep_analyzer import DeepAnalyzerTool
from src.tools.deep_researcher import DeepResearcherTool
from src.tools.planning import PlanningTool

# Conditional import for vector tools (they have LangChain dependencies)
try:
    from src.tools.vector_database import VectorIndexerTool, VectorSearchTool
    from src.tools.vector_function_calls import VectorFunctionCallsTool
    from src.tools.vector_api_service import VectorAPIService, FunctionCallRequest, FunctionCallResponse, get_vector_api_service
    VECTOR_AVAILABLE = True
except ImportError:
    VectorIndexerTool = None
    VectorSearchTool = None
    VectorFunctionCallsTool = None
    VectorAPIService = None
    FunctionCallRequest = None
    FunctionCallResponse = None
    get_vector_api_service = None
    VECTOR_AVAILABLE = False

from src.tools.interactive_planning import InteractivePlanningTool, UserClarificationTool

# Conditional import for browser tools (they have external dependencies)
try:
    from src.tools.auto_browser import AutoBrowserUseTool
    BROWSER_AVAILABLE = True
except ImportError:
    AutoBrowserUseTool = None
    BROWSER_AVAILABLE = False


__all__ = [
    "Tool",
    "ToolResult", 
    "AsyncTool",
    "DeepAnalyzerTool",
    "DeepResearcherTool",
    "PlanningTool",
    "InteractivePlanningTool",
    "UserClarificationTool",
    "make_tool_instance"
]

# Add vector tools if available
if VECTOR_AVAILABLE:
    __all__.extend([
        "VectorIndexerTool",
        "VectorSearchTool", 
        "VectorFunctionCallsTool",
        "VectorAPIService",
        "FunctionCallRequest",
        "FunctionCallResponse",
        "get_vector_api_service"
    ])

# Add browser tools if available
if BROWSER_AVAILABLE:
    __all__.append("AutoBrowserUseTool")