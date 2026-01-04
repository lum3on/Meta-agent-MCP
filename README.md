# 🤖 Meta Agent MCP Server

<div align="center">

An intelligent **Model Context Protocol (MCP)** server that orchestrates multiple AI agents for complex task solving, combining advanced reasoning algorithms with web research capabilities.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)

</div>

---

## 🏗️ Architecture

![Main Architecture](main%20architecture.png)

The Meta Agent MCP Server uses a **hierarchical multi-agent architecture** where a Meta Orchestrator coordinates specialized agents to handle complex queries:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         META ORCHESTRATOR                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │    Task     │→ │ Dependency  │→ │  Parallel   │→ │   Result    │    │
│  │  Planning   │  │ Resolution  │  │  Execution  │  │  Synthesis  │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
├─────────────────────────────────────────────────────────────────────────┤
│                        SPECIALIST AGENTS                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │ 🔍 RESEARCH     │  │ 🧠 REASONING    │  │ 📊 STRATEGY     │         │
│  │ • Web Crawling  │  │ • Beam Search   │  │ • Decision      │         │
│  │ • Deep Crawl    │  │ • MCTS          │  │   Analysis      │         │
│  │ • Data Extract  │  │ • Thought Trees │  │ • Comparisons   │         │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## ✨ Key Features

### 🎯 Multi-Agent Orchestration
- **Task Decomposition**: Automatically breaks complex queries into agent-specific tasks
- **Dependency Resolution**: Topological sorting for optimal execution order
- **Parallel Execution**: Runs independent tasks concurrently for speed
- **Error Recovery**: Graceful handling of partial failures with retry logic

### 🔍 Web Research Agent
- **Single URL Crawling**: Extract clean markdown from any webpage
- **Deep Crawling**: Follow links up to 5 levels deep, crawl up to 50 pages
- **Structured Data Extraction**: CSS selector-based data extraction for scraping
- **LLM-Friendly Output**: Filters navigation, ads, and non-content elements

### 🧠 Advanced Reasoning Algorithms

#### Beam Search
- Maintains multiple promising reasoning paths simultaneously
- Evaluates and selects the best paths at each depth level
- Best for problems with multiple valid approaches

#### Monte Carlo Tree Search (MCTS)
- Balances exploration of new ideas with exploitation of promising paths
- Uses UCB1 algorithm for intelligent path selection
- Best for complex problems with large solution spaces

### 📊 Strategy Agent
- **Decision Analysis**: Understand key factors, opportunities, and threats
- **Option Comparison**: Multi-criteria evaluation with feasibility, impact, and risk scores
- **Strategy Generation**: Comprehensive plans with action items and success criteria

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11 or higher
- An [OpenRouter API key](https://openrouter.ai/)

### Installation

```bash
# Clone the repository
git clone https://github.com/lum3on/Meta-agent-MCP.git
cd Meta-agent-MCP

# Install dependencies
pip install -e ".[dev]"
```

### Configuration

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Edit `.env` with your API key:

```env
# Required
OPENROUTER_API_KEY=your-openrouter-api-key-here

# Optional: Model Configuration
META_AGENT_MODEL=x-ai/grok-4-fast
REASONING_MODEL=anthropic/claude-3-haiku
STRATEGY_MODEL=anthropic/claude-3.5-sonnet

# Optional: Server Configuration
META_AGENT_HOST=localhost
META_AGENT_PORT=8000
LOG_LEVEL=INFO

# Optional: Transport (stdio, sse, or streamable-http)
TRANSPORT=stdio
```

### Run the Server

```bash
meta-agent-mcp
```

Or with Docker:

```bash
docker-compose up
```

---

## 🛠️ Available MCP Tools

### Web Crawling Tools

| Tool | Description |
|------|-------------|
| `crawl_url` | Crawl a single URL and extract content as clean markdown |
| `deep_crawl` | Multi-page crawling with configurable depth (1-5) and page limits (1-50) |
| `extract_structured_data` | Extract structured data using CSS selectors |

### Reasoning Tools

| Tool | Description |
|------|-------------|
| `beam_search_reason` | Solve problems using Beam Search (configurable beam width 1-10, depth 1-20) |
| `mcts_reason` | Solve problems using MCTS (10-150 simulations, configurable exploration) |
| `get_reasoning_tree` | Visualize the full reasoning tree for a completed session |

### Strategy Tools

| Tool | Description |
|------|-------------|
| `analyze_decision` | Analyze a decision situation and provide strategic insights |
| `compare_options` | Compare multiple options using structured criteria |
| `generate_strategy` | Generate comprehensive strategic recommendations |

### Meta Orchestrator

| Tool | Description |
|------|-------------|
| `meta_agent_query` | Main entry point - coordinates all agents for complex queries |
| `health_check` | Check server health and status |

---

## 💡 Usage Examples

### Research Query
```
"What are the latest developments in AI agents and their architectures?"
```
→ Triggers **Research Agent** for web crawling and information gathering

### Reasoning Query
```
"Walk me through solving this optimization problem step by step"
```
→ Triggers **Reasoning Agent** with Beam Search or MCTS

### Strategy Query
```
"Should I use React or Vue for my new project? Compare the options."
```
→ Triggers **Strategy Agent** for decision analysis

### Combined Query
```
"Research microservices patterns and recommend an architecture for my e-commerce platform"
```
→ Triggers **Meta Orchestrator** coordinating Research + Strategy agents

---

## 🐳 Docker Deployment

```bash
# Build and run
docker-compose up --build

# Run in background
docker-compose up -d
```

---

## 📁 Project Structure

```
meta_agent-MCP/
├── src/meta_agent_mcp/
│   ├── agents/           # Agent implementations
│   │   ├── meta.py       # Meta Orchestrator
│   │   ├── research.py   # Research Agent
│   │   ├── reasoning.py  # Reasoning Agent
│   │   └── strategy.py   # Strategy Agent
│   ├── crawling/         # Web crawling with Crawl4AI
│   ├── models/           # Pydantic data models
│   ├── reasoning/        # Beam Search & MCTS algorithms
│   │   ├── beam_search.py
│   │   ├── mcts.py
│   │   └── thought_tree.py
│   ├── tools/            # MCP tool definitions
│   ├── config.py         # Configuration management
│   ├── server.py         # MCP server entry point
│   └── mcp_instance.py   # FastMCP instance
├── tests/                # Test suite
├── docs-next steps/      # Future roadmap documentation
├── .env.example          # Example environment configuration
├── pyproject.toml        # Python project configuration
├── Dockerfile            # Docker configuration
└── docker-compose.yml    # Docker Compose configuration
```

---

## 🗺️ Roadmap

### 🔬 Phase 1: Deep Reflection Agent (Planned)
Implementation of a Deep Reflection Agent using OODA Loop methodology:

<img width="1484" height="758" alt="reflection-agent" src="https://github.com/user-attachments/assets/88317168-5be0-4c38-8742-dd99369451f9" />

- **Observe**: Capture agent interactions, performance metrics, system state
- **Orient**: Pattern recognition, trend analysis, emergent behavior detection
- **Decide**: Trade-off evaluation, recommendation generation
- **Act**: Configuration optimization, alerts, feedback collection

Key components:
- Hierarchical reflection (tactical, strategic, meta-cognitive)
- SQLite + ChromaDB for persistent memory
- Non-intrusive event-driven integration

### 🔧 Phase 2: Self-Healing Agents (Planned)
Autonomous fault detection, diagnosis, and recovery using MAPE-K loop:

- **Monitor**: Continuous health observation with telemetry
- **Analyze**: AI/ML anomaly detection and root cause diagnosis
- **Plan**: Policy-based recovery strategy selection
- **Execute**: Autonomous reconfiguration and failover
- **Knowledge**: Incident storage for adaptive learning

Design principles:
- Graceful degradation over complete failure
- Progressive recovery escalation
- Defense-in-depth with multiple recovery layers

### 🎯 Future Enhancements
- [ ] Multi-modal support (images, audio, video)
- [ ] Streaming responses for long-running operations
- [ ] Plugin architecture for custom agents
- [ ] Web UI dashboard for monitoring
- [ ] Integration with popular IDEs

---

## 🔧 Configuration Reference

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `OPENROUTER_API_KEY` | (required) | OpenRouter API key |
| `META_AGENT_MODEL` | `x-ai/grok-4-fast` | Model for meta orchestration |
| `REASONING_MODEL` | `anthropic/claude-3-haiku` | Model for reasoning tasks |
| `STRATEGY_MODEL` | `anthropic/claude-3.5-sonnet` | Model for strategy tasks |
| `TRANSPORT` | `stdio` | Transport type: stdio, sse, streamable-http |
| `TRANSPORT_HOST` | `127.0.0.1` | Host for HTTP transports |
| `TRANSPORT_PORT` | `8080` | Port for HTTP transports |
| `LOG_LEVEL` | `INFO` | Logging level |
| `DEFAULT_BEAM_WIDTH` | `3` | Default beam search width (1-10) |
| `DEFAULT_MCTS_SIMULATIONS` | `50` | Default MCTS simulations (1-150) |
| `DEFAULT_CRAWL_TIMEOUT` | `30` | Crawl timeout in seconds (5-120) |

---

## 🧪 Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy src/meta_agent_mcp

# Linting
ruff check src/meta_agent_mcp
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [FastMCP](https://github.com/jlowin/fastmcp) - MCP server framework
- [Pydantic AI](https://ai.pydantic.dev/) - AI agent framework
- [Crawl4AI](https://github.com/unclecode/crawl4ai) - Web crawling
- [OpenRouter](https://openrouter.ai/) - LLM API access

---

<div align="center">
  <sub>Built with ❤️ using the Model Context Protocol</sub>
</div>
