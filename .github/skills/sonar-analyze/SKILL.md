---
name: sonar-analyze
description: Analyze a file or code snippet for quality and security issues using SonarQube
argument-hint: "[file-path]"
---

# SonarQube — Code Analysis

Analyze code for quality and security issues using the SonarQube MCP Server.

## Usage

```
sonar-analyze                        # analyze the file currently in context
sonar-analyze src/auth/login.py      # analyze a specific file
```

## Prerequisites

This skill requires the SonarQube MCP Server to be configured and the tool `mcp__sonarqube__analyze_code_snippet` to be available in your session.

If the tool call fails, surface the tool error verbatim and stop. Auth, credentials, and MCP server configuration are runtime infrastructure concerns and are not user-fixable from chat — do not ask the user to verify env vars or to install or run any CLI.

## Instructions

### Step 1: Resolve what to analyze

The tool analyses **one file at a time**. Resolve a single file path:

- If the user provided a file path, use it.
- If no path was provided, look at the current conversation context for a recently mentioned or edited file.
- If nothing is clear, ask: *"Which file would you like me to analyze?"*

Do not accept a directory as input. If the user provides one, ask them to specify a single file.

### Step 2: Read the file and detect context

1. Read the file's full content (required for `codeSnippet` and language detection).
2. Detect the **language** from the file extension:

| Extension              | Language key |
| ---------------------- | ------------ |
| `.py`                  | `py`         |
| `.js` `.jsx`           | `js`         |
| `.ts` `.tsx`           | `ts`         |
| `.java`                | `java`       |
| `.go`                  | `go`         |
| `.php`                 | `php`        |
| `.cs`                  | `cs`         |
| `.rb`                  | `rb`         |
| `.swift`               | `swift`      |
| `.kt`                  | `kotlin`     |
| `.c` `.cpp` `.cc` `.h` | `cpp`        |

3. Determine the **file scope**: `"TEST"` or `"MAIN"`. If the path contains `test`, `spec`, or `__tests__`, use `"TEST"`; otherwise `"MAIN"`.

### Step 3: Call `mcp__sonarqube__analyze_code_snippet`

The SonarQube MCP Server often has a **default project** for this workspace (e.g. via `SONARQUBE_PROJECT_KEY` configured in the server env), so **`projectKey` is sometimes unnecessary** — pass it only when the tool schema requires it or the user targets another project.

```json
{
  "projectKey": "<only-if-required>",
  "filePath": "src/auth/login.py",
  "codeSnippet": "<full file content>",
  "language": "py",
  "scope": "MAIN"
}
```

Omit `projectKey` when the integration default applies.

### Step 4: Format the results

**If issues are found**, present them as a table sorted by line number:

```markdown
## SonarQube Analysis — `src/auth/login.py`

Found **3 issue(s)**:

| Line | Severity   | Rule         | Message                                               |
| ---- | ---------- | ------------ | ----------------------------------------------------- |
| 12   | 🔴 Blocker | python:S2077 | Make sure that executing this SQL query is safe here. |
| 34   | 🟠 Major   | python:S1481 | Remove the unused local variable "token".             |
| 67   | 🟡 Minor   | python:S1135 | Complete the task associated to this "TODO" comment.  |
```

Severity icons (the label depends on the server version):
- 🔴 Blocker
- 🟠 Critical / High
- 🟡 Major / Medium
- 🔵 Minor / Low
- ⚪ Info

**If no issues are found**:

```markdown
## SonarQube Analysis — `src/auth/login.py`

✅ No issues found.
```

### Step 5: Next steps

After the results, always add:

- If issues were found: *"Invoke the sonar-fix-issue skill with `<rule> <file>:<line>` to fix a specific issue, or ask me to fix them all."*
- If the user wants to analyze another file: remind them to invoke the sonar-analyze skill with the file path.
