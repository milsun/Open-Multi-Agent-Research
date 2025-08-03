web_fetcher_tool_config = dict(
    type="web_fetcher_tool",
)

web_searcher_tool_config = dict(
    type="web_searcher_tool",
    engine="Firecrawl",
    retry_delay = 10,
    max_retries = 3,
    lang = "en",
    country = "us",
    num_results = 5,
    fetch_content = True,
    max_length = 4096,
)

deep_researcher_tool_config  = dict(
    type="deep_researcher_tool",
    model_id = "gpt-4.1-mini",
    max_depth = 2,
    max_insights = 20,
    time_limit_seconds = 60,
    max_follow_ups = 3,
)

auto_browser_use_tool_config  = dict(
    type="auto_browser_use_tool",
    model_id="gpt-4.1-mini"
)

deep_analyzer_tool_config  = dict(
    type="deep_analyzer_tool",
    analyzer_model_ids = ["gpt-4.1-mini"],
    summarizer_model_id = "gpt-4.1-mini",
)



# Vector Function Calls Tool Config
vector_function_calls_tool_config = dict(
    type="vector_function_calls_tool",
    db_path="vector_db",
    embeddings_model="text-embedding-3-small"
)

mcp_tools_config = {
    "mcpServers" :  {
        "LocalMCP": {
            "command": "python",
            "args": ["src/mcp/server.py"],
            "env": {"DEBUG": "true"}
        },
    }
}

# Vector Database Configuration
vector_db_config = dict(
    # Database path
    db_path="vector_db",
    
    # Text chunking settings
    chunk_size=1000,
    chunk_overlap=200,
    
    # Embedding model
    embeddings_model="text-embedding-3-small",
    
    # Search settings
    default_search_results=5,
    max_search_results=20,
    
    # Supported file types
    supported_extensions=[
        '.pdf', '.txt', '.md', '.csv', '.xlsx', '.xls', 
        '.pptx', '.docx', '.py', '.js', '.ts', '.html', 
        '.css', '.json', '.xml', '.yaml', '.yml'
    ],
    
    # Processing settings
    max_workers=4,
    batch_size=100,
    
    # Index refresh settings
    auto_refresh=True,
    refresh_interval_hours=24,
    
    # Parallel execution settings
    parallel_execution=True,
    async_optimization=True
)

# Interactive Planning Tools Config
interactive_planning_tool_config = dict(
    type="interactive_planning_tool",
)

user_clarification_tool_config = dict(
    type="user_clarification_tool",
)

