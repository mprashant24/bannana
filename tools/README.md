# Embedding & Semantic Search Tool (`embedding_tool`)

**Module**: [`tools/embedding_tool.py`](embedding_tool.py)
**Task**: `TASK-002`
**Class**: `EmbeddingSemanticSearchTool` (inherits `langchain_core.tools.BaseTool`)

Builds a FAISS-backed semantic index over one or more repositories and exposes semantic
code search, technology/route inventory, and blast-radius dependency analysis to the Deep
Agent — so steps like Inventory Generation, Scope Detection, and Targeted Analysis can query
the codebase without loading raw source files into the prompt.

---

## ⚡ Actions

The tool is driven by a single `action` parameter (see `EmbeddingToolInput`):

| Action | Required args | Description |
| :--- | :--- | :--- |
| `index` | `repo_paths`, `mode` (`baseline` or `diff`) | Builds or refreshes the vector index. |
| `search` | `query`, optional `top_k` | Semantic similarity search over indexed code chunks. |
| `get_inventory` | `repo_paths` | Technology, route, and high-risk module inventory (markdown). |
| `get_blast_radius` | `changed_files` | Upstream/downstream dependency impact for a set of changed files. |

### `index` — `mode="baseline"`
Scans every path in `repo_paths`, chunks source files with language-aware splitters, embeds
the chunks, extracts the route inventory and technology stack, builds the import dependency
graph, and persists everything to `context_dir`.

### `index` — `mode="diff"`
Loads the persisted index/graph, resolves `changed_files` to indexed nodes, walks the
dependency graph to find blast-radius-impacted files, evicts their stale vector chunks, and
re-embeds current file contents in place — without re-scanning the whole repo.

### `search`
Runs a FAISS similarity search over the persisted index and returns the top `top_k` chunks
with repo, file path, chunk index, distance score, and any risk tags.

### `get_inventory`
Re-scans `repo_paths` and returns a markdown report with three sections: **Technology
Inventory** (languages/frameworks per repo), **Route Inventory** (HTTP method, path, handler
file, repo), and **High-Risk Modules** (files flagged for auth/authz/crypto/injection
indicators). Also refreshes the persisted route/tech/dependency state as a side effect.

### `get_blast_radius`
Given `changed_files`, returns directly impacted callers, transitively impacted callers, and
upstream dependencies, using the persisted import graph. Requires a prior baseline `index`.

---

## 📥 Input Schema (`EmbeddingToolInput`)

| Field | Type | Default | Notes |
| :--- | :--- | :--- | :--- |
| `action` | `str` | — | `index` \| `search` \| `get_inventory` \| `get_blast_radius` |
| `mode` | `str` | `"baseline"` | Only used by `action="index"`: `baseline` or `diff` |
| `query` | `str` | `None` | Required for `search` |
| `repo_paths` | `list[str]` | `["repo"]` | One or more repo root directories (multi-repo supported) |
| `changed_files` | `list[str]` | `None` | Required for `diff` mode and `get_blast_radius`; paths relative to a repo root |
| `top_k` | `int` | `5` | Number of results for `search` |

---

## 💾 Persisted Context Layout

Each indexed repo gets its **own top-level folder named after it** (its directory name, e.g.
`vtm`), so multiple repos/apps can be indexed and committed side by side without one
overwriting another. Everything lives under the tool's `context_dir` (default `output/`):

```
output/
├── manifest.json                          # repo_alias -> absolute source path
├── vtm/                                   # <- top-level folder named after the repo
│   └── context/embeddings/
│       ├── faiss_index/                   # FAISS.save_local() output (index.faiss, index.pkl)
│       ├── metadata_store.json            # chunk_id -> {repo, path, language, chunk_index, risk_tags}
│       ├── blast_radius_graph.json        # node_id -> {repo, path, imports, imported_by, risk_tags}
│       ├── route_inventory.json           # [{repo, path, method, file, line, source}, ...]
│       ├── tech_inventory.json            # {path, languages, frameworks}
│       └── file_hashes.json               # node_id -> sha256(content), for change tracking
└── another-app/
    └── context/embeddings/...
```

`repo_alias` defaults to the repo directory's name (`Path(repo_path).name`) and is recorded in
`manifest.json` the first time a repo is indexed/inventoried, so the same alias is reused on
every later `index`/`diff`/`search`/`get_blast_radius` call for that path. If two different
repo paths would produce the same folder name, the second gets a short hash suffix to avoid
collisions. `node_id` = `"{repo_alias}::{relative/posix/path}"`.

`search` and `get_blast_radius` operate across **all** persisted repo folders when
`repo_paths` doesn't resolve to a specific known repo (the default), giving cross-repo
querying; pass an explicit `repo_paths` to scope a call to one or more specific repos.

---

## 🧠 Embeddings Backend

By default the tool uses `DeterministicHashingEmbeddings` — an offline, dependency-free
feature-hashing bag-of-words embedder. It requires no network access or model download, which
keeps indexing/search fast and fully deterministic for tests and local runs.

To use a production embeddings provider (e.g. Bedrock, HuggingFace), inject it at
construction time:

```python
from langchain_aws import BedrockEmbeddings
from tools.embedding_tool import EmbeddingSemanticSearchTool

tool = EmbeddingSemanticSearchTool(embeddings_model=BedrockEmbeddings(model_id="amazon.titan-embed-text-v2:0"))
```

If `embeddings_model` is left unset, the hashing backend is used with `embed_dimensions`
(default `384`).

---

## 🧩 Route & Framework Detection

- **Python decorators**: Flask/FastAPI-style `@app.route(...)`, `@router.get(...)`, etc.
  (including `methods=[...]` on `@app.route`).
- **Django**: `path(...)`, `re_path(...)`, `url(...)` calls in `urls.py`.
- **Express**: `app.get('/x', ...)`, `router.post("/x", ...)`.
- **Spring**: `@GetMapping`, `@PostMapping`, `@RequestMapping`, etc.
- **Frameworks**: detected via import/marker strings (`flask`, `fastapi`, `django`,
  `express`, `spring`) and `package.json` dependencies.

## 🕸️ Blast Radius / Dependency Graph

Import resolution is AST-based and implemented for **Python only** (absolute and relative
imports, including `from pkg import submodule` style). Other supported languages
(JS/TS/Java/Go) are indexed, route-scanned, and risk-tagged, but are not currently wired into
the dependency graph — `imports`/`imported_by` will be empty for those nodes.

---

## 🚩 High-Risk Module Tagging

Files are tagged with one or more categories based on keyword/pattern matches against their
path and content:

- `authentication` — login, password, jwt, session, token, oauth
- `authorization` — permission, role, access_control, login_required
- `cryptographic` — hashlib, encrypt/decrypt, cipher, md5, sha1
- `injection` — `cursor.execute`, `os.system`, `subprocess.`, `eval(`, `exec(`, `pickle.loads`, `yaml.load(`

---

## 🖥️ Usage

### As a LangChain tool
```python
from tools.embedding_tool import EmbeddingSemanticSearchTool

tool = EmbeddingSemanticSearchTool(context_dir="output")  # default; each repo -> output/<repo_alias>/

tool.invoke({"action": "index", "mode": "baseline", "repo_paths": ["repo/vtm"]})
tool.invoke({"action": "search", "query": "JWT verification", "top_k": 5})
tool.invoke({"action": "get_inventory", "repo_paths": ["repo/vtm"]})
tool.invoke({"action": "get_blast_radius", "changed_files": ["taskManager/views.py"]})
```

### Diff mode (incremental refresh)
```python
tool.invoke({
    "action": "index",
    "mode": "diff",
    "repo_paths": ["repo/vtm"],
    "changed_files": ["taskManager/views.py", "taskManager/models.py"],
})
```

---

## ✅ Testing

```bash
pytest tests/test_embedding_tool.py -v
```

Tests run entirely offline against the fixture repo at `tests/fixtures/sample_repo/`
(a small Flask-style app: `crypto.py` → `auth_service.py` → `login.py` → `app.py`) and cover:
tool metadata/schema, baseline indexing, invalid-mode handling, inventory generation, blast
radius (including transitive impact and the "no index yet" error path), semantic search
(including missing-query/missing-index errors), unknown actions, and diff-mode re-embedding.
