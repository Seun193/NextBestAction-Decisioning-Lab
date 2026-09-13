# CI Regression Workflow Validation

## Objective

Establish a repeatable regression workflow that can be executed locally and by a CI platform, produces machine-readable test evidence, and returns reliable process exit codes for pipeline decision-making.

---

## Local Regression Runner

A PowerShell regression entry point was added:

```text
scripts/run_regression.ps1
```

The runner:

- identifies the active Python executable
- verifies the project configuration
- runs the complete pytest regression suite
- generates a JUnit XML report
- captures the pytest exit code
- reports PASS or FAIL
- propagates the exit code to the calling process

The generated JUnit report is written to:

```text
reports/ci/pytest-junit.xml
```

Generated CI reports are local artifacts and are excluded from Git version control.

---

## Baseline Validation

The regression runner was executed against the verified project state.

Result:

```text
56 passed
1 known dependency warning

REGRESSION RESULT: PASS
Pytest exit code : 0
```

The JUnit report was successfully generated.

This confirmed that a healthy build returns process exit code `0`.

---

## Intentional Failure Probe

A temporary regression test was introduced:

```python
def test_ci_failure_probe():
    assert False, "Intentional CI failure probe"
```

The regression runner was then executed without modifying the runner itself.

Result:

```text
1 failed
56 passed
1 known dependency warning

REGRESSION RESULT: FAIL
Pytest exit code : 1
```

PowerShell confirmed:

```text
$LASTEXITCODE
1
```

This demonstrated that the regression workflow propagates test failure correctly to the operating system.

A CI platform can therefore use the non-zero exit code to fail the job and block the change.

---

## Restoration Verification

The temporary failure probe was removed.

The regression workflow was executed again.

Result:

```text
56 passed
1 known dependency warning

REGRESSION RESULT: PASS
Pytest exit code : 0
```

PowerShell confirmed:

```text
$LASTEXITCODE
0
```

The project returned to its verified regression baseline.

---

## CI Workflow

A GitHub Actions workflow was added under:

```text
.github/workflows/regression.yml
```

The workflow is designed to execute in a fresh environment and perform:

```text
Checkout repository
        |
        v
Set up Python
        |
        v
Install dependencies
        |
        v
Generate synthetic customer data
        |
        v
Build SQLite database
        |
        v
Run complete pytest regression suite
        |
        v
Generate JUnit XML report
        |
        v
PASS or FAIL
```

The CI runner does not depend on the developer's local `banking` environment.

---

## CI Decision Behaviour

The validated pipeline behaviour is:

```text
All tests pass
      |
      v
Exit code 0
      |
      v
Pipeline PASS
```

```text
One or more tests fail
      |
      v
Non-zero exit code
      |
      v
Pipeline FAIL
```

This is the mechanism used by CI/CD systems to prevent failed regression builds from progressing.

---

## Validation Result

Local CI-compatible regression validation completed successfully.

Verified evidence:

- complete 56-test regression suite passes
- JUnit XML report is generated
- successful regression returns exit code `0`
- intentional regression failure returns exit code `1`
- removal of the intentional defect restores exit code `0`
- temporary failure probe was not retained in the project

Cloud CI execution will be validated after the workflow is pushed to the repository.