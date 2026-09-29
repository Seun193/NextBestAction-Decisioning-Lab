# Membership Data Operations KPI Definitions

## Purpose

This document defines the business rules, denominators, reporting windows, and interpretation of the Membership Data Operations KPIs used by the Next Best Action Decisioning Lab.

All data is synthetic.

The KPI layer is designed to remain independently verifiable against the SQLite operational data.

---

## Reporting Reference Date

Initial reporting date:

`2026-09-21`

This is the same fixed as-of date used by the synthetic membership data pipeline.

Unless explicitly stated otherwise, time-based KPIs use a trailing 30-calendar-day reporting window inclusive of the as-of date.

For an as-of date of `2026-09-21`, the 30-day reporting window is:

`2026-08-23` through `2026-09-21`

---

# Core Membership KPIs

## KPI-001 — Total Members

### Definition

Total number of membership records in the `members` table.

### Formula

```text
Total Members =
COUNT(members.member_id)