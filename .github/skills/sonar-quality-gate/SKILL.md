---
name: sonar-quality-gate
description: Show SonarQube quality gate status for a project — pass/fail and each condition (metric key, threshold, actual value). Project key optional when MCP integration already defines the default project.
argument-hint: "[project-key?] [--branch name] [--pr id]"
---

# SonarQube — Quality gate

Report **only** the quality gate evaluation for a SonarQube project: overall status and every **condition** returned by the API. Do not pull a broad measures dashboard here — for numeric metrics beyond the gate (coverage %, issue counts, ratings as measures, and so on), use **`mcp__sonarqube__get_component_measures`** afterward with the `metricKeys` you care about.

## Usage

```
sonar-quality-gate                       # quality gate for the current project
sonar-quality-gate my-project            # quality gate for a specific project key
sonar-quality-gate my-project --branch release/2.0
sonar-quality-gate my-project --pr 42
```

## Prerequisites

This skill requires the SonarQube MCP Server to be configured and the tool `mcp__sonarqube__get_project_quality_gate_status` to be available in your session.

If the tool call fails, surface the tool error verbatim and stop. Auth, credentials, and MCP server configuration are runtime infrastructure concerns and are not user-fixable from chat — do not ask the user to verify env vars or to install or run any CLI.

## Instructions

### Step 1: Resolve the project key (only when needed)

MCP tools often **do not require** `projectKey` when the SonarQube MCP Server has a default project for this workspace (e.g. `SONARQUBE_PROJECT_KEY` configured in the server env). Resolve a key only when you must pass it (tool schema requires it, or the user targets another project):

- If the user provided a project key, use it.
- Otherwise look for `sonar.projectKey` in `sonar-project.properties` at the repo root.
- If still not found, **omit `projectKey`** in MCP calls and rely on the integration default.

### Step 2: Parse optional filters from the user-provided arguments

| Flag              | Maps to parameter |
| ----------------- | ----------------- |
| `--branch <name>` | `branchKey`       |
| `--pr <id>`       | `pullRequestKey`  |

Omit keys the MCP tool does not accept. If the tool uses different parameter names, follow the schema exposed by your SonarQube MCP server.

### Step 3: Call `mcp__sonarqube__get_project_quality_gate_status`

Use a single call. Include **`projectKey` only if** you resolved one in Step 1 **and** the tool requires it; otherwise omit it. Example payload:

```json
{
  "projectKey": "<only-if-required>",
  "branchKey": "<name>",
  "pullRequestKey": "<id>"
}
```

Include `branchKey` only when `--branch` was given, and `pullRequestKey` only when `--pr` was given. Omit `projectKey` from the payload when the integration default applies. Omit unused keys.

The tool returns a top-level **`status`** (`OK`, `ERROR`, or other values your server uses) and a **`conditions`** array. Each condition typically includes:

| Field            | Meaning                                                                 |
| ---------------- | ----------------------------------------------------------------------- |
| `metricKey`      | SonarQube metric identifier for the gate condition                      |
| `status`         | Per-condition result (`OK`, `ERROR`, …)                                 |
| `errorThreshold` | Required bound when the gate defines one (may be absent for some types) |
| `actualValue`    | Value SonarQube compared against the threshold                          |

**Example (all conditions OK)** — response shape:

```json
{
  "status": "OK",
  "conditions": [
    {
      "metricKey": "reliability_rating",
      "status": "OK",
      "errorThreshold": "2",
      "actualValue": "1"
    },
    {
      "metricKey": "security_rating",
      "status": "OK",
      "errorThreshold": "1",
      "actualValue": "1"
    },
    {
      "metricKey": "new_duplicated_lines_density",
      "status": "OK",
      "errorThreshold": "3",
      "actualValue": "0.0"
    }
  ]
}
```

**Example (failing gate)** — note missing `errorThreshold` on some conditions is normal:

```json
{
  "status": "ERROR",
  "conditions": [
    {
      "metricKey": "new_coverage",
      "status": "ERROR",
      "errorThreshold": "85",
      "actualValue": "82.50562381034781"
    },
    {
      "metricKey": "new_blocker_violations",
      "status": "ERROR",
      "errorThreshold": "0",
      "actualValue": "14"
    },
    {
      "metricKey": "new_sqale_debt_ratio",
      "status": "OK",
      "errorThreshold": "5",
      "actualValue": "0.6562109862671661"
    },
    {
      "metricKey": "reopened_issues",
      "status": "OK",
      "actualValue": "0"
    },
    {
      "metricKey": "open_issues",
      "status": "ERROR",
      "actualValue": "17"
    }
  ]
}
```

### Step 4: Format the results

Present a concise report:

1. **Headline** — Map top-level `status` to plain language (e.g. `OK` → passed, `ERROR` → failed). Include project key and branch/PR context if known.
2. **Conditions table** — One row per element of `conditions`, columns at minimum:
   - **Metric** — `metricKey` (humanize lightly if you know the name; otherwise keep the key).
   - **Condition status** — `status`.
   - **Threshold** — `errorThreshold` when present; use `—` when absent.
   - **Actual** — `actualValue` when present; use `—` when absent.

Sort so failing conditions (`ERROR` or non-OK, per server rules) appear **before** passing ones.

3. **Ratings** — For keys like `reliability_rating` / `security_rating`, SonarQube often encodes ratings as numeric grades in the API (for example 1 = A, 5 = E). Mention that interpretation when it helps the user.

4. **No extra measures** — Do not call `get_component_measures` inside this skill unless the user explicitly asks for deeper metrics in the same turn. When they need more detail, tell them the next step (see Step 5).

If the quality gate payload is missing or analysis has not run, say so clearly instead of inventing values.

### Step 5: Deeper metrics (`get_component_measures`)

To investigate **beyond** the gate (e.g. overall coverage, line coverage, bug counts, detailed ratings), call **`mcp__sonarqube__get_component_measures`** with the same branch/PR context if applicable, and pass `metricKeys` for the measures you need. Add **`projectKey` only when** the tool requires it and you have a resolved key; otherwise rely on the integration default (you can start from the `metricKey` values that failed or from the [SonarQube metric keys](https://docs.sonarsource.com/) documentation).

### Step 6: Related skills

- **sonar-list-issues** — drill into issues when conditions reference violations or hotspots.
- **sonar-coverage** — file- and line-level coverage when `new_coverage` or similar fails.
