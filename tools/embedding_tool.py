"""Embedding & Semantic Search Tool (TASK-002).

LangChain `BaseTool` that builds a FAISS-backed semantic index over one or
more repositories and exposes semantic search, technology/route inventory,
and blast-radius dependency analysis to the Deep Agent.

Notes on scope:
- Embeddings default to an offline, deterministic hashing-based backend so
  the tool works without network access or a downloaded model. A real
  provider (Bedrock, HuggingFace, ...) can be injected via the
  `embeddings_model` field for production-quality recall.
- Blast-radius dependency resolution is implemented via Python AST import
  analysis. Other languages are indexed, route-scanned, and risk-tagged,
  but are not currently wired into the import dependency graph.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Type

from pydantic import BaseModel, Field, PrivateAttr
from langchain_core.callbacks.manager import CallbackManagerForToolRun
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.tools import BaseTool
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LANGUAGE_BY_EXTENSION: Dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
}

SPLITTER_LANGUAGE: Dict[str, Language] = {
    "python": Language.PYTHON,
    "javascript": Language.JS,
    "typescript": Language.TS,
    "java": Language.JAVA,
    "go": Language.GO,
}

IGNORED_DIR_NAMES = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", "dist", "build",
    ".deepagent_context", "migrations", ".mypy_cache", ".pytest_cache", "static",
}

RISK_KEYWORD_PATTERNS: Dict[str, List[str]] = {
    "authentication": [r"login", r"authenticate", r"password", r"jwt", r"\bsession\b", r"\btoken\b", r"oauth"],
    "authorization": [r"permission", r"is_admin", r"\brole\b", r"access_control", r"authorize", r"login_required"],
    "cryptographic": [r"hashlib", r"encrypt", r"decrypt", r"\bcrypto\b", r"\bcipher\b", r"\bmd5\b", r"\bsha1\b"],
    "injection": [r"cursor\.execute", r"\.execute\(", r"os\.system", r"subprocess\.", r"eval\(", r"exec\(",
                  r"pickle\.loads", r"yaml\.load\("],
}

_METHODS_KW_RE = re.compile(r'methods\s*=\s*\[([^\]]*)\]', re.IGNORECASE)

ROUTE_PATTERNS = {
    "python-decorator": re.compile(
        r'@\w+\.(route|get|post|put|delete|patch|options|head)\(\s*[\'"](?P<path>[^\'"]+)[\'"](?P<rest>[^)]*)\)',
        re.IGNORECASE,
    ),
    "django-url": re.compile(r'\b(?:path|re_path|url)\(\s*[\'"](?P<path>[^\'"]*)[\'"]'),
    "express": re.compile(r'\b\w+\.(get|post|put|delete|patch|use)\(\s*[\'"](?P<path>/[^\'"]*)[\'"]', re.IGNORECASE),
    "spring": re.compile(r'@(?:Get|Post|Put|Delete|Patch|Request)Mapping\(\s*(?:value\s*=\s*)?[\'"](?P<path>[^\'"]+)[\'"]'),
}

FRAMEWORK_MARKERS: Dict[str, List[str]] = {
    "flask": ["from flask", "import flask", "Flask(__name__)"],
    "fastapi": ["from fastapi", "import fastapi", "FastAPI("],
    "django": ["from django", "import django", "DJANGO_SETTINGS_MODULE"],
    "express": ["require('express')", 'require("express")', "from 'express'", 'from "express"'],
    "spring": ["@RestController", "@SpringBootApplication", "org.springframework"],
}


# ---------------------------------------------------------------------------
# Offline deterministic embeddings backend
# ---------------------------------------------------------------------------

class DeterministicHashingEmbeddings(Embeddings):
    """Dependency-free embeddings using a feature-hashing bag-of-words vector.

    Deterministic and offline so the tool is usable/testable without network
    access. Swap in a real provider via `EmbeddingSemanticSearchTool.embeddings_model`.
    """

    _TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|[0-9]+")

    def __init__(self, dimensions: int = 384):
        self.dimensions = dimensions

    def _tokenize(self, text: str) -> List[str]:
        tokens = self._TOKEN_RE.findall(text)
        expanded: List[str] = []
        for tok in tokens:
            expanded.append(tok.lower())
            for part in tok.split("_"):
                if part and part.lower() != tok.lower():
                    expanded.append(part.lower())
        return expanded

    def _embed(self, text: str) -> List[float]:
        vec = [0.0] * self.dimensions
        tokens = self._tokenize(text)
        for tok in tokens:
            digest = hashlib.sha256(tok.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[idx] += sign
        norm = sum(v * v for v in vec) ** 0.5
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed(text)


# ---------------------------------------------------------------------------
# Input schema
# ---------------------------------------------------------------------------

class EmbeddingToolInput(BaseModel):
    action: str = Field(
        description="The tool action to perform: 'index' (build/refresh index), 'search' (semantic search), "
                    "'get_inventory' (tech/route inventory), or 'get_blast_radius' (dependency impact analysis)."
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


# ---------------------------------------------------------------------------
# Tool implementation
# ---------------------------------------------------------------------------

class EmbeddingSemanticSearchTool(BaseTool):
    name: str = "embedding_semantic_search"
    description: str = (
        "Indexes repositories and performs semantic search over codebase vectors, technology attributes, "
        "route inventories, and blast radius dependency graphs for security reviews."
    )
    args_schema: Type[EmbeddingToolInput] = EmbeddingToolInput

    context_dir: str = ".deepagent_context/embeddings"
    embed_dimensions: int = 384
    chunk_size: int = 800
    chunk_overlap: int = 100
    embeddings_model: Any = None

    _vector_store: Optional[FAISS] = PrivateAttr(default=None)
    _metadata_store: Dict[str, Any] = PrivateAttr(default_factory=dict)
    _dependency_graph: Dict[str, Any] = PrivateAttr(default_factory=dict)
    _route_inventory: List[Dict[str, Any]] = PrivateAttr(default_factory=list)
    _tech_inventory: Dict[str, Any] = PrivateAttr(default_factory=dict)
    _file_hashes: Dict[str, str] = PrivateAttr(default_factory=dict)

    # -- LangChain entry point ----------------------------------------------

    def _run(
        self,
        action: str,
        mode: Optional[str] = "baseline",
        query: Optional[str] = None,
        repo_paths: Optional[List[str]] = None,
        changed_files: Optional[List[str]] = None,
        top_k: Optional[int] = 5,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        action = (action or "").strip().lower()
        repo_paths = repo_paths or ["repo"]
        mode = (mode or "baseline").strip().lower()
        top_k = top_k or 5

        if action == "index":
            if mode == "baseline":
                return self._build_baseline_index(repo_paths)
            elif mode == "diff":
                return self._refresh_diff_index(repo_paths, changed_files or [])
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

    # -- Embeddings backend ---------------------------------------------------

    def _get_embeddings(self) -> Embeddings:
        if self.embeddings_model is not None:
            return self.embeddings_model
        return DeterministicHashingEmbeddings(dimensions=self.embed_dimensions)

    # -- Context persistence paths --------------------------------------------

    def _context_path(self) -> Path:
        return Path(self.context_dir)

    def _index_dir(self) -> Path:
        return self._context_path() / "faiss_index"

    def _metadata_path(self) -> Path:
        return self._context_path() / "metadata_store.json"

    def _blast_graph_path(self) -> Path:
        return self._context_path() / "blast_radius_graph.json"

    def _route_inventory_path(self) -> Path:
        return self._context_path() / "route_inventory.json"

    def _tech_inventory_path(self) -> Path:
        return self._context_path() / "tech_inventory.json"

    def _file_hashes_path(self) -> Path:
        return self._context_path() / "file_hashes.json"

    @staticmethod
    def _persist_json(path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, default=list), encoding="utf-8")

    def _load_context(self, require_index: bool = False) -> Optional[str]:
        if self._vector_store is None and self._index_dir().exists():
            try:
                self._vector_store = FAISS.load_local(
                    str(self._index_dir()), self._get_embeddings(), allow_dangerous_deserialization=True
                )
            except Exception as exc:
                if require_index:
                    return f"[ERROR] Failed to load persisted FAISS index: {exc}"
        if not self._metadata_store and self._metadata_path().exists():
            self._metadata_store = json.loads(self._metadata_path().read_text(encoding="utf-8"))
        if not self._dependency_graph and self._blast_graph_path().exists():
            self._dependency_graph = json.loads(self._blast_graph_path().read_text(encoding="utf-8"))
        if not self._route_inventory and self._route_inventory_path().exists():
            self._route_inventory = json.loads(self._route_inventory_path().read_text(encoding="utf-8"))
        if not self._tech_inventory and self._tech_inventory_path().exists():
            self._tech_inventory = json.loads(self._tech_inventory_path().read_text(encoding="utf-8"))
        if not self._file_hashes and self._file_hashes_path().exists():
            self._file_hashes = json.loads(self._file_hashes_path().read_text(encoding="utf-8"))

        if require_index and self._vector_store is None:
            return "[ERROR] No persisted index found. Run action='index' with mode='baseline' first."
        return None

    # -- Repo scanning ---------------------------------------------------------

    @staticmethod
    def _iter_source_files(repo_root: Path):
        for path in repo_root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in LANGUAGE_BY_EXTENSION:
                continue
            if any(part in IGNORED_DIR_NAMES for part in path.relative_to(repo_root).parts[:-1]):
                continue
            yield path

    @staticmethod
    def _unique_alias(name: str, used: Set[str]) -> str:
        alias = name or "repo"
        candidate = alias
        counter = 1
        while candidate in used:
            counter += 1
            candidate = f"{alias}_{counter}"
        return candidate

    @staticmethod
    def _node_id(repo_alias: str, repo_root: Path, file_path: Path) -> str:
        return f"{repo_alias}::{file_path.relative_to(repo_root).as_posix()}"

    @staticmethod
    def _module_name_for(repo_root: Path, file_path: Path) -> str:
        rel = file_path.relative_to(repo_root).with_suffix("")
        parts = list(rel.parts)
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(parts)

    @staticmethod
    def _extract_python_import_candidates(file_path: Path, repo_root: Path) -> Set[str]:
        try:
            tree = ast.parse(file_path.read_text(encoding="utf-8", errors="ignore"))
        except (SyntaxError, ValueError):
            return set()

        own_parts = list(file_path.relative_to(repo_root).with_suffix("").parts)
        if own_parts and own_parts[-1] == "__init__":
            own_parts = own_parts[:-1]
        package_parts = own_parts[:-1]

        candidates: Set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    candidates.add(alias.name)

            elif isinstance(node, ast.ImportFrom):
                if node.level and node.level > 0:
                    trim = node.level - 1
                    base_parts = package_parts[: len(package_parts) - trim] if trim < len(package_parts) else []
                else:
                    base_parts = []

                if node.module:
                    base_parts = base_parts + node.module.split(".")

                if base_parts:
                    candidates.add(".".join(base_parts))
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    candidates.add(".".join(base_parts + [alias.name]))

        return candidates

    def _detect_frameworks(self, text: str, file_path: Path) -> Set[str]:
        found: Set[str] = set()
        for framework, markers in FRAMEWORK_MARKERS.items():
            if any(marker in text for marker in markers):
                found.add(framework)
        if file_path.name == "package.json":
            try:
                data = json.loads(text)
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                if "express" in deps:
                    found.add("express")
                if "react" in deps:
                    found.add("react")
            except json.JSONDecodeError:
                pass
        return found

    @staticmethod
    def _detect_risk_tags(text: str, rel_path: str) -> Set[str]:
        haystack = f"{rel_path}\n{text}".lower()
        tags: Set[str] = set()
        for category, patterns in RISK_KEYWORD_PATTERNS.items():
            if any(re.search(p, haystack) for p in patterns):
                tags.add(category)
        return tags

    @staticmethod
    def _extract_routes(text: str, rel_path: str, repo_alias: str) -> List[Dict[str, Any]]:
        routes: List[Dict[str, Any]] = []

        def line_of(pos: int) -> int:
            return text.count("\n", 0, pos) + 1

        for match in ROUTE_PATTERNS["python-decorator"].finditer(text):
            verb = match.group(1).lower()
            path = match.group("path")
            rest = match.group("rest") or ""
            if verb != "route":
                methods = [verb.upper()]
            else:
                kw_match = _METHODS_KW_RE.search(rest)
                if kw_match:
                    methods = [m.strip().strip("'\"").upper() for m in kw_match.group(1).split(",") if m.strip()]
                else:
                    methods = ["GET"]
            for method in methods:
                routes.append({
                    "repo": repo_alias, "path": path, "method": method,
                    "file": rel_path, "line": line_of(match.start()), "source": "python-decorator",
                })

        for match in ROUTE_PATTERNS["django-url"].finditer(text):
            routes.append({
                "repo": repo_alias, "path": match.group("path"), "method": "ANY",
                "file": rel_path, "line": line_of(match.start()), "source": "django-url",
            })

        for match in ROUTE_PATTERNS["express"].finditer(text):
            verb = match.group(1).lower()
            if verb == "use":
                continue
            routes.append({
                "repo": repo_alias, "path": match.group("path"), "method": verb.upper(),
                "file": rel_path, "line": line_of(match.start()), "source": "express",
            })

        for match in ROUTE_PATTERNS["spring"].finditer(text):
            g0 = match.group(0)
            method_match = re.search(r'@(Get|Post|Put|Delete|Patch)Mapping', g0)
            method = method_match.group(1).upper() if method_match else "ANY"
            routes.append({
                "repo": repo_alias, "path": match.group("path"), "method": method,
                "file": rel_path, "line": line_of(match.start()), "source": "spring",
            })

        return routes

    def _split_text(self, text: str, language: str) -> List[str]:
        if not text.strip():
            return []
        splitter_lang = SPLITTER_LANGUAGE.get(language)
        if splitter_lang is not None:
            splitter = RecursiveCharacterTextSplitter.from_language(
                language=splitter_lang, chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
            )
        else:
            splitter = RecursiveCharacterTextSplitter(chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap)
        chunks = splitter.split_text(text)
        return [c for c in chunks if c.strip()]

    def _scan_repos(self, repo_paths: List[str]) -> Dict[str, Any]:
        documents: List[Document] = []
        metadata_store: Dict[str, Any] = {}
        file_hashes: Dict[str, str] = {}
        route_inventory: List[Dict[str, Any]] = []
        tech_inventory: Dict[str, Any] = {"repos": {}}
        dependency_nodes: Dict[str, Dict[str, Any]] = {}
        used_aliases: Set[str] = set()
        indexed_files = 0
        missing_repos: List[str] = []

        for repo_path_str in repo_paths:
            repo_root = Path(repo_path_str)
            if not repo_root.exists() or not repo_root.is_dir():
                missing_repos.append(repo_path_str)
                continue

            repo_alias = self._unique_alias(repo_root.name or repo_path_str, used_aliases)
            used_aliases.add(repo_alias)

            files = list(self._iter_source_files(repo_root))

            module_map: Dict[str, str] = {}
            for file_path in files:
                if file_path.suffix == ".py":
                    module_map[self._module_name_for(repo_root, file_path)] = self._node_id(repo_alias, repo_root, file_path)

            languages: Dict[str, int] = defaultdict(int)
            frameworks: Set[str] = set()

            for file_path in files:
                node_id = self._node_id(repo_alias, repo_root, file_path)
                rel_path = file_path.relative_to(repo_root).as_posix()
                language = LANGUAGE_BY_EXTENSION[file_path.suffix]
                languages[language] += 1

                try:
                    text = file_path.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue

                file_hashes[node_id] = hashlib.sha256(text.encode("utf-8")).hexdigest()
                frameworks.update(self._detect_frameworks(text, file_path))
                route_inventory.extend(self._extract_routes(text, rel_path, repo_alias))
                risk_tags = self._detect_risk_tags(text, rel_path)

                imports: Set[str] = set()
                if file_path.suffix == ".py":
                    for candidate in self._extract_python_import_candidates(file_path, repo_root):
                        target = module_map.get(candidate)
                        if target and target != node_id:
                            imports.add(target)

                dependency_nodes[node_id] = {
                    "repo": repo_alias, "path": rel_path, "language": language,
                    "imports": sorted(imports), "imported_by": [], "risk_tags": sorted(risk_tags),
                }

                for i, chunk in enumerate(self._split_text(text, language)):
                    chunk_id = f"{node_id}#{i}"
                    meta = {
                        "chunk_id": chunk_id, "node_id": node_id, "repo": repo_alias,
                        "path": rel_path, "language": language, "chunk_index": i,
                        "risk_tags": sorted(risk_tags),
                    }
                    metadata_store[chunk_id] = meta
                    documents.append(Document(page_content=chunk, metadata=meta))

                indexed_files += 1

            pkg_json = repo_root / "package.json"
            if pkg_json.exists():
                try:
                    frameworks.update(self._detect_frameworks(
                        pkg_json.read_text(encoding="utf-8", errors="ignore"), pkg_json
                    ))
                except OSError:
                    pass

            tech_inventory["repos"][repo_alias] = {
                "path": str(repo_root),
                "languages": dict(languages),
                "frameworks": sorted(frameworks),
            }

        for node_id, node in dependency_nodes.items():
            for dep in node["imports"]:
                if dep in dependency_nodes:
                    dependency_nodes[dep]["imported_by"].append(node_id)
        for node in dependency_nodes.values():
            node["imported_by"] = sorted(set(node["imported_by"]))

        return {
            "documents": documents,
            "metadata_store": metadata_store,
            "file_hashes": file_hashes,
            "route_inventory": route_inventory,
            "tech_inventory": tech_inventory,
            "dependency_graph": dependency_nodes,
            "indexed_files": indexed_files,
            "missing_repos": missing_repos,
            "repo_aliases": sorted(used_aliases),
        }

    # -- Action: index / baseline ----------------------------------------------

    def _build_baseline_index(self, repo_paths: List[str]) -> str:
        scan = self._scan_repos(repo_paths)
        documents = scan["documents"]

        if not documents:
            missing = f" Missing paths: {scan['missing_repos']}." if scan["missing_repos"] else ""
            return f"[ERROR] No source files found to index across repo_paths={repo_paths}.{missing}"

        context_path = self._context_path()
        context_path.mkdir(parents=True, exist_ok=True)

        doc_ids = [doc.metadata["chunk_id"] for doc in documents]
        vector_store = FAISS.from_documents(documents, self._get_embeddings(), ids=doc_ids)
        vector_store.save_local(str(self._index_dir()))

        self._vector_store = vector_store
        self._metadata_store = scan["metadata_store"]
        self._dependency_graph = scan["dependency_graph"]
        self._route_inventory = scan["route_inventory"]
        self._tech_inventory = scan["tech_inventory"]
        self._file_hashes = scan["file_hashes"]

        self._persist_json(self._metadata_path(), self._metadata_store)
        self._persist_json(self._blast_graph_path(), self._dependency_graph)
        self._persist_json(self._route_inventory_path(), self._route_inventory)
        self._persist_json(self._tech_inventory_path(), self._tech_inventory)
        self._persist_json(self._file_hashes_path(), self._file_hashes)

        high_risk = sum(1 for n in self._dependency_graph.values() if n["risk_tags"])

        return (
            "[INDEX] Successfully indexed repositories in baseline mode.\n"
            f"Repositories: {', '.join(scan['repo_aliases']) or 'none'}\n"
            f"Files indexed: {scan['indexed_files']}\n"
            f"Chunks embedded: {len(documents)}\n"
            f"Routes discovered: {len(self._route_inventory)}\n"
            f"High-risk modules flagged: {high_risk}\n"
            f"Context persisted to: {context_path}"
        )

    # -- Action: index / diff ---------------------------------------------------

    def _resolve_node_ids(self, paths: List[str]) -> Set[str]:
        resolved: Set[str] = set()
        graph = self._dependency_graph
        for raw in paths:
            normalized = raw.replace("\\", "/").strip()
            if not normalized:
                continue
            if normalized in graph:
                resolved.add(normalized)
                continue
            for node_id, node in graph.items():
                if node["path"] == normalized or node_id.endswith(f"::{normalized}") or normalized.endswith(f"/{node['path']}") or normalized == node["path"]:
                    resolved.add(node_id)
        return resolved

    def _blast_radius_node_ids(self, node_ids: Set[str]) -> Set[str]:
        graph = self._dependency_graph
        visited: Set[str] = set()
        queue = deque(node_ids)
        while queue:
            current = queue.popleft()
            node = graph.get(current)
            if not node:
                continue
            for caller in node.get("imported_by", []):
                if caller not in visited and caller not in node_ids:
                    visited.add(caller)
                    queue.append(caller)
        return visited

    def _refresh_diff_index(self, repo_paths: List[str], changed_files: List[str]) -> str:
        error = self._load_context(require_index=True)
        if error:
            return error

        if not changed_files:
            return "[ERROR] changed_files parameter is required for diff mode indexing."

        changed_node_ids = self._resolve_node_ids(changed_files)
        if not changed_node_ids:
            return (
                f"[ERROR] None of the provided changed_files could be matched to indexed nodes: {changed_files}. "
                "Run a baseline index first, or verify the paths are relative to an indexed repo_paths entry."
            )

        impacted_node_ids = self._blast_radius_node_ids(changed_node_ids)
        refresh_targets = sorted(changed_node_ids | impacted_node_ids)

        module_maps: Dict[str, Dict[str, str]] = {}
        repo_roots: Dict[str, Path] = {}
        for repo_path_str in repo_paths:
            repo_root = Path(repo_path_str)
            if not repo_root.exists():
                continue
            alias = repo_root.name
            repo_roots[alias] = repo_root
            module_map: Dict[str, str] = {}
            for file_path in self._iter_source_files(repo_root):
                if file_path.suffix == ".py":
                    module_map[self._module_name_for(repo_root, file_path)] = self._node_id(alias, repo_root, file_path)
            module_maps[alias] = module_map

        evicted_chunks = 0
        removed_routes = 0
        reembedded_files = 0
        removed_files: List[str] = []

        for node_id in refresh_targets:
            node = self._dependency_graph.get(node_id)
            if node is None:
                continue
            repo_alias = node["repo"]
            rel_path = node["path"]
            repo_root = repo_roots.get(repo_alias)

            stale_chunk_ids = [cid for cid, meta in self._metadata_store.items() if meta.get("node_id") == node_id]
            if stale_chunk_ids and self._vector_store is not None:
                self._vector_store.delete(ids=stale_chunk_ids)
            for cid in stale_chunk_ids:
                self._metadata_store.pop(cid, None)
                evicted_chunks += 1

            before = len(self._route_inventory)
            self._route_inventory = [
                r for r in self._route_inventory if not (r["repo"] == repo_alias and r["file"] == rel_path)
            ]
            removed_routes += before - len(self._route_inventory)

            file_path = (repo_root / rel_path) if repo_root else None
            if file_path is None or not file_path.exists():
                removed_files.append(node_id)
                del self._dependency_graph[node_id]
                self._file_hashes.pop(node_id, None)
                continue

            text = file_path.read_text(encoding="utf-8", errors="ignore")
            language = LANGUAGE_BY_EXTENSION.get(file_path.suffix, node["language"])
            self._file_hashes[node_id] = hashlib.sha256(text.encode("utf-8")).hexdigest()

            risk_tags = self._detect_risk_tags(text, rel_path)
            self._route_inventory.extend(self._extract_routes(text, rel_path, repo_alias))

            imports: Set[str] = set()
            if file_path.suffix == ".py":
                module_map = module_maps.get(repo_alias, {})
                for candidate in self._extract_python_import_candidates(file_path, repo_root):
                    target = module_map.get(candidate)
                    if target and target != node_id:
                        imports.add(target)

            node["imports"] = sorted(imports)
            node["risk_tags"] = sorted(risk_tags)

            new_docs: List[Document] = []
            for i, chunk in enumerate(self._split_text(text, language)):
                chunk_id = f"{node_id}#{i}"
                meta = {
                    "chunk_id": chunk_id, "node_id": node_id, "repo": repo_alias, "path": rel_path,
                    "language": language, "chunk_index": i, "risk_tags": sorted(risk_tags),
                }
                self._metadata_store[chunk_id] = meta
                new_docs.append(Document(page_content=chunk, metadata=meta))

            if new_docs:
                new_ids = [doc.metadata["chunk_id"] for doc in new_docs]
                if self._vector_store is None:
                    self._vector_store = FAISS.from_documents(new_docs, self._get_embeddings(), ids=new_ids)
                else:
                    self._vector_store.add_documents(new_docs, ids=new_ids)
            reembedded_files += 1

        for node in self._dependency_graph.values():
            node["imported_by"] = []
        for node_id, node in self._dependency_graph.items():
            for dep in node["imports"]:
                if dep in self._dependency_graph:
                    self._dependency_graph[dep]["imported_by"].append(node_id)
        for node in self._dependency_graph.values():
            node["imported_by"] = sorted(set(node["imported_by"]))

        if self._vector_store is not None:
            self._vector_store.save_local(str(self._index_dir()))
        self._persist_json(self._metadata_path(), self._metadata_store)
        self._persist_json(self._blast_graph_path(), self._dependency_graph)
        self._persist_json(self._route_inventory_path(), self._route_inventory)
        self._persist_json(self._file_hashes_path(), self._file_hashes)

        return (
            "[INDEX] Successfully refreshed index in diff mode.\n"
            f"Changed files: {len(changed_node_ids)}\n"
            f"Blast-radius impacted files also refreshed: {len(impacted_node_ids)}\n"
            f"Files re-embedded: {reembedded_files}\n"
            f"Files removed (deleted on disk): {len(removed_files)}\n"
            f"Chunks evicted: {evicted_chunks}\n"
            f"Route entries removed: {removed_routes}\n"
            f"Context persisted to: {self._context_path()}"
        )

    # -- Action: search ----------------------------------------------------------

    def _perform_semantic_search(self, query: str, top_k: Optional[int]) -> str:
        error = self._load_context(require_index=True)
        if error:
            return error

        k = top_k or 5
        results = self._vector_store.similarity_search_with_score(query, k=k)
        if not results:
            return f"[SEARCH] No relevant results found for query: '{query}'"

        blocks = [f"[SEARCH] Top {len(results)} result(s) for query: '{query}'"]
        for rank, (doc, score) in enumerate(results, start=1):
            meta = doc.metadata
            snippet = doc.page_content.strip()
            if len(snippet) > 400:
                snippet = snippet[:400] + "..."
            risk_tags = meta.get("risk_tags") or []
            risk_suffix = f", risk={','.join(risk_tags)}" if risk_tags else ""
            blocks.append(
                f"{rank}. [{meta.get('repo')}] {meta.get('path')} "
                f"(chunk {meta.get('chunk_index')}, score={score:.4f}{risk_suffix})\n"
                f"```\n{snippet}\n```"
            )
        return "\n\n".join(blocks)

    # -- Action: get_inventory ------------------------------------------------

    def _generate_inventory(self, repo_paths: List[str]) -> str:
        scan = self._scan_repos(repo_paths)

        if not scan["repo_aliases"]:
            missing = f" Missing paths: {scan['missing_repos']}." if scan["missing_repos"] else ""
            return f"[ERROR] No repositories could be scanned for repo_paths={repo_paths}.{missing}"

        self._dependency_graph = scan["dependency_graph"]
        self._route_inventory = scan["route_inventory"]
        self._tech_inventory = scan["tech_inventory"]
        self._file_hashes = scan["file_hashes"]
        self._context_path().mkdir(parents=True, exist_ok=True)
        self._persist_json(self._blast_graph_path(), self._dependency_graph)
        self._persist_json(self._route_inventory_path(), self._route_inventory)
        self._persist_json(self._tech_inventory_path(), self._tech_inventory)
        self._persist_json(self._file_hashes_path(), self._file_hashes)

        lines = ["# Multi-Repo Technology & Route Inventory", "", "## Technology Inventory"]
        for alias, info in scan["tech_inventory"]["repos"].items():
            lang_summary = ", ".join(f"{lang} ({count})" for lang, count in sorted(info["languages"].items()))
            fw_summary = ", ".join(info["frameworks"]) or "none detected"
            lines.append(f"- **{alias}** ({info['path']}): languages: {lang_summary or 'none'}; frameworks: {fw_summary}")

        lines.append("")
        lines.append("## Route Inventory")
        if scan["route_inventory"]:
            lines.append("| Method | Path | Handler File | Repo |")
            lines.append("|---|---|---|---|")
            for route in sorted(scan["route_inventory"], key=lambda r: (r["repo"], r["path"])):
                lines.append(f"| {route['method']} | {route['path']} | {route['file']} | {route['repo']} |")
        else:
            lines.append("No routes discovered.")

        lines.append("")
        lines.append("## High-Risk Modules")
        high_risk_nodes = [n for n in scan["dependency_graph"].values() if n["risk_tags"]]
        if high_risk_nodes:
            for node in sorted(high_risk_nodes, key=lambda n: (n["repo"], n["path"])):
                lines.append(f"- [{'/'.join(node['risk_tags'])}] {node['repo']}::{node['path']}")
        else:
            lines.append("No high-risk modules flagged.")

        lines.append("")
        lines.append(f"Files scanned: {scan['indexed_files']}")
        if scan["missing_repos"]:
            lines.append(f"Missing repo paths: {scan['missing_repos']}")

        return "\n".join(lines)

    # -- Action: get_blast_radius ----------------------------------------------

    def _calculate_blast_radius(self, changed_files: List[str]) -> str:
        self._load_context(require_index=False)
        graph = self._dependency_graph
        if not graph:
            return (
                "[ERROR] No blast radius graph available. Run action='index' with mode='baseline' first "
                f"to build the dependency graph. (changed_files={changed_files})"
            )

        changed_node_ids = self._resolve_node_ids(changed_files)
        resolved_paths = {graph[nid]["path"] for nid in changed_node_ids if nid in graph}
        unresolved = [
            f for f in changed_files
            if f.replace("\\", "/") not in changed_node_ids and not f.replace("\\", "/").endswith(tuple(f"/{p}" for p in resolved_paths))
            and f.replace("\\", "/") not in resolved_paths
        ]

        direct_impact: Set[str] = set()
        for nid in changed_node_ids:
            direct_impact.update(graph.get(nid, {}).get("imported_by", []))

        transitive_impact = self._blast_radius_node_ids(changed_node_ids) - direct_impact - changed_node_ids

        upstream_deps: Set[str] = set()
        for nid in changed_node_ids:
            upstream_deps.update(graph.get(nid, {}).get("imports", []))

        def describe(nid: str) -> str:
            node = graph.get(nid, {})
            return f"{node.get('repo', '?')}::{node.get('path', nid)}"

        lines = [f"[BLAST RADIUS] Impact analysis for {len(changed_files)} changed file(s).", "", "Changed files:"]
        lines.extend(f"  - {f}" for f in changed_files)

        if unresolved:
            lines.append("")
            lines.append("Unresolved (not found in dependency graph - new/untracked files):")
            lines.extend(f"  - {f}" for f in unresolved)

        lines.append("")
        lines.append(f"Directly impacted callers ({len(direct_impact)}):")
        if direct_impact:
            lines.extend(f"  - {describe(nid)}" for nid in sorted(direct_impact))
        else:
            lines.append("  (none)")

        lines.append("")
        lines.append(f"Transitively impacted callers ({len(transitive_impact)}):")
        if transitive_impact:
            lines.extend(f"  - {describe(nid)}" for nid in sorted(transitive_impact))
        else:
            lines.append("  (none)")

        lines.append("")
        lines.append(f"Upstream dependencies of changed files ({len(upstream_deps)}):")
        if upstream_deps:
            lines.extend(f"  - {describe(nid)}" for nid in sorted(upstream_deps))
        else:
            lines.append("  (none)")

        total_impacted = len(changed_node_ids | direct_impact | transitive_impact)
        lines.append("")
        lines.append(f"Total files in blast radius (changed + impacted): {total_impacted}")

        return "\n".join(lines)
