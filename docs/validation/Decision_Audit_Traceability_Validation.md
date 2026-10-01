# Decision Audit and Traceability Validation

## Purpose

This document records implementation and validation evidence for the Decision Audit and Traceability capability in the synthetic Next Best Action Decisioning Lab.

The capability allows a successfully returned Next Best Action decision to be traced from the API response back to the exact persisted decision evidence used at decision time.

The implementation covers:

- unique decision identifiers
- SQLite audit persistence
- customer input snapshots
- membership-context snapshots
- selected-action evidence
- complete ranked-action evidence
- reason-code traceability
- decision and API version traceability
- API-to-database reconciliation
- data-quality validation
- append-only decision history
- transaction atomicity
- fail-closed API behaviour
- automated release validation

All customer, membership, and decision information used in this project is synthetic.

---

## Requirements Basis

Validation is derived from:

```text
docs/requirements/Decision_Audit_Traceability_Requirements_v1.md
```

The requirements are identified as:

```text
DAT-001 through DAT-040
```

The pre-feature regression baseline defined by the requirements was:

```text
317 automated tests passing
```

The validated post-implementation regression baseline is:

```text
360 automated tests passing
```

---

## High-Level Decision Audit Flow

The implemented decision path is:

```text
GET /nba/{customer_id}
        |
        v
Customer lookup
        |
        v
Membership context lookup
        |
        v
Next Best Action decision
        |
        v
Selected action + ranked candidate set
        |
        v
Decision Audit persistence
        |
        +--------------------------+
        |                          |
        v                          v
SQLite decision_audits       X-Decision-ID
        |                          |
        +-------------+------------+
                      |
                      v
             API-to-audit
             reconciliation
```

The audit capability records a completed decision.

It does not determine:

- eligibility
- consent
- product rules
- scoring
- membership relevance
- candidate ranking

Existing banking and membership decisioning logic remains authoritative.

---

## Audit Schema

The audit schema is implemented in:

```text
src/decision_audit_schema.py
```

The persisted table is:

```text
decision_audits
```

Each decision record contains:

| Field | Purpose |
| --- | --- |
| decision_id | Unique audit identifier |
| customer_id | Customer used for decisioning |
| decision_timestamp | UTC decision timestamp |
| selected_action | Final Next Best Action |
| selected_score | Persisted selected score |
| selected_eligible | Selected eligibility state |
| selected_reason_codes_json | Selected-action reason codes |
| ranked_actions_json | Complete ranked candidate set |
| customer_snapshot_json | Customer inputs at decision time |
| membership_snapshot_json | Membership inputs when supplied |
| membership_used | Whether membership context was supplied |
| decision_engine_version | Decision-logic version |
| model_version | Model version when applicable |
| api_version | API/application version |
| audit_schema_version | Audit-structure version |

The initial audit schema version is:

```text
1.0
```

---

## Referential Integrity

Successful audit records reference:

```text
decision_audits.customer_id
        ->
customers.customer_id
```

SQLite foreign-key enforcement is enabled during audit schema creation and persistence validation.

Automated tests confirm that an audit record cannot reference a customer that does not exist in the customer table.

---

## Schema Initialization Safety

Audit schema creation uses:

```text
CREATE TABLE IF NOT EXISTS
```

and equivalent safe index creation.

Repeated schema initialization does not delete existing decision history.

Automated validation confirms that an existing audit row remains present after audit schema initialization is executed again.

This provides evidence for reload-safety requirements.

---

## Decision Identifier

Every successfully persisted decision receives a unique identifier.

Generated identifiers use the format:

```text
DEC-<UUID>
```

Example shape:

```text
DEC-3F982AE689AB4A2BA5D4F313A25F4411
```

The identifier is:

- generated for each successful decision
- persisted as the primary key
- returned to the API consumer
- usable for exact audit retrieval
- unique across repeated decisions

Repeated requests for the same customer produce separate decision identifiers.

---

## API Decision Identifier

The public `NBAResponse` JSON contract remains unchanged.

The decision identifier is exposed through the HTTP response header:

```text
X-Decision-ID
```

Example logical response:

```text
HTTP 200

X-Decision-ID: DEC-...

{
    "customer_id": "...",
    "next_best_action": "...",
    "score": ...,
    "eligible": ...,
    "reason_codes": [...],
    "ranked_actions": [...]
}
```

The audit identifier is deliberately kept outside the existing response body to preserve backward compatibility.

---

## Decision Persistence

Audit persistence is implemented in:

```text
src/decision_audit.py
```

The main persistence function is:

```text
persist_decision_audit(...)
```

The function receives an already calculated:

```text
Customer
MembershipContext or None
NBAResponse
```

It does not recalculate the decision.

The stored score, eligibility, reason codes, and ranking therefore represent the decision-system output supplied to the audit layer.

---

## Controlled Audit Retrieval

Audit retrieval is provided by:

```text
get_decision_audit(...)
```

The function retrieves one record using:

```text
decision_id
```

The returned representation includes deserialized:

- selected reason codes
- ranked candidate actions
- customer snapshot
- membership snapshot
- version information

A public audit API endpoint is not required for the current version.

---

## Customer Snapshot

Each successful audit record preserves the decision-relevant Customer model values used at decision time.

The snapshot includes:

```text
customer_id
age
monthly_income
savings_balance
monthly_surplus
has_mortgage
has_credit_card
investment_customer
app_visits_30d
marketing_consent
investment_consent
credit_score_band
preferred_channel
```

The snapshot is persisted as deterministic JSON.

Automated testing confirms that changing the in-memory customer object after persistence does not modify the historical audit record.

---

## Membership Snapshot

When membership context is supplied to decisioning, the audit record preserves:

```text
member_id
membership_status
membership_tier
tenure_days
engagement_events_30d
successful_benefit_redemptions_30d
campaign_sends_30d
campaign_conversions_30d
latest_campaign_response
```

The record also stores:

```text
membership_used = true
```

When no membership context exists:

```text
membership_used = false
membership_snapshot = NULL
```

This distinguishes:

- a decision with membership context
- a decision without membership context

without implying that membership necessarily changed the selected action.

---

## Membership Influence Traceability

Membership relevance reason codes generated by the decisioning layer are preserved in the ranked-action and selected-action evidence.

Examples include:

```text
MEMBERSHIP_RECENT_ENGAGEMENT
MEMBERSHIP_RECENT_CAMPAIGN_CONVERSION
MEMBERSHIP_RECENT_CAMPAIGN_CLICK
MEMBERSHIP_RECENT_CAMPAIGN_OPEN
```

The audit layer does not generate these codes independently.

It records the reason codes produced by the decisioning system.

---

## Ranked Candidate Traceability

Each audit record preserves the complete ranked candidate list.

Every stored candidate contains:

```text
action
score
eligible
reason_codes
```

The order of the stored list matches the decision result supplied to the audit layer.

The selected action is validated against the winning ranked candidate before persistence.

---

## Pre-Persistence Consistency Protection

Before an audit record is inserted, the audit layer validates consistency between the selected decision and the ranked candidate result.

Validation includes:

- customer identity matches
- ranked candidate list is not empty
- selected action matches ranked winner
- selected score matches ranked winner
- selected eligibility matches ranked winner
- selected reason codes match ranked winner

Contradictory decision objects are rejected rather than silently repaired.

---

## Deterministic Serialization

Structured fields are stored using deterministic JSON serialization.

Serialization uses stable key ordering and compact separators.

Structured persisted fields include:

```text
selected_reason_codes_json
ranked_actions_json
customer_snapshot_json
membership_snapshot_json
```

Automated round-trip testing confirms that deserialization preserves the original decision evidence.

---

## Version Traceability

Each audit record contains:

```text
decision_engine_version
model_version
api_version
audit_schema_version
```

Current decision-engine identifier:

```text
decision-engine-v1
```

Current API version:

```text
1.0.0
```

Current audit schema version:

```text
1.0
```

The current membership-aware NBA API does not directly use the synthetic propensity model when producing the audited decision.

Therefore:

```text
model_version = NULL
```

is a valid and explicitly supported state.

The audit layer can preserve a model-version identifier when one is supplied in future model-assisted decision paths.

---

## API Integration

Audit persistence is integrated into:

```text
src/app.py
```

The API path is:

```text
get_customer(...)
        |
        v
get_membership_context(...)
        |
        v
decide_with_membership(...)
        |
        v
persist_api_decision(...)
        |
        v
persist_decision_audit(...)
        |
        v
X-Decision-ID
```

Audit persistence occurs after decision calculation.

This preserves separation between decision logic and decision evidence.

---

## Unknown Customer Behaviour

A validly formatted customer identifier that does not exist continues to return:

```text
HTTP 404
```

No successful audit record is created.

No `X-Decision-ID` header is returned.

---

## Malformed Customer Behaviour

A malformed customer identifier continues to be rejected by FastAPI request validation.

Example:

```text
/nba/INVALID
```

Result:

```text
HTTP 422
```

No successful audit record is created.

No `X-Decision-ID` header is returned.

---

## Non-Member Compatibility

A customer without membership context continues through the original decision path.

Validation confirms:

```text
membership_used = false
membership_snapshot = NULL
```

while preserving:

- selected action
- selected score
- selected eligibility
- selected reason codes
- complete ranked candidate list

Audit integration does not change the non-member recommendation.

---

## Member Compatibility

Customers with membership records retain membership-aware ranking.

The audit layer preserves the resulting membership-enriched scores and reason codes.

Automated real-database testing validates a synthetic ACTIVE PLUS member with:

```text
engagement_events_30d        = 5
campaign_sends_30d           = 1
campaign_conversions_30d     = 1
latest_campaign_response     = CONVERTED
```

The tested membership-aware result selected:

```text
INVESTMENT_INFO
```

with score:

```text
0.93
```

and retained membership influence reason codes.

---

## Real API-to-Audit Reconciliation

Automated reconciliation executes the actual FastAPI decision path against a temporary SQLite database.

The validation process:

```text
1. Create synthetic customer database
2. Make GET /nba/{customer_id}
3. Capture X-Decision-ID
4. Retrieve decision_audits row
5. Compare API response with stored audit evidence
```

Reconciliation verifies exact agreement for:

- customer_id
- selected action
- selected score
- selected eligibility
- selected reason codes
- ranked actions

Both member and non-member paths are validated.

---

## Append-Only Decision History

Repeated requests for the same customer create separate decision records.

Automated testing verifies:

```text
first decision_id != second decision_id
```

and confirms both rows remain stored.

A new decision does not overwrite the previous decision.

---

## Snapshot Immutability

Historical audit evidence is stored as serialized decision-time snapshots.

Later mutation of the source customer object does not change already persisted evidence.

Existing audit rows are not updated by subsequent decisions.

This preserves historical decision evidence.

---

## Audit Data Quality Validation

Audit data-quality validation is implemented in:

```text
src/decision_audit_quality.py
```

The validator evaluates persisted audit evidence rather than recalculating decisions.

Detected conditions include:

```text
MISSING_DECISION_ID
DUPLICATE_DECISION_ID
MISSING_CUSTOMER_ID
MISSING_SELECTED_ACTION
INVALID_SERIALIZED_FIELD
INCOMPLETE_RANKED_ACTIONS
MISSING_MEMBERSHIP_SNAPSHOT
UNEXPECTED_MEMBERSHIP_SNAPSHOT
CUSTOMER_SNAPSHOT_MISMATCH
NO_ELIGIBLE_RANKED_ACTION
SELECTED_ACTION_MISMATCH
SELECTED_SCORE_MISMATCH
SELECTED_ELIGIBILITY_MISMATCH
SELECTED_REASON_CODES_MISMATCH
```

This provides explicit evidence for persisted-record integrity.

---

## Invalid JSON Detection

Automated tests deliberately corrupt structured audit fields.

Examples include:

```text
selected_reason_codes_json = 'not-json'
```

and:

```text
ranked_actions_json = 'not-json'
```

The data-quality validator detects the invalid serialized evidence.

---

## Incomplete Ranked Action Detection

Automated testing deliberately replaces the complete ranked-action structure with incomplete data.

Example:

```json
[
  {
    "action": "SAVINGS_PLAN"
  }
]
```

The validator detects the missing required candidate fields.

---

## Selected Action Integrity

The stored top-level selected action must agree with the persisted winning ranked candidate.

A controlled defect modifies `selected_action` without changing `ranked_actions_json`.

The validator identifies:

```text
SELECTED_ACTION_MISMATCH
```

---

## Score Integrity

The audit layer persists the score produced by decisioning.

It does not independently recompute scoring.

A controlled corruption of the stored selected score is detected as:

```text
SELECTED_SCORE_MISMATCH
```

---

## Reason-Code Integrity

Reason codes are preserved as generated by the decisioning layer.

The audit layer does not silently:

- remove reason codes
- add reason codes
- rewrite reason codes

Controlled corruption of selected reason codes is detected as:

```text
SELECTED_REASON_CODES_MISMATCH
```

---

## Record Count Validation

A dedicated audit-count helper supports validation of persisted audit volume.

Automated coverage verifies:

```text
1 successful request -> 1 audit record
2 repeated successful requests -> 2 audit records
unknown customer -> no successful audit record
malformed request -> no successful audit record
failed persistence -> no successful audit record
```

---

## Transaction Safety

Decision-audit persistence uses SQLite transaction handling.

Automated transaction testing deliberately forces database failure using SQLite triggers.

A failing insert is verified to leave:

```text
0 partial decision audit rows
```

Existing valid audit history remains unchanged after a later failed insert.

---

## Atomic Rollback Validation

A controlled SQLite trigger performs a side-effect insert and then deliberately aborts the decision-audit write.

The test verifies that both the decision audit insert and trigger side effect are rolled back.

Validated result:

```text
decision_audits rows after failure = 0
probe rows after failure           = 0
```

This demonstrates atomic failure behaviour rather than partial persistence.

---

## Fail-Closed API Behaviour

If decision calculation succeeds but audit persistence fails, the API does not return the decision as successfully audited.

The API returns:

```text
HTTP 500
```

with:

```json
{
  "detail": "Decision audit persistence failed"
}
```

and does not return:

```text
X-Decision-ID
```

This behaviour is validated with both mocked persistence failure and a real SQLite failure.

---

## Automated Test Coverage

Decision Audit and Traceability added validation across:

| Area | Added test cases |
| --- | ---: |
| Audit schema | 12 |
| Audit persistence and retrieval | 10 |
| API audit integration | 2 |
| Real API-to-audit reconciliation | 3 |
| Audit data quality | 10 |
| Transaction and failure safety | 4 |
| Release-readiness audit checks | 2 |
| Total added | 43 |

Pre-feature baseline:

```text
317 tests
```

Current validated baseline:

```text
360 tests
```

Net increase:

```text
43 tests
```

---

## Audit Test Family

The principal Decision Audit test modules are:

```text
tests/test_decision_audit_schema.py
tests/test_decision_audit.py
tests/test_decision_audit_quality.py
tests/test_decision_audit_transactions.py
tests/test_api.py
tests/test_api_audit_reconciliation.py
tests/test_release_readiness.py
```

A focused audit/API validation run reached:

```text
45 passed, 1 warning
```

before release-readiness additions.

---

## Release Readiness Integration

Critical audit controls are included in:

```text
tests/test_release_readiness.py
```

The release smoke suite now contains:

```text
10 tests
```

Audit-specific release checks include:

```text
RV-009 successful API decision is audited
RV-010 audit persistence failure blocks success
```

These checks ensure that a release cannot pass smoke validation if core audit persistence or fail-closed behaviour is broken.

---

## Release Validation

Release validation command:

```powershell
.\scripts\run_release_validation.ps1
```

Validated Stage 1 result:

```text
STAGE 1 - RELEASE READINESS SMOKE VALIDATION

10 passed, 1 warning
Smoke exit code: 0
```

Validated Stage 2 result:

```text
STAGE 2 - COMPLETE REGRESSION VALIDATION

360 passed, 1 warning
Regression exit code: 0
```

Final result:

```text
RELEASE RESULT: PASS
Smoke exit code      : 0
Regression exit code : 0
```

JUnit evidence is generated at:

```text
reports/release/release-smoke-junit.xml
reports/release/release-regression-junit.xml
```

Generated reports are excluded from source control.

---

## Known Dependency Warning

The automated suite currently reports one dependency warning from Starlette TestClient / AnyIO:

```text
The anyio.abc.BlockingPortal alias is deprecated.
```

The warning originates from:

```text
starlette/testclient.py
```

It does not currently cause project test failure and remains visible rather than being suppressed.

---

## Continuous Integration Validation

The feature branch is validated by the GitHub Actions workflow:

```text
NBA Regression Validation
```

The workflow:

- installs project dependencies
- generates synthetic customer data
- builds the SQLite customer database
- executes the complete pytest suite
- generates JUnit evidence
- uploads the regression artifact

Decision-audit tests use isolated temporary SQLite databases where required.

This prevents generated audit evidence from contaminating source-controlled project data.

The release-readiness integration checkpoint:

```text
501b953
Add decision audit release readiness checks
```

was validated by:

```text
GitHub Actions run #47
Result: success
```

---

## Generated Data Handling

Generated SQLite decision history is runtime or test evidence.

The project ignore rules already exclude:

```text
data/*.db
data/*.sqlite
data/*.sqlite3
reports/
```

Decision audit data is therefore not committed to the repository.

---

## Regression Protection

The Decision Audit implementation was introduced without removing the existing banking and membership validation scope.

Regression progression:

```text
Membership-complete baseline              317
Audit schema                              329
Audit persistence                         339
API integration                           341
API-to-audit reconciliation               344
Audit data quality                        354
Transaction safety                        358
Release-readiness integration             360
```

Final result:

```text
360 passed
```

---

## Requirement Coverage Summary

Implementation and automated evidence cover:

```text
DAT-001  Unique Decision Identifier
DAT-002  Audit Record Persistence
DAT-003  Customer Identity Traceability
DAT-004  Decision Timestamp
DAT-005  Selected Action Traceability
DAT-006  Ranked Candidate Traceability
DAT-007  Customer Input Snapshot
DAT-008  Membership Context Snapshot
DAT-009  Membership Usage Indicator
DAT-010  Membership Influence Traceability
DAT-011  Eligibility Protection
DAT-012  Decision Engine Version
DAT-013  Model Version Traceability
DAT-014  API Version Traceability
DAT-015  Audit Schema Version
DAT-016  Serialization Integrity
DAT-017  API Decision Identifier Exposure
DAT-018  Unknown Customer Behaviour
DAT-019  Malformed Request Behaviour
DAT-020  Non-Member Compatibility
DAT-021  Member Compatibility
DAT-022  API-to-Audit Reconciliation
DAT-023  Snapshot Immutability
DAT-024  Append-Only Decision History
DAT-025  Deterministic Decision Verification
DAT-026  Audit Referential Integrity
DAT-027  Audit Data Quality
DAT-028  Selected Action Consistency
DAT-029  Score Integrity
DAT-030  Reason-Code Integrity
DAT-031  Read Access for Validation
DAT-032  Audit Record Count Validation
DAT-033  Database Reload Safety
DAT-034  Transaction Safety
DAT-035  Failure Handling
DAT-036  Existing Regression Protection
DAT-037  Release Validation
DAT-038  Synthetic Data Only
DAT-039  Generated Audit Database Handling
DAT-040  Documentation
```

---

## Acceptance Criteria Result

The Decision Audit and Traceability acceptance criteria are validated as follows:

| Acceptance criterion | Result |
| --- | --- |
| Unique decision identifiers | PASS |
| SQLite audit persistence | PASS |
| Customer and membership snapshots | PASS |
| Complete ranked candidate evidence | PASS |
| API-to-audit reconciliation | PASS |
| Append-only history | PASS |
| Member and non-member compatibility | PASS |
| Eligibility and consent protection | PASS |
| Malformed/unknown requests create no successful audit | PASS |
| Persistence failure handled fail-closed | PASS |
| Regression remains green | PASS |
| Release validation passes | PASS |
| Validation documentation completed | PASS |

---

## Validation Conclusion

The Decision Audit and Traceability capability satisfies the defined synthetic-lab requirements for persistent and reconcilable Next Best Action decision evidence.

The implementation provides:

- traceable decision identifiers
- immutable decision-time snapshots
- complete ranked-action evidence
- member and non-member traceability
- API-to-SQLite reconciliation
- audit data-quality controls
- append-only history
- atomic transaction handling
- fail-closed persistence behaviour
- automated release protection

Validated final regression result:

```text
360 passed, 1 known dependency warning
```

Validated release result:

```text
RELEASE RESULT: PASS
```

The capability remains synthetic and is intended for engineering, QA, data-quality, and decision-system validation rather than production regulatory audit certification.
