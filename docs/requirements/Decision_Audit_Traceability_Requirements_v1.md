# Decision Audit and Traceability Requirements v1

## Purpose

This specification defines requirements for auditable and traceable Next Best Action decisions in the synthetic banking Decisioning Lab.

The capability must make it possible to determine:

- which customer received a decision
- when the decision was produced
- which action was selected
- which alternatives were evaluated
- which eligibility and scoring results were used
- which reason codes contributed to the decision
- whether membership context influenced ranking
- which decision/model versions produced the result
- whether the persisted audit record matches the API decision

All data in this project is synthetic.

---

## Scope

The Decision Audit and Traceability capability will add:

- persistent decision audit records
- decision identifiers
- customer-input snapshots
- membership-context snapshots
- ranked-action snapshots
- decision/model version traceability
- API-to-audit reconciliation
- audit data-quality validation
- deterministic decision verification
- release-gate coverage

The initial version does not provide regulatory compliance certification or production banking audit infrastructure.

---

## DAT-001 - Unique Decision Identifier

Every successfully completed Next Best Action request must receive a unique decision identifier.

The identifier must:

- be non-empty
- be unique across decision records
- be persisted with the audit record
- allow an API decision to be reconciled to its stored audit record

---

## DAT-002 - Audit Record Persistence

Every successfully produced Next Best Action decision must create one persisted audit record.

The audit record must be stored in SQLite.

A successful decision must not be returned as audited unless persistence succeeds.

---

## DAT-003 - Customer Identity Traceability

Each audit record must contain the customer identifier used for decisioning.

The persisted customer identifier must exactly match the customer identifier used by the API request.

---

## DAT-004 - Decision Timestamp

Each audit record must contain a decision timestamp.

The timestamp must:

- represent the time the decision was produced
- use a consistent machine-readable format
- be persisted with the audit record

---

## DAT-005 - Selected Action Traceability

Each audit record must contain:

- selected action
- selected score
- selected eligibility state
- selected reason codes

These values must reconcile exactly with the decision returned by the API.

---

## DAT-006 - Ranked Candidate Traceability

Each audit record must preserve the complete ranked candidate set evaluated for the decision.

For every candidate action, the stored representation must include:

- action name
- score
- eligibility state
- reason codes

The ordering must match the final decision ranking.

---

## DAT-007 - Customer Input Snapshot

The audit record must preserve the customer attributes used by the decision engine.

The snapshot must contain the decision-relevant Customer model fields available at decision time.

The audit snapshot must represent the values used for that decision rather than values retrieved later from a potentially changed customer record.

---

## DAT-008 - Membership Context Snapshot

When membership context is available, the audit record must preserve the membership context used during decisioning.

This includes the decision-relevant MembershipContext fields.

When no membership context exists, the audit record must clearly represent that membership enrichment was not used.

---

## DAT-009 - Membership Usage Indicator

Each audit record must contain an explicit indicator showing whether membership context was supplied to the membership-aware decisioning layer.

Membership existence alone must not imply that ranking was changed.

---

## DAT-010 - Membership Influence Traceability

When membership relevance signals modify candidate scores, the persisted ranked-action snapshot must retain the resulting membership reason codes.

Examples include:

- MEMBERSHIP_RECENT_ENGAGEMENT
- MEMBERSHIP_RECENT_CAMPAIGN_CONVERSION
- MEMBERSHIP_RECENT_CAMPAIGN_CLICK
- MEMBERSHIP_RECENT_CAMPAIGN_OPEN

The audit layer must not create or infer reason codes that were not produced by the decisioning layer.

---

## DAT-011 - Eligibility Protection

The audit capability must not change existing eligibility rules.

Audit persistence must not:

- create eligibility
- override marketing consent
- override investment consent
- alter product constraints
- make an ineligible action selectable

The audit layer records decisions; it does not determine them.

---

## DAT-012 - Decision Engine Version

Each audit record must contain a decision-engine version.

The version must identify the decision logic responsible for producing the recorded decision.

---

## DAT-013 - Model Version Traceability

When model-assisted scoring contributes to decisioning, the applicable model version must be traceable.

The audit record must preserve the relevant model-version identifier where available.

If no model version contributes to a decision, the stored representation must explicitly support that state.

---

## DAT-014 - API Version Traceability

Each audit record must contain the API/application version associated with the decision request.

This supports comparison of decisions produced by different application releases.

---

## DAT-015 - Audit Schema Version

Each audit record must contain an audit-schema version.

The version allows future changes to the stored audit structure to remain distinguishable from earlier records.

---

## DAT-016 - Serialization Integrity

Structured audit fields must be persisted in a deterministic machine-readable representation.

Structured fields include:

- selected reason codes
- ranked actions
- customer snapshot
- membership snapshot

Serialization and deserialization must preserve the original decision information.

---

## DAT-017 - API Decision Identifier Exposure

A successfully audited API decision must expose its decision identifier to the API consumer.

The identifier may be exposed without changing the existing NBAResponse JSON contract.

The initial implementation should prefer an HTTP response header:

X-Decision-ID

This keeps the existing decision response body backward compatible.

---

## DAT-018 - Unknown Customer Behaviour

A request for an unknown customer must continue to return the existing not-found response.

A customer-not-found response must not create a successful decision audit record.

---

## DAT-019 - Malformed Request Behaviour

A malformed customer identifier rejected by API validation must not create a successful decision audit record.

---

## DAT-020 - Non-Member Compatibility

Customers without membership records must continue through the original banking decisioning path.

Their audit record must:

- show that membership context was not used
- preserve the base decision
- preserve the complete ranked candidate set

---

## DAT-021 - Member Compatibility

Customers with membership records must retain the existing membership-aware decision behaviour.

Audit persistence must not alter:

- base banking scores
- membership relevance adjustments
- candidate ordering
- selected action

---

## DAT-022 - API-to-Audit Reconciliation

Automated validation must prove that a decision returned by the API reconciles to its stored audit record.

At minimum, reconciliation must compare:

- customer_id
- selected action
- selected score
- eligibility
- reason codes
- ranked actions

---

## DAT-023 - Snapshot Immutability

An existing audit record must represent the historical decision as originally produced.

Later changes to customer data, membership data, model configuration, or decision logic must not silently alter previously persisted audit records.

---

## DAT-024 - Append-Only Decision History

Repeated decisions for the same customer must create separate decision records.

A new decision must not overwrite a prior decision.

This allows historical comparison of decisions across time.

---

## DAT-025 - Deterministic Decision Verification

For identical deterministic decision inputs and the same decision/model versions, the decision content must remain reproducible.

Different audit identifiers and timestamps are expected for separate executions.

---

## DAT-026 - Audit Referential Integrity

Audit records must reference valid customers for successful decisions.

The SQLite schema must enforce or independently validate the customer relationship.

---

## DAT-027 - Audit Data Quality

Automated validation must detect invalid audit data including:

- missing decision identifiers
- duplicate decision identifiers
- missing customer identifiers
- missing selected actions
- invalid serialized structured fields
- incomplete ranked-action snapshots
- inconsistent selected-action data

---

## DAT-028 - Selected Action Consistency

The selected action stored at the audit-record level must match the first eligible winning action represented by the persisted decision result.

The audit layer must detect contradictory stored decision information.

---

## DAT-029 - Score Integrity

Persisted scores must preserve the values produced by the decisioning layer.

Audit persistence must not independently recalculate scores.

---

## DAT-030 - Reason-Code Integrity

Persisted reason codes must preserve the reason codes generated by the decisioning system.

The audit layer must not silently remove, add, or rewrite decision reason codes.

---

## DAT-031 - Read Access for Validation

The repository layer must provide a controlled method for retrieving an audit record by decision identifier.

This capability is required for automated reconciliation and test validation.

A public audit API endpoint is not required for v1.

---

## DAT-032 - Audit Record Count Validation

Automated tests must verify expected audit-record creation.

Examples include:

- one successful decision -> one new audit record
- repeated successful decisions -> multiple audit records
- unknown customer -> no successful audit record
- malformed request -> no successful audit record

---

## DAT-033 - Database Reload Safety

Creating or initializing the audit schema must not delete valid existing audit history unless explicitly requested by test setup.

Schema initialization must be safe to execute repeatedly.

---

## DAT-034 - Transaction Safety

A decision audit record must be persisted atomically.

Partial audit records must not remain after persistence failure.

---

## DAT-035 - Failure Handling

If audit persistence fails after a decision has been calculated, the API must fail closed rather than falsely representing the decision as successfully audited.

The failure behaviour must be testable.

---

## DAT-036 - Existing Regression Protection

All existing banking, membership, API, model, reconciliation, performance, and release-readiness tests must continue to pass unless an intentional contract extension is documented.

The established baseline before Decision Audit and Traceability is:

317 automated tests passing

---

## DAT-037 - Release Validation

Decision audit and traceability tests must become part of the complete regression suite.

Critical audit-integrity checks should also be represented in release-readiness validation where appropriate.

---

## DAT-038 - Synthetic Data Only

The Decision Audit and Traceability capability must use only synthetic customer and membership information.

No production banking, customer, payment, or membership information may be introduced.

---

## DAT-039 - Generated Audit Database Handling

Generated SQLite audit data is runtime/test evidence and must not be committed to source control.

Existing database ignore rules should continue to protect generated databases.

---

## DAT-040 - Documentation

The implementation must include validation documentation describing:

- audit schema
- persistence behaviour
- API integration
- traceability fields
- reconciliation evidence
- data-quality controls
- automated test coverage
- release-validation result

---

## Acceptance Criteria

The Decision Audit and Traceability capability is considered complete when:

1. successful NBA decisions receive unique decision identifiers
2. decision records are persisted to SQLite
3. customer and membership decision inputs are snapshotted
4. complete ranked candidate decisions are retained
5. API responses can be reconciled to stored audit records
6. historical decisions are append-only
7. non-member and member decision behaviour remains unchanged
8. eligibility and consent controls remain authoritative
9. malformed and unknown-customer requests do not create successful decision records
10. persistence failure is handled fail-closed
11. automated regression remains green
12. release validation passes
13. implementation and validation documentation are complete
