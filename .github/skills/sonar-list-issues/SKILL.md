---
name: sonar-list-issues
description: Search and filter SonarQube issues for a project, branch, or pull request via the SonarQube MCP Server (project key optional when MCP integration already defines the default project)
argument-hint: "[project-key?] [--severity values] [--qualities values] [--statuses values] [--rules values] [--component path] [--branch name] [--pr id]"
---

# SonarQube — List Issues

Search for issues (bugs, vulnerabilities, code smells) in a SonarQube project using the SonarQube MCP Server.

## Usage

```
sonar-list-issues                                          # issues in the current project
sonar-list-issues my-project                               # issues in a specific project key
sonar-list-issues my-project --severity HIGH,BLOCKER       # filter by severity
sonar-list-issues my-project --qualities SECURITY          # filter by software quality
sonar-list-issues my-project --statuses OPEN,CONFIRMED     # filter by status
sonar-list-issues my-project --rules python:S2077          # filter by rule key
sonar-list-issues my-project --component src/auth/login.py # issues in a specific file
sonar-list-issues my-project --pr 42                       # on a pull request
```

## Prerequisites

This skill requires the SonarQube MCP Server to be configured and the tool `mcp__sonarqube__search_sonar_issues_in_projects` to be available in your session.

If the tool call fails, surface the tool error verbatim and stop. Auth, credentials, and MCP server configuration are runtime infrastructure concerns and are not user-fixable from chat — do not ask the user to verify env vars or to install or run any CLI.

## Instructions

### Step 1: Resolve the project key (only when needed)

MCP tools sometimes **do not require** `projectKey` when the SonarQube MCP Server has a default project for this workspace (e.g. `SONARQUBE_PROJECT_KEY` configured in the server env). Resolve a key only when you must pass it (tool schema requires it, or the user targets another project):

- If the user provided a project key, use it.
- Otherwise look for `sonar.projectKey` in `sonar-project.properties` at the repo root.
- If still not found, **omit `projects`** in the MCP call and rely on the integration default.

### Step 2: Parse optional flags from the user-provided arguments

| Flag                   | Maps to MCP parameter                          |
| ---------------------- | ---------------------------------------------- |
| `--severity <values>`  | `severities` (array)                           |
| `--qualities <values>` | `impactSoftwareQualities` (array)              |
| `--statuses <values>`  | `issueStatuses` (array)                        |
| `--rules <values>`     | _(filter client-side from response)_           |
| `--component <path>`   | `files` (array; file key `project-key:src/...`)|
| `--branch <name>`      | _(not supported on this tool — see note)_      |
| `--pr <id>`            | `pullRequestId`                                |
| `--page <n>`           | `p`                                            |
| `--page-size <n>`      | `ps` (1–500, default 100)                      |

When `--component` is given as a plain path, prepend the resolved project key (when you have one) to form the component key (e.g. `my-project:src/auth/login.py`).

**Note on `--branch`:** `mcp__sonarqube__search_sonar_issues_in_projects` does not expose a branch parameter directly. If the user passes `--branch`, tell them branch filtering is not supported on this MCP tool and offer to run the query against the default branch or a pull request instead.

### Step 3: Validate arguments

Before building the call, validate each user-supplied value against the rules below. If any value fails validation, stop and tell the user what was rejected and why — do not run the call. Validate the resolved project key (from args or `sonar-project.properties`) against the project-key pattern before sending it.

| Argument      | Allowed pattern / values                                                                  |
| ------------- | ----------------------------------------------------------------------------------------- |
| project key   | `^[a-zA-Z0-9_\-\.:]+$`                                                                    |
| `--severity`  | comma-separated subset of: `INFO`, `LOW`, `MEDIUM`, `HIGH`, `BLOCKER`                     |
| `--qualities` | comma-separated subset of: `MAINTAINABILITY`, `RELIABILITY`, `SECURITY`                   |
| `--statuses`  | comma-separated subset of: `OPEN`, `CONFIRMED`, `FALSE_POSITIVE`, `ACCEPTED`, `FIXED`     |
| `--rules`     | comma-separated values matching `^[a-zA-Z0-9_\-:]+$`                                      |
| `--component` | path matching `^[a-zA-Z0-9_\-\./:,]+$`                                                    |
| `--pr`        | digits only                                                                               |
| `--page`      | positive integer                                                                          |
| `--page-size` | integer 1–500                                                                             |

### Step 4: Call `mcp__sonarqube__search_sonar_issues_in_projects`

Include **`projects` only if** you resolved a project key in Step 1 **and** you want to target a non-default project; otherwise omit it and rely on the integration default.

```json
{
  "projects": ["<only-if-needed>"],
  "severities": ["HIGH", "BLOCKER"],
  "impactSoftwareQualities": ["SECURITY"],
  "issueStatuses": ["OPEN"],
  "files": ["<project-key>:src/auth/login.py"],
  "pullRequestId": "<id>",
  "p": 1,
  "ps": 100
}
```

Omit any field that was not requested by the user. If `--rules` was given, filter the returned issues client-side by `rule` matching one of the supplied rule keys.

### Step 5: Format the results

**If issues are found**, present a summary line then a table sorted by severity then line number:

```markdown
## SonarQube Issues — `my-project`

Found **12 issue(s)**:

| File                 | Line | Severity  | Rule         | Message                       |
| -------------------- | ---- | --------- | ------------ | ----------------------------- |
| src/auth/login.py    | 12   | 🔴 Blocker | python:S2077 | SQL injection risk            |
| src/utils/helpers.py | 34   | 🟠 Critical / High | python:S2259 | Null dereference              |
| src/api/routes.py    | 67   | 🟡 Medium  | python:S3776 | Cognitive complexity too high |
```

Severity icons (the label depends on the server version):
- 🔴 Blocker
- 🟠 Critical / High
- 🟡 Major / Medium
- 🔵 Minor / Low
- ⚪ Info

If the response is paginated and more issues exist, mention the next page (e.g. *"Showing page 1 of N. Re-run with `--page 2` to see more."*).

**If no issues are found**:

```markdown
## SonarQube Issues — `my-project`

✅ No issues found.
```

### Step 6: Next steps

- To fix a specific issue: *"Invoke the sonar-fix-issue skill with `<rule> <file>:<line>`."*
- To check the quality gate: *"Invoke the sonar-quality-gate skill."*
