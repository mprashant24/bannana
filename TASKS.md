# Project Tasks: Deep Agent Upgrade

This document outlines the detailed task breakdown for upgrading the Deep Agent framework with Baseline and Diff execution modes, supporting tools, and the 7-step pipeline.

---

## 🛠️ Phase 1: Supporting Tools Development

### Task 1
| Task ID | TASK-001: Implement Git Operations Tool (`git_ops_tool`) |
| :--- | :--- |
| **Owner** | Phillip |
| **Change Details** | Create `tools/git_ops.py` wrapping Git CLI / `GitPython`. Implement `get_current_commit()`, `get_diff_summary(base_commit, target_commit)`, `map_changes_to_modules()`, and `save_commit_context(commit_id, context_data)`. |

### Task 2
| Task ID | TASK-002: Implement Embedding & Semantic Search Tool (`embedding_tool`) |
| :--- | :--- |
| **Owner** | Prashant |
| **Change Details** | Create `tools/embedding_tool.py` using FAISS/Chroma and HuggingFace/Bedrock embeddings. Implement `build_code_index(repo_path)`, `update_code_index(changed_files)`, and `search_relevant_snippets(query, scope_filters)`. |

### Task 3
| Task ID | TASK-003: Implement Reporting & State Management Tool (`reporting_tool`) |
| :--- | :--- |
| **Owner** | Amanda |
| **Change Details** | Create `tools/reporting_tool.py` to handle JSON/Markdown schema validation, finding reconciliation (`reconcile_findings` for New, Persistent, and Resolved issues), and output formatting (`format_output`). |

---

## 🔄 Phase 2: Pipeline Refactoring & Execution Modes

### Task 4
| Task ID | TASK-004: Refactor Main Agent Engine for 7-Step Pipeline |
| :--- | :--- |
| **Owner** | Tom |
| **Change Details** | Refactor `deepagent.py` to replace the 4-step pipeline with the 7-step pipeline: `Inventory Generation`, `Scope Detection`, `Execution of Analysis`, `Validating/Judging Results`, `Generation of Report`, `Validation/Judging of Report`, and `Saving Context`. |

### Task 5
| Task ID | TASK-005: Create Step Prompt Templates |
| :--- | :--- |
| **Owner** | Tom |
| **Change Details** | Create specialized markdown prompt files under `prompts/`: `inventory.md`, `scope.md`, `analysis.md`, `judge_results.md`, `report.md`, `judge_report.md`, and `context.md`. |

### Task 6
| Task ID | TASK-006: Implement CLI Options for Baseline and Diff Modes |
| :--- | :--- |
| **Owner** | Phillip |
| **Change Details** | Update `ArgumentParser` in `deepagent.py` to add `--mode` (`baseline` or `diff`) and `--commit <commit_id>` flags. Connect CLI options to control full repo vs incremental diff workflows. |

---

## 📦 Phase 3: State Persistence & Delta Engine Integration

### Task 7
| Task ID | TASK-007: Design Context State Persistence Schema |
| :--- | :--- |
| **Owner** | |
| **Change Details** | Design and implement `.deepagent_context/` directory structure and JSON schema to store baseline snapshots, findings hashes, commit metadata, and vector index references. |

### Task 8
| Task ID | TASK-008: Implement Automated Issue Resolution Tracking |
| :--- | :--- |
| **Owner** | |
| **Change Details** | Implement vulnerability delta reconciliation logic in `reporting_tool` and `git_ops.py` to automatically detect and mark issues as Resolved when vulnerability-associated code blocks are modified or removed. |

### Task 9
| Task ID | TASK-009: Add Context Locking & Git Error Handling |
| :--- | :--- |
| **Owner** | |
| **Change Details** | Implement context locking mechanisms, repository state validation (clean working directory check), and error handling for missing Git history or invalid commit SHAs. |

---

## 🧪 Phase 4: Testing, Validation & Documentation

### Task 10
| Task ID | TASK-010: Token & Performance Benchmarking |
| :--- | :--- |
| **Owner** | |
| **Change Details** | Perform benchmarks comparing full Baseline execution against incremental Diff execution on test repositories to verify 60–80% token savings and >3x execution speedup. |

### Task 11
| Task ID | TASK-011: Finding Reconciliation Accuracy Verification |
| :--- | :--- |
| **Owner** | |
| **Change Details** | Conduct test scenarios with introduced and remediated vulnerabilities to ensure 100% accuracy in marking New, Persistent, and Resolved findings across commits. |

### Task 12
| Task ID | TASK-012: Update Project Documentation & Batch Scripts |
| :--- | :--- |
| **Owner** | |
| **Change Details** | Update `README.md`, `scr.bat`, and CLI `--help` messages with updated usage examples for `--mode baseline` and `--mode diff` execution. |
