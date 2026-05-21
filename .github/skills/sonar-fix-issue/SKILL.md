---
name: sonar-fix-issue
description: Fix a specific SonarQube issue in code by rule key and location
argument-hint: "[rule-key] [file-path:line]"
---

# SonarQube — Fix Issue

Fix a code quality or security issue identified by SonarQube.

## Usage

```
sonar-fix-issue java:S1481 src/main/java/MyClass.java:42
sonar-fix-issue python:S2077 src/auth/login.py
sonar-fix-issue Remove unused variable in MyClass.java
```

## Prerequisites

This skill requires the SonarQube MCP Server to be configured and the tool `mcp__sonarqube__show_rule` to be available in your session.

If the tool call fails, surface the tool error verbatim and stop. Auth, credentials, and MCP server configuration are runtime infrastructure concerns and are not user-fixable from chat — do not ask the user to verify env vars or to install or run any CLI. Do not fabricate rule descriptions from built-in knowledge.

## Instructions

### Step 1: Identify the issue

Parse the user-provided arguments for:
- A rule key (e.g. `java:S1481`, `python:S2077`)
- A file path and optional line number (e.g. `src/auth/login.py:34`)
- Or a plain-language description if no rule key is given

If neither a rule key nor a file path can be determined, ask: *"Which rule and file should I fix?"*

### Step 2: Look up the rule (if a key was given)

Call `mcp__sonarqube__show_rule` with the rule key to retrieve the full rule description,
rationale, and remediation guidance before touching any code. **Do not add extra parameters** (such as `projectKey`) unless the tool schema requires them — rule lookup usually needs only the rule key.

If the call fails, surface the error verbatim and stop — do not fall back to built-in knowledge of the rule, since it may be stale or wrong for the user's SonarQube configuration. Auth and configuration issues are infrastructure problems, not user-fixable from chat.

### Step 3: Read the file

Read the full file content. If a line number was given, focus analysis around that line
but read the whole file to understand context.

### Step 4: Apply the fix

- Make the **minimal change** that resolves the rule violation
- Do not refactor surrounding code or fix unrelated issues
- Preserve existing behaviour — the fix must not change what the code does

### Step 5: Explain the change

After editing, briefly explain:
- What the violation was
- Why the rule flags it
- What was changed and why it resolves the issue

### Step 6: Suggest next steps

- *"Invoke the sonar-analyze skill with `<file>` to confirm no new issues were introduced."*
- *"Invoke the sonar-list-issues skill (add a project key only if you are not using the MCP integration default)."*
