# NBA CI Regression Rules v1

## Purpose

Define the regression-validation requirements for automated execution of the NBA Decisioning Lab test suite in local and CI environments.

---

## CI-001 — Single Regression Entry Point

The project shall provide a single command for executing the complete automated regression suite.

Local PowerShell entry point:

```powershell
.\scripts\run_regression.ps1
```

---

## CI-002 — Complete Regression Suite

The regression workflow shall execute all pytest tests configured for the project.

A successful regression run shall require every test to pass.

---

## CI-003 — Machine-Readable Report

Every regression run shall generate a JUnit XML report suitable for CI systems.

Expected location:

```text
reports/ci/pytest-junit.xml
```

---

## CI-004 — Successful Exit Status

When all regression tests pass, the regression runner shall:

- report PASS
- return exit code `0`

---

## CI-005 — Failed Exit Status

When one or more regression tests fail, the regression runner shall:

- report FAIL
- return a non-zero exit code

This allows CI/CD systems to block defective changes.

---

## CI-006 — Fresh CI Environment

The cloud CI workflow shall not depend on:

- the local `banking` environment
- an existing local SQLite database
- locally generated customer files

The workflow shall reconstruct the required test environment from repository-controlled source files.

---

## CI-007 — Synthetic Test Data

The CI workflow shall generate the synthetic customer dataset before running regression tests.

---

## CI-008 — SQLite Database Build

The CI workflow shall build the SQLite customer database before executing tests that depend on repository data.

---

## CI-009 — Push Validation

The regression workflow shall execute automatically for relevant pushes.

---

## CI-010 — Pull Request Validation

The regression workflow shall execute for pull requests targeting `main`.

---

## CI-011 — Regression Artifact

The JUnit regression report shall be retained as a CI artifact when supported by the CI platform.

---

## CI-012 — Release Protection Principle

A failing regression suite shall produce a failed CI job so the change can be prevented from progressing through the delivery pipeline.