# System Design Specification: TASK-002 — Embedding & Semantic Search Tool (`embedding_tool`)

**Module**: `tools/embedding_tool.py`  
**Owner**: Prashant  
**Task ID**: `TASK-002`  
**Framework Target**: LangChain `BaseTool` (`langchain_core.tools.BaseTool`) & Pydantic `BaseModel`  
**Target Architecture**: Baseline and Diff Execution Modes with Semantic Indexing & Blast Radius Analysis  

---

## 1. Executive Summary & Purpose

The **Embedding & Semantic Search Tool** (`embedding_tool`) provides dense vector representation, semantic search capabilities, and dependency-aware inventory discovery for the Deep Agent security framework. 

Built as a LangChain custom tool inheriting from `langchain_core.tools.BaseTool` (following the architectural pattern of `owasp_cheatsheet_tool.py`), it integrates seamlessly into the DeepAgent toolbelt. It allows Deep Agent steps (Inventory Generation, Scope Detection, Targeted Analysis) to query technology attributes, route inventories, security risk indicators, and blast radius without clogging prompt contexts with raw source files.

---

## 2. Key System Requirements

1. **LangChain `BaseTool` Standard**:
   - Inherit from `langchain_core.tools.BaseTool`.
   - Define tool `name`, `description`, and Pydantic `args_schema` using `pydantic.BaseModel` & `Field`.
   - Implement `_run(self, ...)` with typing and `CallbackManagerForToolRun` support.
2. **Dual Execution Modes**:
   - **Baseline Mode**: Full-repository code indexing, vector store generation (FAISS), and multi-repo/cross-repo semantic search setup.
   - **Diff Mode**: Loads saved index state and incrementally refreshes vector embeddings for changed files and their dependent "blast radius" scope.
3. **Inventory & Semantic Attributes**:
   - Multi-repo indexing and cross-repo querying.
   - Blast radius calculation (know what breaks before touching code).
   - Route inventory extraction (HTTP endpoints, methods, handlers, and repos).
   - Security and technology attribute querying across indexed codebases.
4. **Unit Testing**:
   - Comprehensive unit test suite (`unittest` / `pytest`) validating Pydantic schema parsing, tool invocation (`_run`), baseline indexing, diff refresh, and semantic search queries.

---

## 3. High-Level Architecture & Workflow

```
                                ┌───────────────────────────┐
                                │ Deep Agent / Step Callers │
                                └─────────────┬─────────────┘
                                              │
                                              ▼
                        ┌───────────────────────────────────────────┐
                        │      EmbeddingSemanticSearchTool          │
                        │      (inherits langchain BaseTool)        │
                        └─────────────┬───────────────┬─────────────┘
                                      │               │
                 ┌────────────────────┘               └────────────────────┐
                 ▼                                                         ▼
    ┌─────────────────────────┐                               ┌─────────────────────────┐
    │   Action: 'index'       │                               │ Action: 'search' /      │
    │   Mode: 'baseline'/'diff'│                               │ 'inventory' / 'blast'   │
    ├─────────────────────────┤                               ├─────────────────────────┤
    │ 1. Full/Incremental Scan│                               │ 1. Vector Search (FAISS)│
    │ 2. Extract AST & Routes │                               │ 2. Route Registry Look  │
    │ 3. Build Blast Radius   │                               │ 3. Return Semantic Code │
    │ 4. Persist Vector Store │                               │    Snippets & Attributes│
    └────────────┬────────────┘                               └────────────┬────────────┘
                 │                                                         │
                 └────────────────────────────┬────────────────────────────┘
                                              │
                                              ▼
                               ┌─────────────────────────────┐
                               │     Persisted Context Store │
                               │  - faiss_index.bin          │
                               │  - metadata_store.json      │
                               │  - blast_radius_graph.json  │
                               └─────────────────────────────┘
```

---

## 4. Class Design & LangChain BaseTool Schema

Following the pattern established in `owasp_cheatsheet_tool.py`, the tool uses Pydantic input models and `BaseTool`.

### 4.1. Input Schema Definition (`EmbeddingToolInput`)

```python
from typing import Optional, List, Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from langchain_core.callbacks.manager import CallbackManagerForToolRun


class EmbeddingToolInput(BaseModel):
    action: str = Field(
        description="The tool action to perform: 'index' (build/refresh index), 'search' (semantic search), 'get_inventory' (tech/route inventory), or 'get_blast_radius' (dependency impact analysis)."
    )
    mode: Optional[str] = Field(
        default="baseline",
        description="Execution mode when action is 'index': 'baseline' (full repo scan) or 'diff' (refresh changed files)."
    )
    query: Optional[str] = Field(
        default=None,
        description="Semantic search query or risk attribute string (e.g., 'JWT verification', 'SQL execution', 'authentication endpoints')."
    )
    repo_paths: Optional[List[str]] = Field(
        default_factory=lambda: ["repo"],
        description="List of repository directory paths for multi-repo or single-repo indexing/queries."
    )
    changed_files: Optional[List[str]] = Field(
        default=None,
        description="List of added/modified/deleted file paths when mode is 'diff'."
    )
    top_k: Optional[int] = Field(
        default=5,
        description="Number of top relevant semantic code snippets to return during search."
    )
```

---

### 4.2. LangChain Tool Class Implementation Structure (`EmbeddingSemanticSearchTool`)

```python
class EmbeddingSemanticSearchTool(BaseTool):
    name: str = "embedding_semantic_search"
    description: str = (
        "Indexes repositories and performs semantic search over codebase vectors, technology attributes, "
        "route inventories, and blast radius dependency graphs for security reviews."
    )
    args_schema: Type[EmbeddingToolInput] = EmbeddingToolInput

    context_dir: str = ".deepagent_context/embeddings"

    def _run(
        self,
        action: str,
        mode: Optional[str] = "baseline",
        query: Optional[str] = None,
        repo_paths: Optional[List[str]] = None,
        changed_files: Optional[List[str]] = None,
        top_k: Optional[int] = 5,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """
        Main tool execution entry point invoked by LangChain / DeepAgent.
        """
        action = action.strip().lower()
        repo_paths = repo_paths or ["repo"]

        if action == "index":
            if mode.lower() == "baseline":
                return self._build_baseline_index(repo_paths)
            elif mode.lower() == "diff":
                return self._refresh_diff_index(repo_paths, changed_files or [])
            else:
                return f"[ERROR] Invalid mode '{mode}'. Must be 'baseline' or 'diff'."

        elif action == "search":
            if not query:
                return "[ERROR] Query parameter is required for 'search' action."
            return self._perform_semantic_search(query, top_k)

        elif action == "get_inventory":
            return self._generate_inventory(repo_paths)

        elif action == "get_blast_radius":
            if not changed_files:
                return "[ERROR] changed_files parameter is required for 'get_blast_radius' action."
            return self._calculate_blast_radius(changed_files)

        else:
            return f"[ERROR] Unknown action '{action}'. Supported actions: 'index', 'search', 'get_inventory', 'get_blast_radius'."
```

---

## 5. Detailed Operational Logic

### 5.1. Baseline Mode (`_build_baseline_index`)
- Scans all specified `repo_paths` (supports multi-repo indexing).
- Extracts AST information (import graphs, class/method declarations, HTTP routes).
- Chunks source code using syntax-aware splitters and embeds chunks into a FAISS vector store.
- Extracts Route Inventory across all repositories (e.g. `@app.route`, FastAPI, Express, Spring controllers).
- Builds and saves the **Blast Radius Dependency Graph** (adjacency list of module imports/calls).
- Persists FAISS binary index and metadata in `.deepagent_context/embeddings/`.

### 5.2. Diff Mode (`_refresh_diff_index`)
- Loads saved index, route inventory, and blast radius graph from `.deepagent_context/embeddings/`.
- Accepts `changed_files` list from `git_ops_tool`.
- Calculates dependent files impacted by the changes via the dependency graph.
- Evicts obsolete vector chunks for changed and blast-radius affected files.
- Re-embeds modified files and updates route registry and vector store in place.

### 5.3. Inventory Output Format (`_generate_inventory`)
Generates structured markdown/JSON summarizing:
1. **Multi-Repo Technology Inventory**: Frameworks, languages, dependencies across indexed repos.
2. **Route Inventory**: HTTP method, route path, controller handler, file path, and repository association.
3. **High-Risk Modules**: Flagged authentication, authorization, cryptographic, and injection surface files.

### 5.4. Blast Radius Output (`_calculate_blast_radius`)
Traces upstream and downstream dependencies for modified files:
- *Input*: `['repo/services/auth.py']`
- *Blast Radius Output*: Lists directly changed files along with all dependent caller modules (e.g. `repo/controllers/login.py`, `repo/api/router.py`).

---

## 6. Unit Testing Strategy (`tests/test_embedding_tool.py`)

Using standard Python `unittest` framework to test the `BaseTool` implementation:

```python
import unittest
from tools.embedding_tool import EmbeddingSemanticSearchTool, EmbeddingToolInput


class TestEmbeddingSemanticSearchTool(unittest.TestCase):

    def setUp(self):
        self.tool = EmbeddingSemanticSearchTool()

    def test_tool_metadata(self):
        """Verify tool name, description, and schema inheritance."""
        self.assertEqual(self.tool.name, "embedding_semantic_search")
        self.assertEqual(self.tool.args_schema, EmbeddingToolInput)

    def test_baseline_index_action(self):
        """Test baseline indexing action execution."""
        result = self.tool._run(
            action="index",
            mode="baseline",
            repo_paths=["tests/fixtures/sample_repo"]
        )
        self.assertIn("Successfully indexed", result)

    def test_get_inventory_action(self):
        """Test route inventory and technology extraction."""
        result = self.tool._run(
            action="get_inventory",
            repo_paths=["tests/fixtures/sample_repo"]
        )
        self.assertIn("Route Inventory", result)

    def test_blast_radius_action(self):
        """Test blast radius calculation action."""
        result = self.tool._run(
            action="get_blast_radius",
            changed_files=["src/auth.py"]
        )
        self.assertIn("Blast Radius", result)

    def test_semantic_search_action(self):
        """Test semantic code snippet retrieval."""
        result = self.tool._run(
            action="search",
            query="SQL query execution",
            top_k=3
        )
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
```


    def test_blast_radius_calculation(self):
        """Verify dependency graph returns correct impacted file list."""
        tool = EmbeddingTool(mode='baseline', repo_paths=['tests/fixtures/sample_repo'])
        tool.initialize()
        
        blast_radius = tool.get_blast_radius(['src/utils/crypto.py'])
        self.assertIn('src/services/auth_service.py', blast_radius)

    def test_semantic_query_attributes(self):
        """Verify vector similarity query returns relevant code chunks."""
        tool = EmbeddingTool(mode='baseline', repo_paths=['tests/fixtures/sample_repo'])
        tool.initialize()
        
        results = tool.query_security_attributes('SQL query execution')
        self.assertGreater(len(results), 0)

if __name__ == '__main__':
    unittest.main()
```
