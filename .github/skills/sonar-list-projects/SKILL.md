---
name: sonar-list-projects
description: List SonarQube projects accessible to the current user via the SonarQube MCP Server
argument-hint: "[search-query] [--page n] [--page-size n]"
---

# SonarQube — List Projects

List SonarQube projects accessible to the authenticated user. Useful for discovering project keys before running other skills.

## Usage

```
sonar-list-projects                      # list accessible projects
sonar-list-projects my-project           # search by name (partial) or key (exact)
sonar-list-projects --page 2             # next page of results
sonar-list-projects --page-size 100      # limit page size
```

## Prerequisites

This skill requires the SonarQube MCP Server to be configured and the tool `mcp__sonarqube__search_my_sonarqube_projects` to be available in your session.

If the tool call fails, surface the tool error verbatim and stop. Auth, credentials, and MCP server configuration are runtime infrastructure concerns and are not user-fixable from chat — do not ask the user to verify env vars or to install or run any CLI.

## Instructions

### Step 1: Parse arguments

- The first non-flag argument (if present) is the search term and maps to `q`.
- `--page <n>` maps to `page` (string, defaults to `1`).
- `--page-size <n>` maps to `pageSize` (integer 1–500, defaults to 500).

### Step 2: Validate arguments

| Argument      | Allowed pattern / values |
| ------------- | ------------------------ |
| search term   | `^[a-zA-Z0-9_\-\. ]+$`   |
| `--page`      | positive integer         |
| `--page-size` | integer 1–500            |

If a value fails validation, stop and tell the user what was rejected — do not run the call.

### Step 3: Call `mcp__sonarqube__search_my_sonarqube_projects`

```json
{
  "q": "<search-term>",
  "page": "<n>",
  "pageSize": <n>
}
```

Omit any field the user did not provide.

### Step 4: Format the results

**If projects are found**:

```markdown
## SonarQube Projects

Found **8 project(s)**:

| Project key       | Name            |
| ----------------- | --------------- |
| my-org_backend    | Backend Service |
| my-org_frontend   | Frontend App    |
| my-org_shared-lib | Shared Library  |
```

**If no projects are found**:

```markdown
## SonarQube Projects

No projects found.
```

**If more results are likely** (response is full to `pageSize`): *"Showing page N. Use `--page <n+1>` to see more, or pass a search term to narrow results."*

### Step 5: Next steps

- To list issues: *"Invoke the sonar-list-issues skill with the project key, or rely on the MCP integration default."*
- To check the quality gate: *"Invoke the sonar-quality-gate skill — add a project key only if you are not using the MCP integration default."*
