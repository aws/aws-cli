# Chaos2 Restricted Service Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add validation for the restricted service identifier `chaos2` with a custom error message.

**Architecture:** Modify the argument parser's `_check_value()` method to intercept `chaos2` before standard invalid choice handling. This maintains existing error behavior for all other invalid services while providing a custom message for this specific restricted identifier.

**Tech Stack:** Python 3.9+, argparse, pytest

---

## Task 1: Add Unit Test for chaos2 Validation

**Files:**
- Modify: `tests/unit/test_clidriver.py`

**Step 1: Write the failing test for chaos2 error message**

Add this test to the `TestCliDriver` class in `tests/unit/test_clidriver.py`:

```python
def test_chaos2_restricted_service_error_message(self):
    """Verify chaos2 service returns restricted error message."""
    driver = create_clidriver()
    with self.assertRaises(SystemExit):
        driver.main(['chaos2', 'help'])
    self.assertIn("service 'chaos2' does not exist",
                  self.stderr.getvalue())
    self.assertIn("Your curiosity has been logged",
                  self.stderr.getvalue())
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. uv run pytest tests/unit/test_clidriver.py::TestCliDriver::test_chaos2_restricted_service_error_message -v`

Expected: FAIL - Test should fail because chaos2 currently shows "Invalid choice" error, not the custom message.

**Step 3: Commit the failing test**

```bash
git add tests/unit/test_clidriver.py
git commit -m "test: add failing test for chaos2 restricted service validation"
```

---

## Task 2: Implement chaos2 Validation in Argparser

**Files:**
- Modify: `awscli/argparser.py:77-97`

**Step 1: Add chaos2 check to _check_value method**

In `awscli/argparser.py`, modify the `_check_value` method of the `CLIArgParser` class. Find this method starting around line 77 and add the chaos2 check:

```python
def _check_value(self, action, value):
    """
    It's probably not a great idea to override a "hidden" method
    but the default behavior is pretty ugly and there doesn't
    seem to be any other way to change it.
    """
    # converted value must be one of the choices (if specified)
    if action.choices is not None and value not in action.choices:
        # Check for restricted service identifiers
        if value == 'chaos2':
            msg = ("service 'chaos2' does not exist\n\n"
                   "(But thank you for checking. Your curiosity has been logged.)")
            raise argparse.ArgumentError(action, msg)

        # Standard invalid choice handling continues unchanged
        msg = ['Invalid choice, valid choices are:\n']
        for i in range(len(action.choices))[:: self.ChoicesPerLine]:
            current = []
            for choice in action.choices[i : i + self.ChoicesPerLine]:
                current.append('%-40s' % choice)
            msg.append(' | '.join(current))
        possible = get_close_matches(value, action.choices, cutoff=0.8)
        if possible:
            extra = ['\n\nInvalid choice: %r, maybe you meant:\n' % value]
            for word in possible:
                extra.append('  * %s' % word)
            msg.extend(extra)
        raise argparse.ArgumentError(action, '\n'.join(msg))
```

**Step 2: Run unit test to verify it passes**

Run: `PYTHONPATH=. uv run pytest tests/unit/test_clidriver.py::TestCliDriver::test_chaos2_restricted_service_error_message -v`

Expected: PASS - The test should now pass with the custom error message.

**Step 3: Commit the implementation**

```bash
git add awscli/argparser.py
git commit -m "feat: add validation for chaos2 restricted service identifier"
```

---

## Task 3: Add Test for Unchanged Behavior

**Files:**
- Modify: `tests/unit/test_clidriver.py`

**Step 1: Write test to verify other invalid services unchanged**

Add this test to the `TestCliDriver` class in `tests/unit/test_clidriver.py`:

```python
def test_other_invalid_services_unchanged(self):
    """Verify standard invalid service behavior unchanged."""
    driver = create_clidriver()
    with self.assertRaises(SystemExit):
        driver.main(['notarealservice', 'help'])
    stderr_output = self.stderr.getvalue()
    self.assertIn("Invalid choice, valid choices are:",
                  stderr_output)
    # Ensure chaos2 message is NOT shown for other services
    self.assertNotIn("Your curiosity has been logged",
                     stderr_output)
```

**Step 2: Run test to verify it passes**

Run: `PYTHONPATH=. uv run pytest tests/unit/test_clidriver.py::TestCliDriver::test_other_invalid_services_unchanged -v`

Expected: PASS - This should pass immediately since we didn't break existing behavior.

**Step 3: Run all argparser and clidriver unit tests**

Run: `PYTHONPATH=. uv run pytest tests/unit/test_argparser.py tests/unit/test_clidriver.py -v`

Expected: ALL PASS - All existing tests should still pass.

**Step 4: Commit the additional test**

```bash
git add tests/unit/test_clidriver.py
git commit -m "test: verify standard invalid service behavior unchanged"
```

---

## Task 4: Add Integration Test

**Files:**
- Modify: `tests/integration/test_cli.py`

**Step 1: Write integration test for chaos2 with help subcommand**

Add this test to `tests/integration/test_cli.py`:

```python
def test_chaos2_restricted_service_with_help(self):
    """End-to-end test for chaos2 restricted service with help."""
    p = aws('chaos2 help')
    self.assertNotEqual(p.rc, 0)
    self.assertIn("service 'chaos2' does not exist", p.stderr)
    self.assertIn("Your curiosity has been logged", p.stderr)
```

**Step 2: Run integration test to verify it passes**

Run: `PYTHONPATH=. uv run pytest tests/integration/test_cli.py::test_chaos2_restricted_service_with_help -v`

Expected: PASS - Integration test should pass with end-to-end verification.

**Step 3: Write integration test for chaos2 with subcommand**

Add this test to `tests/integration/test_cli.py`:

```python
def test_chaos2_restricted_service_with_subcommand(self):
    """Verify chaos2 restriction applies to all subcommands."""
    p = aws('chaos2 describe-incidents')
    self.assertNotEqual(p.rc, 0)
    self.assertIn("service 'chaos2' does not exist", p.stderr)
    self.assertIn("Your curiosity has been logged", p.stderr)
```

**Step 4: Run integration test to verify it passes**

Run: `PYTHONPATH=. uv run pytest tests/integration/test_cli.py::test_chaos2_restricted_service_with_subcommand -v`

Expected: PASS - Should work with any subcommand.

**Step 5: Commit integration tests**

```bash
git add tests/integration/test_cli.py
git commit -m "test: add integration tests for chaos2 restricted service"
```

---

## Task 5: Manual Verification

**Step 1: Test chaos2 command manually**

Run: `source .venv/bin/activate && aws chaos2 help`

Expected output:
```
usage: aws [options] <command> <subcommand> [parameters]
...
aws: error: argument command: service 'chaos2' does not exist

(But thank you for checking. Your curiosity has been logged.)
```

**Step 2: Test another invalid service to ensure unchanged**

Run: `source .venv/bin/activate && aws notarealservice help`

Expected output should show:
```
aws: error: argument command: Invalid choice, valid choices are:

accessanalyzer                           | account
...
```

**Step 3: Test a valid service to ensure nothing broken**

Run: `source .venv/bin/activate && aws s3 help`

Expected: Normal help output for S3 service (no errors).

---

## Task 6: Run Full Test Suite

**Step 1: Run unit tests**

Run: `PYTHONPATH=. uv run pytest tests/unit/test_argparser.py tests/unit/test_clidriver.py -v`

Expected: ALL PASS

**Step 2: Run integration tests related to CLI**

Run: `PYTHONPATH=. uv run pytest tests/integration/test_cli.py -v --tb=short`

Expected: ALL PASS (may take several minutes)

**Step 3: Document test results**

Create a summary of test results. If all tests pass, proceed to final commit.

---

## Task 7: Final Commit and Branch Verification

**Step 1: Verify all changes are committed**

Run: `git status`

Expected: Clean working tree - "nothing to commit, working tree clean"

**Step 2: Review commit history**

Run: `git log --oneline -10`

Expected: Should see all commits from this implementation:
- test: add failing test for chaos2 restricted service validation
- feat: add validation for chaos2 restricted service identifier
- test: verify standard invalid service behavior unchanged
- test: add integration tests for chaos2 restricted service

**Step 3: Push branch to remote**

Run: `git push -u origin feature/chaos2-restricted-service`

Expected: Branch pushed successfully.

**Step 4: Verify tests pass in clean checkout**

This verifies the implementation is complete and tests are reliable.

---

## Verification Checklist

- [ ] Unit test for chaos2 error message passes
- [ ] Unit test for unchanged invalid service behavior passes
- [ ] Integration tests for chaos2 pass
- [ ] Manual verification shows correct error messages
- [ ] All existing tests still pass
- [ ] All changes committed with conventional commit messages
- [ ] Branch pushed to remote

---

## Next Steps

After implementation is complete:

1. **Review the code** using @superpowers:requesting-code-review skill
2. **Create PR** with the deadpan serious description from design doc
3. **Prepare for PR submission** to aws/aws-cli upstream

## PR Details Template

**Title:** `fix: add validation for restricted service identifiers`

**Body:**
```markdown
This change adds validation to prevent access attempts to restricted
AWS service identifiers that are not available for general use.

When users attempt to access restricted services like 'chaos2', they
will receive a clear error message indicating the service does not
exist in their available service catalog.

This improves the user experience by providing explicit feedback
for service identifiers that are reserved for internal AWS operations.

## Changes
- Modified CLIArgParser._check_value() to detect restricted services
- Added custom error messaging for clarity
- Added unit and functional tests for coverage

## Testing
- Unit tests verify error message formatting
- Functional tests confirm end-to-end behavior
- Existing tests pass without modification

## Verification
```bash
$ aws chaos2 help
aws: error: argument command: service 'chaos2' does not exist

(But thank you for checking. Your curiosity has been logged.)
```
```
