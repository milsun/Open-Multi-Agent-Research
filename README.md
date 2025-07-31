# Open Deep Research Agent

> An AI-powered research system that combines web research with local document intelligence through vector database capabilities. The system uses multiple coordinated AI agents to conduct comprehensive research across both web sources and your local documents.

## 🌟 Key Features

| Feature | Description |
|---------|-------------|
| **🔍 Multi-Source Research** | Combines web research with local document analysis |
| **📚 Vector Database** | Intelligent indexing and semantic search of local documents (PDF, DOCX, XLSX, etc.) |
| **🤖 Multi-Agent System** | Coordinated AI agents for planning, research, analysis, and document operations |
| **⚡ Parallel Processing** | Concurrent web research and vector database searches |
| **🖥️ User-Friendly Interface** | GUI directory picker and intuitive menu system |
| **🔧 OpenAI-Compatible API** | Structured function calls for programmatic access |
| **🏠 Local Model Support** | Ollama integration for offline/local model usage |

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+**
- **API keys for providers** (OpenAI, etc.) or **Ollama** for local models

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd DeepResearchAgent
   ```

2. **Run the installation script**
   ```bash
   python install.py
   ```

3. **Configure API keys or Ollama**
   ```bash
   # Edit .env file with your API keys for providers
   # OR install and configure Ollama for local models
   ```

4. **Run the application**
   ```bash
   python main.py
   ```

## 🎯 Usage

When you start the application, you'll see a three-option menu:

1. **Start Research** - Begin research using existing indexed documents and web sources
2. **Index Documents** - Select a directory to index your local documents for search
3. **Exit** - Close the application

### Document Indexing

- **GUI Directory Picker**: Select folders containing your documents
- **Multi-format Support**: PDF, DOCX, XLSX, CSV, TXT, MD, and many other file types
- **Smart Chunking**: Documents are automatically chunked and indexed for semantic search
- **Incremental Updates**: Only new or changed files are re-indexed for efficiency

### Vector Database Features

**📚 Intelligent Document Processing**
- **Multi-format Support**: Handles PDF, DOCX, XLSX, CSV, TXT, MD, and code files
- **Comprehensive Metadata**: Captures file info, timestamps, permissions, and content properties
- **Incremental Updates**: Only re-indexes changed files using file hash detection

**🔍 Advanced Search Capabilities**
- **Semantic Search**: Uses OpenAI embeddings for context-aware document retrieval
- **Relevance Scoring**: Returns results with similarity scores and relevance levels
- **Flexible Queries**: Natural language search across all indexed content
- **Rich Results**: Includes file metadata, chunk information, and content previews

**⚡ Performance Optimizations**
- **Parallel Processing**: Multi-threaded document loading and processing
- **Intelligent Batching**: Dynamic batch sizing to handle API token limits
- **Error Recovery**: Robust error handling with automatic retry mechanisms
- **Memory Efficient**: Optimized for large document collections

### Research Process

- **Multi-Agent Coordination**: The system coordinates multiple AI agents to plan and execute research
- **Hybrid Research**: Combines web search results with relevant local documents
- **Comprehensive Analysis**: Provides comprehensive analysis and synthesis of findings
- **Structured Results**: Returns structured, well-organized research results

### Web Research Capabilities

The system uses advanced web research tools to gather comprehensive information:

**🔍 Firecrawl Search Engine**
- High-quality web search with content extraction
- Configurable result limits and year filtering
- Automatic fallback to multiple search engines
- Fetches full page content for detailed analysis

**🌐 Browser Automation**
- Interactive web browsing and navigation
- Form filling, clicking, and page interaction
- Dynamic content extraction from JavaScript-heavy sites
- PDF viewing and document handling capabilities
- Supports complex multi-step web tasks

## 📁 Supported File Types

| Category | File Types |
|----------|------------|
| **Documents** | PDF, DOCX, TXT, MD |
| **Spreadsheets** | XLSX, XLS, CSV |
| **Presentations** | PPTX |
| **Code** | PY, JS, TS, HTML, CSS, JSON, XML, YAML |

## 🤖 Multi-Agent Architecture

The system uses a sophisticated hierarchical multi-agent architecture for comprehensive research:

### **Agent Hierarchy & Flow**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACE                                   │
│                    (Research Request Input)                                │
└─────────────────────┬───────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SCOPING AGENT                                      │
│              (Clarification & Research Planning)                          │
│  • Analyzes ambiguous requests                                            │
│  • Asks clarifying questions if needed                                    │
│  • Develops comprehensive research strategy                               │
│  • Presents plan for user confirmation                                    │
└─────────────────────┬───────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       PLANNING AGENT                                      │
│                (Strategic Coordination)                                    │
│  • Receives detailed research task                                        │
│  • Creates step-by-step execution plan                                    │
│  • Coordinates all specialized agents                                     │
│  • Manages parallel research activities                                   │
└─────────────────────┬───────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SPECIALIZED AGENTS                                     │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │
│  │   VECTOR AGENT  │  │ DEEP RESEARCHER │  │ DEEP ANALYZER   │            │
│  │                 │  │     AGENT       │  │     AGENT       │            │
│  │ • Document      │  │                 │  │                 │            │
│  │   search &      │  │ • Web search    │  │ • Analysis &    │            │
│  │   retrieval     │  │ • Information   │  │   synthesis     │            │
│  │ • Semantic      │  │   gathering     │  │ • Step-by-step  │            │
│  │   similarity    │  │ • Multi-source  │  │   reasoning     │            │
│  │ • Metadata      │  │   research      │  │ • Problem       │            │
│  │   filtering     │  │ • Content       │  │   decomposition │            │
│  │                 │  │   extraction    │  │                 │            │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘            │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                BROWSER USE AGENT                                   │    │
│  │                                                                     │    │
│  │ • Interactive web navigation                                        │    │
│  │ • Form filling & clicking                                           │    │
│  │ • Dynamic content extraction                                        │    │
│  │ • JavaScript-heavy site handling                                    │    │
│  │ • PDF viewing & document handling                                   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────┬───────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SYNTHESIS                                          │
│              (Combined Research Results)                                  │
│  • Integrates findings from all sources                                  │
│  • Resolves conflicts and contradictions                                 │
│  • Provides comprehensive analysis                                       │
│  • Delivers structured final report                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### **Research Flow Process**

1. **Scoping Phase**: User request → Clarification → Research plan → User confirmation
2. **Planning Phase**: Detailed task → Strategy creation → Agent coordination
3. **Execution Phase**: Parallel research across multiple agents
4. **Synthesis Phase**: Integration of all findings into comprehensive results

### **Agent Specializations**

| Agent | Specialization |
|-------|----------------|
| **Scoping Agent** | Request clarification and research planning |
| **Planning Agent** | Strategic coordination and task decomposition |
| **Vector Agent** | Document search and analysis |
| **Deep Researcher Agent** | Web research and information gathering |
| **Deep Analyzer Agent** | Analysis and synthesis |
| **Browser Use Agent** | Interactive web tasks |

## 🔧 Configuration

The system is configured through `configs/config_main.py` and `configs/base.py`. Key settings include:

| Setting Category | Description |
|------------------|-------------|
| **Model Configurations** | Settings for each agent's AI model (OpenAI, Ollama, etc.) |
| **Vector Database** | Chunk size, embedding model, and search parameters |
| **Web Search** | Search engine settings and result limits |
| **Tool Configurations** | Individual tool parameters and capabilities |

## 🛠️ Development

### Project Structure

```
DeepResearchAgent/
├── main.py                    # Main application entry point
├── configs/                   # Configuration files
├── src/
│   ├── agent/                # AI agent implementations
│   ├── tools/                # Research and processing tools
│   ├── models/               # Model management
│   └── utils/                # Utility functions
├── vector_db/                # Vector database storage
└── workdir/                  # Working directory
```



## 🚨 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| **Missing Dependencies** | Run `python install.py` to install all dependencies |
| **API Key Issues** | Ensure your API keys are set in `.env` (copy from `.env.template`) and check permissions |
| **Local Model Issues** | Install Ollama and ensure local models are available for offline usage |
| **Vector Database Issues** | Index documents first using option 2 in the main menu, check file permissions |
| **GUI Issues** | The system automatically falls back to CLI input if GUI isn't available |


## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests for any improvements.