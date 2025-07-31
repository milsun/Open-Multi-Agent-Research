_base_ = './base.py'

# General Config
tag = "main"
concurrency = 1
workdir = "workdir"
log_path = "log.txt"
save_path = "dra.jsonl"
use_local_proxy = False

use_hierarchical_agent = True


vector_agent_config = dict(
    type="vector_agent",
    name="vector_agent",
    model_id="gpt-4.1-mini",
    description="Intelligent vector search agent for document retrieval and analysis.",
    max_steps=10,
    template_path="src/agent/vector_agent/prompts/vector_agent.yaml",
    provide_run_summary=True,
    tools=["vector_search_tool"],
)

deep_researcher_agent_config = dict(
    type="deep_researcher_agent",
    name="deep_researcher_agent",
    model_id="gpt-4.1-mini",
    description="An advanced research agent that conducts comprehensive web searches and information gathering.",
    max_steps=3,
    template_path="src/agent/deep_researcher_agent/prompts/deep_researcher_agent.yaml",
    provide_run_summary=True,
    tools=["deep_researcher_tool"],
)

deep_analyzer_agent_config = dict(
    type="deep_analyzer_agent",
    name="deep_analyzer_agent",
    model_id="gpt-4.1-mini",
    description="A specialized analysis agent that performs methodical, step-by-step problem analysis.",
    max_steps=3,
    template_path="src/agent/deep_analyzer_agent/prompts/deep_analyzer_agent.yaml",
    provide_run_summary=True,
    tools=["deep_analyzer_tool"],
)

browser_use_agent_config = dict(
    type="browser_use_agent",
    name="browser_use_agent",
    model_id="gpt-4.1-mini",
    description="An intelligent browser agent that navigates web pages and performs interactive web tasks.",
    max_steps=5,
    template_path="src/agent/browser_use_agent/prompts/browser_use_agent.yaml",
    provide_run_summary=True,
    tools=["auto_browser_use_tool"],
)

planning_agent_config = dict(
    type="planning_agent",
    name="planning_agent",
    model_id="gpt-4.1-mini",
    description = "A planning agent that can plan the steps to complete the task.",
    max_steps = 20,
    template_path = "src/agent/planning_agent/prompts/planning_agent.yaml",
    provide_run_summary = True,
    tools = ["planning_tool"],
    managed_agents = ["deep_analyzer_agent", "browser_use_agent", "deep_researcher_agent", "vector_agent"]
)

# Scoping Agent Config (first-step agent for clarification and planning)
scoping_agent_config = dict(
    type="scoping_agent",
    name="scoping_agent",
    model_id="gpt-4.1-mini",
    description="An interactive scoping agent that clarifies research requests and produces a research plan for confirmation.",
    max_steps=10,
    template_path="src/agent/scoping_agent/prompts/scoping_agent.yaml",
    provide_run_summary=True,
    tools=["interactive_planning_tool", "user_clarification_tool"],
    managed_agents=["planning_agent", "deep_analyzer_agent", "browser_use_agent", "deep_researcher_agent", "vector_agent"] 
)

# The primary agent to run in this configuration.
agent_config = scoping_agent_config