
from dataclasses import dataclass
from typing import Any, Dict, Optional


from src.tools.tools import PipelineTool, Tool, ToolResult

@dataclass
class PreTool:
    name: str
    inputs: Dict[str, str]
    output_type: type
    task: str
    description: str
    repo_id: str





class FinalAnswerTool(Tool):
    name = "final_answer"
    description = "Provides a final answer to the given problem."
    parameters = {
        "type": "object",
        "properties": {
            "answer": {
                "type": "any",
                "description": "The final answer to the problem.",
            },
        },
        "required": ["answer"],
    }
    output_type = "any"

    def forward(self, answer: Any) -> ToolResult:
        result = ToolResult(
            output=answer,
            error=None,
        )
        return result


class UserInputTool(Tool):
    name = "user_input"
    description = "Asks for user's input on a specific question"
    parameters = {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question to ask the user",
            },
        },
        "required": ["question"],
    }
    output_type = "any"

    def forward(self, question):
        user_input = input(f"{question} => Type your answer here:")

        result = ToolResult(
            output=user_input,
            error=None,
        )

        return result


class DuckDuckGoSearchTool(Tool):
    name = "web_search"
    description = """Performs a duckduckgo web search based on your query (think a Google search) then returns the top search results."""

    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to perform.",
            },
            "max_results": {
                "type": "integer",
                "description": "The maximum number of results to return.",
                "default": 10,
                "nullable": True,
            },
        },
        "required": ["query"],
    }
    output_type = "any"

    def __init__(self, max_results=10, **kwargs):
        super().__init__()
        self.max_results = max_results
        try:
            from duckduckgo_search import DDGS
        except ImportError as e:
            raise ImportError(
                "You must install package `duckduckgo_search` to run this tool: for instance run `pip install duckduckgo-search`."
            ) from e
        self.ddgs = DDGS(**kwargs)

    def forward(self, query: str, max_results: Optional[int] = None) -> ToolResult:
        if max_results is None:
            max_results = self.max_results
        results = self.ddgs.text(query, max_results = max_results)
        if len(results) == 0:
            raise Exception("No results found! Try a less restrictive/shorter query.")
        postprocessed_results = [f"[{result['title']}]({result['href']})\n{result['body']}" for result in results]


        result = ToolResult(
            output="## Search Results\n\n" + "\n\n".join(postprocessed_results),
            error=None)

        return result


class GoogleSearchTool(Tool):
    name = "web_search"
    description = """Performs a google web search for your query then returns a string of the top search results."""
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to perform.",
            },
            "filter_year": {
                "type": "integer",
                "description": "Optionally restrict results to a certain year",
                "default": None,
            },
        },
        "required": ["query"],
    }
    output_type = "string"

    def __init__(self, provider: str = "serpapi"):
        super().__init__()
        import os

        self.provider = provider
        if provider == "serpapi":
            self.organic_key = "organic_results"
            api_key_env_name = "SERPAPI_API_KEY"
        else:
            self.organic_key = "organic"
            api_key_env_name = "SERPER_API_KEY"
        self.api_key = os.getenv(api_key_env_name)
        if self.api_key is None:
            raise ValueError(f"Missing API key. Make sure you have '{api_key_env_name}' in your env variables.")

    def forward(self, query: str, filter_year: Optional[int] = None) -> str:
        import requests

        if self.provider == "serpapi":
            params = {
                "q": query,
                "api_key": self.api_key,
                "engine": "google",
                "google_domain": "google.com",
            }
            base_url = "https://serpapi.com/search.json"
        else:
            params = {
                "q": query,
                "api_key": self.api_key,
            }
            base_url = "https://google.serper.dev/search"
        if filter_year is not None:
            params["tbs"] = f"cdr:1,cd_min:01/01/{filter_year},cd_max:12/31/{filter_year}"

        response = requests.get(base_url, params=params)

        if response.status_code == 200:
            results = response.json()
        else:
            raise ValueError(response.json())

        if self.organic_key not in results.keys():
            if filter_year is not None:
                raise Exception(
                    f"No results found for query: '{query}' with filtering on year={filter_year}. Use a less restrictive query or do not filter on year."
                )
            else:
                raise Exception(f"No results found for query: '{query}'. Use a less restrictive query.")
        if len(results[self.organic_key]) == 0:
            year_filter_message = f" with filter year={filter_year}" if filter_year is not None else ""
            return f"No results found for '{query}'{year_filter_message}. Try with a more general query, or remove the year filter."

        web_snippets = []
        if self.organic_key in results:
            for idx, page in enumerate(results[self.organic_key]):
                date_published = ""
                if "date" in page:
                    date_published = "\nDate published: " + page["date"]

                source = ""
                if "source" in page:
                    source = "\nSource: " + page["source"]

                snippet = ""
                if "snippet" in page:
                    snippet = "\n" + page["snippet"]

                redacted_version = f"{idx}. [{page['title']}]({page['link']}){date_published}{source}\n{snippet}"
                web_snippets.append(redacted_version)

        result = ToolResult(
            output="## Search Results\n" + "\n\n".join(web_snippets),
            error=None,
        )

        return result


class VisitWebpageTool(Tool):
    name = "visit_webpage"
    description = (
        "Visits a webpage at the given url and reads its content as a markdown string. Use this to browse webpages."
    )
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The url of the webpage to visit.",
            },
        },
    }
    output_type = "string"

    def __init__(self, max_output_length: int = 40000):
        super().__init__()
        self.max_output_length = max_output_length

    def forward(self, url: str) -> ToolResult:
        try:
            import re

            import requests
            from markdownify import markdownify
            from requests.exceptions import RequestException

            from smolagents.utils import truncate_content
        except ImportError as e:
            raise ImportError(
                "You must install packages `markdownify` and `requests` to run this tool: for instance run `pip install markdownify requests`."
            ) from e
        try:
            # Send a GET request to the URL with a 20-second timeout
            response = requests.get(url, timeout=20)
            response.raise_for_status()  # Raise an exception for bad status codes

            # Convert the HTML content to Markdown
            markdown_content = markdownify(response.text).strip()

            # Remove multiple line breaks
            markdown_content = re.sub(r"\n{3,}", "\n\n", markdown_content)

            res_str = truncate_content(markdown_content, self.max_output_length)

            return ToolResult(
                output=res_str,
                error=None
            )

        except requests.exceptions.Timeout:
            res_str = "The request timed out. Please try again later or check the URL."
            return ToolResult(
                output=None,
                error=res_str,
            )
        except RequestException as e:
            res_str = f"Error fetching the webpage: {str(e)}"
            return ToolResult(
                output=None,
                error=res_str,
            )
        except Exception as e:
            res_str = f"An unexpected error occurred: {str(e)}"
            return ToolResult(
                output=None,
                error=res_str,
            )


class WikipediaSearchTool(Tool):
    """
    WikipediaSearchTool searches Wikipedia and returns a summary or full text of the given topic, along with the page URL.

    Attributes:
        user_agent (str): A custom user-agent string to identify the project. This is required as per Wikipedia API policies, read more here: http://github.com/martin-majlis/Wikipedia-API/blob/master/README.rst
        language (str): The language in which to retrieve Wikipedia articles.
                http://meta.wikimedia.org/wiki/List_of_Wikipedias
        content_type (str): Defines the content to fetch. Can be "summary" for a short summary or "text" for the full article.
        extract_format (str): Defines the output format. Can be `"WIKI"` or `"HTML"`.

    Example:
        >>> from smolagents import ToolCallingAgent, InferenceClientModel, WikipediaSearchTool
        >>> agent = ToolCallingAgent(
        >>>     tools=[
        >>>            WikipediaSearchTool(
        >>>                user_agent="MyResearchBot (myemail@example.com)",
        >>>                language="en",
        >>>                content_type="summary",  # or "text"
        >>>                extract_format="WIKI",
        >>>            )
        >>>        ],
        >>>     model=InferenceClientModel(),
        >>> )
        >>> agent.run("Python_(programming_language)")
    """

    name = "wikipedia_search"
    description = "Searches Wikipedia and returns a summary or full text of the given topic, along with the page URL."
    inputs = {
        "query": {
            "type": "string",
            "description": "The topic to search on Wikipedia.",
        }
    }
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The topic to search on Wikipedia.",
            },
        },
        "required": ["query"],
    }
    output_type = "string"

    def __init__(
        self,
        user_agent: str = "Smolagents (myemail@example.com)",
        language: str = "en",
        content_type: str = "text",
        extract_format: str = "WIKI",
    ):
        super().__init__()
        try:
            import wikipediaapi
        except ImportError as e:
            raise ImportError(
                "You must install `wikipedia-api` to run this tool: for instance run `pip install wikipedia-api`"
            ) from e
        if not user_agent:
            raise ValueError("User-agent is required. Provide a meaningful identifier for your project.")

        self.user_agent = user_agent
        self.language = language
        self.content_type = content_type

        # Map string format to wikipediaapi.ExtractFormat
        extract_format_map = {
            "WIKI": wikipediaapi.ExtractFormat.WIKI,
            "HTML": wikipediaapi.ExtractFormat.HTML,
        }

        if extract_format not in extract_format_map:
            raise ValueError("Invalid extract_format. Choose between 'WIKI' or 'HTML'.")

        self.extract_format = extract_format_map[extract_format]

        self.wiki = wikipediaapi.Wikipedia(
            user_agent=self.user_agent, language=self.language, extract_format=self.extract_format
        )

    def forward(self, query: str) -> ToolResult:
        try:
            page = self.wiki.page(query)

            if not page.exists():
                return f"No Wikipedia page found for '{query}'. Try a different query."

            title = page.title
            url = page.fullurl

            if self.content_type == "summary":
                text = page.summary
            elif self.content_type == "text":
                text = page.text
            else:
                return "⚠️ Invalid `content_type`. Use either 'summary' or 'text'."

            res_str = f"✅ **Wikipedia Page:** {title}\n\n**Content:** {text}\n\n🔗 **Read more:** {url}"
            return ToolResult(
                output=res_str,
                error=None,
            )

        except Exception as e:
            res_str = f"Error fetching Wikipedia summary: {str(e)}"
            return ToolResult(
                output=None,
                error=res_str,
            )


class SpeechToTextTool(PipelineTool):
    default_checkpoint = "openai/whisper-large-v3-turbo"
    description = "This is a tool that transcribes an audio into text. It returns the transcribed text."
    name = "transcriber"
    parameters = {
        "type": "object",
        "properties": {
            "audio": {
                "type": "audio",
                "description": "The audio to transcribe. Can be a local path, an url, or a tensor.",
            },
        },
        "required": ["audio"],
    }
    output_type = "string"

    def __new__(cls, *args, **kwargs):
        from transformers.models.whisper import (
            WhisperForConditionalGeneration,
            WhisperProcessor,
        )

        cls.pre_processor_class = WhisperProcessor
        cls.model_class = WhisperForConditionalGeneration
        return super().__new__(cls, *args, **kwargs)

    def encode(self, audio):
        from src.utils.agent_types import AgentAudio

        audio = AgentAudio(audio).to_raw()
        return self.pre_processor(audio, return_tensors="pt")

    def forward(self, inputs):
        return self.model.generate(inputs["input_features"])

    def decode(self, outputs):
        return self.pre_processor.batch_decode(outputs, skip_special_tokens=True)[0]


TOOL_MAPPING = {
    tool_class.name: tool_class
    for tool_class in [
        DuckDuckGoSearchTool,
        VisitWebpageTool,
    ]
}

__all__ = [
    "FinalAnswerTool",
    "UserInputTool",
    "DuckDuckGoSearchTool",
    "GoogleSearchTool",
    "VisitWebpageTool",
    "WikipediaSearchTool",
    "SpeechToTextTool",
]
