# Security Code Review Agent Pipeline (`bannana`)

An automated AI-driven security code review framework built using [`deepagents`](https://github.com/langchain-ai) and LangChain on top of AWS Bedrock (`qwen.qwen3-coder-30b-a3b-v1:0`).

This tool analyzes source code placed in the `repo/` folder through a structured 4-stage agentic workflow to discover vulnerabilities, trace endpoints, and produce structured security review reports.

---

## 📐 Architecture & Pipeline

The framework executes a sequential 4-agent chain to conduct deep reflection and analysis:

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  1. Collect     │ ───► │  2. Analyze     │ ───► │  3. Review      │ ───► │  4. Report      │
│  (Identify Scope)│      │  (Find Issues)  │      │  (Validate & Refine)   │  (Generate Final)│
└─────────────────┘      └─────────────────┘      └─────────────────┘      └─────────────────┘
```

1. **Collect Agent (`1 - collect.md`)**: Scans `repo/` and enumerates relevant files based on the task description to build an analysis scope.
2. **Analyze Agent (`2 - analyze.md`)**: Conducts initial deep analysis on the scope, flagging findings with file locations, line numbers, code snippets, and impact assessments.
3. **Review Agent (`3 - review.md`)**: Performs a second-pass reflection to validate, refine, and prune false positives.
4. **Report Agent (`4 - report.md`)**: Synthesizes all verified findings into a professional, comprehensive security report.

---

## 📁 Repository Structure

```
.
├── deepagent.py           # Main CLI entry point executing the agent pipeline
├── scr.bat                # Windows batch script for automated multi-pass security audits
├── requirements.txt       # Python dependencies (deepagents, langchain-aws, dotenv, etc.)
├── .env                   # AWS Bedrock API configuration
├── repo/                  # Directory where the target codebase to be audited is placed
├── prompts/               # Prompt templates defining persona, step objectives & instructions
│   ├── personna.md        # Security analyst role & reflection process
│   ├── instructions.md    # Tool usage rules & directory constraints
│   ├── collect.md         # Stage 1: File collection prompt
│   ├── analyze.md         # Stage 2: Code analysis prompt
│   ├── review.md          # Stage 3: Verification prompt
│   └── report.md          # Stage 4: Report generation prompt
├── skills/                # Domain-specific security review guidance
│   ├── auditing-review/
│   ├── authentication-review/
│   ├── authorization-review/
│   ├── configuration-review/
│   ├── cryptographic-review/
│   ├── identify-url-paths/
│   └── injection-review/
└── steps/                 # Generated intermediate and final markdown artifacts per run
```

---

## 🚀 Setup & Prerequisites

### Prerequisites

- **Python 3.10+**
- **AWS Bedrock Access**: Configured with permissions to invoke `qwen.qwen3-coder-30b-a3b-v1:0` or your configured ChatBedrockConverse model.

### Installation

1. **Clone or open the repository**:
   ```bash
   cd c:\workspace\bannana
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure AWS Environment Variables**:
   Create or edit `.env` in the root directory with your AWS credentials:
   ```env
   AWS_ACCESS_KEY_ID=your_access_key
   AWS_SECRET_ACCESS_KEY=your_secret_key
   AWS_DEFAULT_REGION=us-east-1
   ```

4. **Add Target Code**:
   Place the source code you want to review into the `repo/` directory:
   ```
   repo/
   └── <target_application_files>
   ```

---

## 💻 Usage Instructions

### 1. Running Single Audit Tasks (`deepagent.py`)

Run `deepagent.py` directly by passing a task description as an argument:

```bash
python deepagent.py "Perform a security code review on the authentication module in /repo"
```

#### Command-Line Arguments

| Argument | Short | Description |
| :--- | :--- | :--- |
| `task` | — | *(Required)* Task description / focus for the DeepAgent. |
| `--output` | `-o` | *(Optional)* Output directory path where step markdown files will be saved. |
| `--isolate`| `-i` | *(Optional)* Flag to isolate input context between agents (prevents passing output from previous steps). |

#### Usage Examples

- **Codebase Overview**:
  ```bash
  python deepagent.py -o "./output/overview" "Create a codebase overview. Identify the application's core architecture and components."
  ```

- **Discover Vulnerabilities**:
  ```bash
  python deepagent.py -o "./output/injection" "Perform a code review to discover vulnerabilities related to SQL injection and command injection."
  ```

- **Isolated Execution**:
  ```bash
  python deepagent.py -i -o "./output/auth" "Perform a code review focusing on authentication flaws."
  ```

---

### 2. Batch Security Review (`scr.bat`)

On Windows, `scr.bat` executes a full automated 8-pass audit covering key OWASP/security domains:

```cmd
scr.bat
```

This runs sequential analysis passes and outputs findings under `..\_output\vtm\`:
1. `1 - overview`: High-level codebase architecture overview.
2. `2 - URL endpoints`: Endpoint & URL path discovery.
3. `3 - URL paths and injection`: URL paths and injection vulnerability assessment.
4. `4 - authentication`: Authentication flaws review.
5. `5 - authorization`: Authorization and access control review.
6. `6 - auditing`: Logging and auditing mechanism review.
7. `7 - configuration and injections`: Configuration security and generic injection review.
8. `8 - cryptography`: Cryptographic implementation review.

---

## 📊 Output Artifacts

Execution progress and markdown results are stored under `steps/`:
- `steps/1 - collect.md`
- `steps/2 - analyze.md`
- `steps/3 - review.md`
- `steps/4 - report.md`

If `--output` / `-o` is specified, the contents of `steps/` are copied to the designated folder upon task completion.

---

## ⚙️ Customization

- **Prompts**: Edit files in `prompts/` (`personna.md`, `collect.md`, `analyze.md`, `review.md`, `report.md`) to adjust the agent roles, reflection process, or report formatting.
- **Skills**: Add or update skill guides under `skills/<skill-name>/SKILL.md` to inject specific vulnerability checking guidelines or checklists into the agent context.
- **LLM Model**: Modify `deepagent.py` to target a different LangChain model provider or Bedrock model ID.
