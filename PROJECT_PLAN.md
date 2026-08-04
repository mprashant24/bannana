# Project Plan: Deep Agent Upgrade — Incremental & Baseline Security Analysis Framework

## 🎯 Executive Summary

The objective of this project is to enhance the **Deep Agent Security Code Review Framework** by introducing two distinct execution modes (**Baseline** and **Diff**) along with **3 supporting auxiliary tools** and a **7-step agentic workflow**. 

These upgrades will drastically optimize token consumption, accelerate audit execution time, enable CI/CD integration for commit-by-commit reviews, and ensure high consistency across security review reports over time.

---

## 🏗️ Architecture Overview

```
                      ┌──────────────────────────────────────┐
                      │        CLI / Execution Entry         │
                      │   (Baseline Mode  |  Diff Mode)      │
                      └──────────────────┬───────────────────┘
                                         │
 ┌───────────────────────────────────────┴───────────────────────────────────────┐
 │                            7-Step Deep Agent Pipeline                         │
 │                                                                               │
 │  1. Inventory Generation  ──►  2. Scope Detection  ──►  3. Targeted Analysis │
 │            ▲                                                      │           │
 │            │                                                      ▼           │
 │  7. Context Persistence  ◄──  6. Report Validation ◄── 5. Report Gen ◄── 4. Result Judging │
 └───────────────────────────────────────┬───────────────────────────────────────┘
                                         │
              ┌──────────────────────────┼──────────────────────────┐
              ▼                          ▼                          ▼
     ┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
     │  Git Operations  │       │  Embedding Tool  │       │  Reporting Tool  │
     │      Tool        │       │   (FAISS / RAG)  │       │   (Delta/Format) │
     └──────────────────┘       └──────────────────┘       └──────────────────┘
```

---

## 🛠️ Supporting Tools Specification

### 1. Git Operations Tool (`git_ops_tool`)
- **Purpose**: Interacts with the repository's Git history to extract diffs, modified files, and commit metadata.
- **Capabilities**:
  - `get_current_commit()`: Fetches the current HEAD commit hash.
  - `get_diff_summary(base_commit, target_commit)`: Returns added, modified, deleted file paths and line-level diff chunks.
  - `map_changes_to_modules()`: Groups changed files into functional areas (e.g. auth, api, db, config).
  - `save_commit_context(commit_id, context_data)`: Records the state and snapshot hash for future comparison.

### 2. Embedding & Semantic Search Tool (`embedding_tool`)
- **Purpose**: Creates and queries vector representations of the codebase to minimize prompt context size and focus LLM token usage.
- **Capabilities**:
  - `build_code_index(repo_path)`: Generates dense embeddings for codebase chunks (using FAISS / vector store).
  - `update_code_index(changed_files)`: Incremental embedding updates for added/modified files in diff mode.
  - `search_relevant_snippets(query, scope_filters)`: Retrieves top-$k$ relevant code blocks for specific security topics (e.g., "JWT verification", "SQL query construction").

### 3. Reporting & State Management Tool (`reporting_tool`)
- **Purpose**: Manages standardized report output generation and handles delta tracking (new, persistent, and resolved issues).
- **Capabilities**:
  - `generate_report_schema(findings, metadata)`: Ensures strict JSON / Markdown report consistency.
  - `reconcile_findings(previous_report, new_findings, git_diff)`:
    - **Mark New**: Vulnerabilities introduced in the commit.
    - **Mark Resolved**: Previously identified issues fixed in modified/deleted code.
    - **Mark Persistent**: Ongoing unaddressed vulnerabilities.
  - `format_output(mode, format_type)`: Generates clean human-readable Markdown and machine-readable JSON.

---

## 🔄 Execution Modes

### Mode 1: Baseline (`--mode baseline`)
- **Objective**: Full codebase security audit and state capture.
- **Workflow**:
  1. Scans the entire repository (`/repo`).
  2. Generates full technology and risk-area inventory.
  3. Builds complete vector index via the Embedding Tool.
  4. Conducts exhaustive security analysis across all active domain skills.
  5. Saves baseline report and persists state context (commit hash, findings manifest, embeddings) under `.deepagent_context/`.

### Mode 2: Diff (`--mode diff --commit <commit_id>`)
- **Objective**: Incremental audit focusing strictly on modified code and affected risk areas.
- **Workflow**:
  1. Identifies differences between target commit and baseline commit using Git Operations Tool.
  2. Refreshes vector embeddings only for changed files via Embedding Tool.
  3. Detects analysis scope (e.g., if only `auth/` changed, restrict deep checks to Authentication/Authorization skills).
  4. Runs targeted analysis on changed/impacted code blocks.
  5. Reconciles new findings against baseline via Reporting Tool (adds new findings, marks fixed issues as resolved).
  6. Updates persisted context for subsequent diff runs.

---

## 📋 7-Step Deep Agent Pipeline Detail

| Step | Name | Objective | Tools & Inputs Used |
| :---: | :--- | :--- | :--- |
| **1** | **Inventory Generation** | Identify technologies, frameworks, libraries, and risk areas present in the repository. | Embedding Tool, File Inspection |
| **2** | **Scope Analysis Detection** | Determine required analysis depth & specific security skills (e.g. Auth, Injection, Crypto) based on changes. | Git Operations Tool, Inventory Manifest |
| **3** | **Execution of Analysis** | Run targeted security reviews on scoped areas using domain-specific skills. | Prompt Templates, Embedding Search, Skills |
| **4** | **Validating / Judging Results** | Filter out false positives, verify evidence, and assign severity scores. | Agentic Reflection / Critic Prompt |
| **5** | **Generation of Report** | Assemble standardized report structures for baseline or diff views. | Reporting Tool |
| **6** | **Validation / Judging of Report**| Ensure completeness, verified line citations, code snippets, and remediation clarity. | Quality Assurance Agent |
| **7** | **Saving Context for Future Runs**| Store baseline snapshot, updated inventory, active findings, and commit metadata. | Local File Storage (`.deepagent_context/`) |

---

## 🗓️ Implementation Phases & Roadmap

### Phase 1: Supporting Tools Development (Days 1–3)
- [ ] Implement `GitOpsTool` class (wrapping `git` commands / `GitPython`).
- [ ] Implement `EmbeddingTool` class using FAISS/Chroma and HuggingFace/Bedrock embeddings.
- [ ] Implement `ReportingTool` class for finding reconciliation (New, Fixed, Persistent) and schema validation.

### Phase 2: Pipeline & Prompt Refactoring (Days 4–6)
- [ ] Refactor `deepagent.py` to support 7 distinct step execution prompts in sequence.
- [ ] Create specialized prompt templates for:
  - `1_inventory.md`
  - `2_scope.md`
  - `3_analysis.md`
  - `4_judge_results.md`
  - `5_report.md`
  - `6_judge_report.md`
  - `7_context.md`
- [ ] Integrate `--mode baseline` and `--mode diff` CLI switches with `--commit` parameters.

### Phase 3: State Persistence & Diff Engine Integration (Days 7–8)
- [ ] Design `.deepagent_context/` JSON schema for baseline snapshots and finding hashes.
- [ ] Implement automated resolution tracking when code chunks containing vulnerabilities are modified/removed.
- [ ] Add context locking and error handling for missing git history or clean working trees.

### Phase 4: Testing, Validation & Documentation (Days 9–10)
- [ ] Validate token savings comparing baseline vs. incremental diff runs on sample repositories.
- [ ] Verify accuracy of finding reconciliation (verifying fixed vulnerabilities vs newly introduced ones).
- [ ] Update `README.md` and CLI documentation with usage guidelines for both execution modes.

---

## 🎯 Success Metrics

- **Token Cost Reduction**: Minimum **60–80% reduction** in token consumption on incremental diff runs vs full baseline runs.
- **Execution Speed**: **>3x faster** turnaround time on commit-level CI/CD checks.
- **Report Consistency**: 100% adherence to standard JSON/Markdown finding formats.
- **Resolution Accuracy**: Zero false resolves for untouched vulnerabilities across commit iterations.
