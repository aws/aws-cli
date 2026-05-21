---
name: sonar-coverage
description: Find files with low test coverage and inspect uncovered lines in a SonarQube project (project key optional when MCP integration already defines the default project)
argument-hint: "[project-key?] [--max n] [--file key] [--pr id]"
---

# SonarQube — Coverage

Identify files with insufficient test coverage and pinpoint the exact lines that need tests.

## Usage

```
sonar-coverage                              # worst-covered files in the configured project
sonar-coverage my-project                   # worst-covered files in a specific project
sonar-coverage --max 50                     # only files with coverage <= 50%
sonar-coverage --file src/auth/login.py     # line-by-line detail for one file
sonar-coverage --pr 42                      # coverage on a pull request
```

## Prerequisites

This skill requires the SonarQube MCP Server to be configured and the tools `mcp__sonarqube__search_files_by_coverage` and `mcp__sonarqube__get_file_coverage_details` to be available in your session.

If a call to either MCP tool fails, surface the tool error verbatim and stop. Auth, credentials, and MCP server configuration are runtime infrastructure concerns and are not user-fixable from chat — do not ask the user to verify env vars or to install or run any CLI.

## Instructions

### Step 1: Resolve the project key (only when needed)

MCP tools sometimes **do not require** `projectKey` when the SonarQube MCP Server has a default project for this workspace (e.g. `SONARQUBE_PROJECT_KEY` configured in the server env). Resolve a key only when you must pass it (tool schema requires it, or the user targets another project):

- If the user provided a project key, use it.
- Otherwise look for `sonar.projectKey` in `sonar-project.properties` at the repo root.
- If still not found, **omit `projectKey`** in MCP calls and rely on the integration default.

### Step 2: Parse optional flags from the user-provided arguments

| Flag           | Meaning                                                                     |
| -------------- | --------------------------------------------------------------------------- |
| `--max <n>`    | Only return files with coverage ≤ n% (maps to `maxCoverage`)                |
| `--pr <id>`    | Analyse a pull request instead of the main branch                           |
| `--file <key>` | Skip the file list and go straight to line-by-line detail for this file key |

### Step 3: Run the appropriate flow

#### Flow A — File list (default, no `--file`)

Invoke the MCP tool `mcp__sonarqube__search_files_by_coverage`. Include **`projectKey` only if** you resolved one in Step 1 **and** the tool requires it; otherwise omit it.

```json
{
  "projectKey": "<only-if-required>",
  "maxCoverage": "<n>",
  "pullRequest": "<id>",
  "pageSize": 20
}
```

Omit unused optional fields.

Present results as a table sorted by coverage ascending:

```markdown
## Coverage

Files with lowest coverage (worst first):

| File                | Coverage |
| ------------------- | -------- |
| src/auth/login.py   | 12.5%    |
| src/utils/crypto.py | 23.0%    |
| src/api/routes.py   | 41.8%    |
```

If no files are returned (all files exceed the threshold), say: *"All files meet the coverage threshold."*

Then offer to drill in:
*"Ask me to inspect any of these files for uncovered lines, or invoke the sonar-coverage skill with `--file <file-key>`."*

#### Flow B — Line detail (`--file <key>` given, or user asks to inspect a file)

Invoke the MCP tool `mcp__sonarqube__get_file_coverage_details`:

```json
{
  "key": "<file-key>",
  "pullRequest": "<id>"
}
```

Use the file key as returned by Flow A (format `<projectKey>:<path>`, e.g. `my-project:src/auth/login.py`). If the user provides just a path, prepend the resolved project key when you have one; otherwise pass the path as-is and the MCP server resolves it against the configured project.

Present uncovered and partially covered lines:

```markdown
## Coverage Detail — `src/auth/login.py`

Overall coverage: **12.5%**

### Uncovered lines
Lines with no test coverage: 14, 15, 23, 45–52, 67

### Partially covered branches
| Line | Covered branches | Total branches |
| ---- | ---------------- | -------------- |
| 30   | 1                | 2              |
| 61   | 0                | 2              |
```

If the file is fully covered, say: *"All lines in this file are covered."*

### Step 4: Next steps

- To write tests for uncovered lines: *"Ask me to add tests for the uncovered lines above."*
- To check for quality issues in the same file: *"Invoke the sonar-list-issues skill with `--component <file>`."*
- To check the quality gate: *"Invoke the sonar-quality-gate skill."*
