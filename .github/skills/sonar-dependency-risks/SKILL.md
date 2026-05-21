---
name: sonar-dependency-risks
description: Search for software composition analysis (SCA) dependency risks in a SonarQube project (project key optional when MCP integration already defines the default project)
argument-hint: "[project-key?] [--branch name] [--pr id]"
---

# SonarQube — Dependency Risks

Search for dependency risks (software composition analysis issues) in a SonarQube project, paired with the releases that appear in the analysed project, application, or portfolio.

## Usage

```
sonar-dependency-risks                    # risks in the current project
sonar-dependency-risks my-project         # risks in a specific project
sonar-dependency-risks my-project --branch feature/auth
sonar-dependency-risks my-project --pr 42
```

## Prerequisites

This skill requires SonarQube Advanced Security (available on SonarQube Cloud Enterprise plan, or SonarQube Server 2025.4 Enterprise edition or higher), the SonarQube MCP Server to be configured, and the tool `mcp__sonarqube__search_dependency_risks` to be available in your session.

If the tool call fails, surface the tool error verbatim and stop. Auth, credentials, and MCP server configuration are runtime infrastructure concerns and are not user-fixable from chat — do not ask the user to verify env vars or to install or run any CLI. If the error indicates the feature is unavailable, note plainly that SCA requires SonarQube Advanced Security (SonarQube Cloud Enterprise plan, or SonarQube Server 2025.4 Enterprise or higher).

## Instructions

### Step 1: Resolve the project key (only when needed)

MCP tools sometimes **do not require** `projectKey` when the SonarQube MCP Server has a default project for this workspace (e.g. `SONARQUBE_PROJECT_KEY` configured in the server env). Resolve a key only when you must pass it (tool schema requires it, or the user targets another project):

- If the user provided a project key, use it.
- Otherwise look for `sonar.projectKey` in `sonar-project.properties` at the repo root.
- If still not found, **omit `projectKey`** in MCP calls and rely on the integration default.

### Step 2: Parse optional flags from the user-provided arguments

| Flag              | Maps to parameter |
| ----------------- | ----------------- |
| `--branch <name>` | `branchKey`       |
| `--pr <id>`       | `pullRequestKey`  |

### Step 3: Call `mcp__sonarqube__search_dependency_risks`

Include **`projectKey` only if** you resolved one in Step 1 **and** the tool requires it; otherwise omit it.

```json
{
  "projectKey": "<only-if-required>",
  "branchKey": "<name>",       // if --branch was given
  "pullRequestKey": "<id>"     // if --pr was given
}
```

Omit `projectKey` from the payload when the integration default applies. Omit unused optional fields.

### Step 4: Format the results

**If risks are found**, group by severity and present as a table:

```markdown
## Dependency Risks — `my-project` (branch: `main`)

Found **5 dependency risk(s)**:

### Critical
| Dependency | Version | Risk                  | CVE            |
| ---------- | ------- | --------------------- | -------------- |
| log4j-core | 2.14.1  | Remote code execution | CVE-2021-44228 |

### High
| Dependency       | Version | Risk                          | CVE            |
| ---------------- | ------- | ----------------------------- | -------------- |
| jackson-databind | 2.12.3  | Deserialization vulnerability | CVE-2021-46877 |
| commons-text     | 1.9     | Remote code execution         | CVE-2022-42889 |

### Medium
| Dependency    | Version | Risk              | CVE            |
| ------------- | ------- | ----------------- | -------------- |
| spring-web    | 5.3.18  | DoS vulnerability | CVE-2022-22965 |
| netty-handler | 4.1.68  | SSL/TLS issue     | CVE-2021-43797 |
```

Omit columns that are not present in the response. Omit severity sections that have no risks.

**If no risks are found**:

```markdown
## Dependency Risks — `my-project`

✅ No dependency risks found.
```

### Step 5: Next steps

- To fix a vulnerable dependency: *"Ask me to update `<dependency>` to a safe version."*
- To check the quality gate: *"Invoke the sonar-quality-gate skill (add a project key only if you are not using the integration default)."*
- To check code-level security issues: *"Invoke the sonar-list-issues skill with filters as needed (add a project key only if you are not using the MCP integration default)."*
