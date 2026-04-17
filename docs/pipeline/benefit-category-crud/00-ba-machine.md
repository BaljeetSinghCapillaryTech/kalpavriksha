---
feature: Benefit Category CRUD
ticket: CAP-185145
phase: 1
date: 2026-04-18
source_brd: Tiers_Benefits_PRD_v3_Full.pdf
ba_doc: 00-ba.md

scope:
  in:
    - Category CRUD (create, read, list, update, soft-delete)
    - Instance CRUD (create link, read, list, soft-delete)
    - Cascade deactivation (category → instances) in single txn
    - Uniqueness per program (program_id, name)
    - Multi-tenancy (org_id + program_id on new tables)
    - Audit metadata (created_*, updated_*)
  out:
    - 9 category types (WELCOME_GIFT, EARN_POINTS, etc.)
    - triggerEvent field and derivation
    - Per-type value schemas on instances
    - Value payload on instances (no points, amount, voucher template)
    - Maker-checker approval workflow
    - Hard-delete endpoint
    - aiRa natural-language mapping
    - Matrix View UI
    - Subscription benefit picker
    - Schema changes to legacy Benefits table

entities:
  BenefitCategory:
    kind: new
    fields:
      - {name: id, type: long, role: pk}
      - {name: org_id, type: long, role: tenant_scope, indexed: true}
      - {name: program_id, type: long, role: feature_scope, indexed: true}
      - {name: name, type: string, unique_with: [program_id]}
      - {name: category_type, type: enum, values: [BENEFITS], mvp_single_value: true, reason: "D-06 — forward extensibility"}
      - {name: tier_applicability, type: "collection<long>", role: "set of allowed tier_ids", physical_form_tbd: true}
      - {name: is_active, type: boolean, default: true}
      - {name: created_at, type: timestamp, audit: true}
      - {name: created_by, type: long, audit: true}
      - {name: updated_at, type: timestamp, audit: true}
      - {name: updated_by, type: long, audit: true}
  BenefitInstance:
    kind: new
    fields:
      - {name: id, type: long, role: pk}
      - {name: org_id, type: long, role: tenant_scope, indexed: true}
      - {name: program_id, type: long, role: feature_scope, indexed: true}
      - {name: category_id, type: long, role: fk, references: "benefit_category.id", indexed: true}
      - {name: tier_id, type: long, role: fk, references: "existing tier table", indexed: true}
      - {name: is_active, type: boolean, default: true}
      - {name: created_at, type: timestamp, audit: true}
      - {name: created_by, type: long, audit: true}
      - {name: updated_at, type: timestamp, audit: true}
      - {name: updated_by, type: long, audit: true}
    unique_constraint_candidate: "(category_id, tier_id) across active+inactive — final decision Phase 7"
    excluded_fields_with_reason:
      - field: trigger_event
        reason: "D-07 — not modelled"
      - field: value / amount / points / voucher_template_id / json_config
        reason: "D-09 — instance carries no value payload"
      - field: lifecycle_state / approval_status
        reason: "D-05 — maker-checker descoped"

legacy_coexistence:
  legacy_entity: "Benefits (emf-parent)"
  relationship: strict_coexistence
  forbidden:
    - "FK from new entities to legacy Benefits"
    - "Column added to legacy benefits table"
    - "New code imports legacy Benefits class"
  glossary_clarification_required: true
  reason: "D-12 — zero blast radius on legacy"

user_stories:
  - {id: US-1, epic: E1, persona: Maya, action: "create Benefit Category", priority: P0}
  - {id: US-2, epic: E1, persona: Maya, action: "list Benefit Categories in my program", priority: P0}
  - {id: US-3, epic: E1, persona: Maya, action: "view single Benefit Category details", priority: P0}
  - {id: US-4, epic: E1, persona: Maya, action: "update Benefit Category (name, tierApplicability)", priority: P0}
  - {id: US-5, epic: E1, persona: Maya, action: "deactivate Benefit Category (cascades to instances)", priority: P0}
  - {id: US-6, epic: E1, persona: Maya, action: "reactivate Benefit Category (instances stay inactive)", priority: P1}
  - {id: US-7, epic: E2, persona: Maya, action: "create Benefit Instance (link category → tier)", priority: P0}
  - {id: US-8, epic: E2, persona: Maya, action: "list Benefit Instances for a Category", priority: P0}
  - {id: US-9, epic: E2, persona: Maya, action: "deactivate Benefit Instance", priority: P0}
  - {id: US-10, epic: E2, persona: Maya, action: "reactivate Benefit Instance (only if parent active)", priority: P1}

acceptance_criteria:
  in_scope_reinterpreted:
    - id: AC-BC01'
      covers: US-1
      summary: "Category creation with name, tierApplicability, categoryType=BENEFITS; 409 on duplicate name; 400 on empty/invalid tierApplicability; no DRAFT/trigger derivation"
    - id: AC-BC02
      covers: US-1
      summary: "Name uniqueness per program (case-insensitive); same name permitted in different program"
    - id: AC-BC03'
      covers: US-7
      summary: "Instance links active Category to Tier in its applicability; 409 on duplicate (category,tier); 400 if tier not in applicability or category inactive"
    - id: AC-BC12
      covers: US-5
      summary: "Category deactivation cascades to all instances in same DB transaction; reactivation does NOT auto-reactivate instances"
  out_of_scope:
    - {id: AC-BC07, reason: "Maker-checker descoped — D-05"}
    - {id: AC-BC08, reason: "Maker-checker descoped — D-05"}
    - {id: AC-BC09, reason: "aiRa out of scope — D-03"}
    - {id: AC-BC10, reason: "Matrix View out of scope — D-03"}
    - {id: AC-BC11, reason: "Matrix View out of scope — D-03"}
    - {id: AC-BC13, reason: "Subscription picker out of scope — D-03"}
  missing_in_brd:
    - {ids: [AC-BC04, AC-BC05, AC-BC06], status: "OQ-4 — unknown if intentional gap"}

functional_requirements:
  - {id: FR-1, text: "REST endpoints for Category CRUD"}
  - {id: FR-2, text: "REST endpoints for Instance CRUD"}
  - {id: FR-3, text: "Name uniqueness enforced at DB + service layer"}
  - {id: FR-4, text: "Instance.tier_id must be in parent category's tierApplicability"}
  - {id: FR-5, text: "Instance creation rejected under inactive parent category"}
  - {id: FR-6, text: "Category deactivation cascades to instances in one transaction"}
  - {id: FR-7, text: "Category reactivation does NOT auto-reactivate instances"}
  - {id: FR-8, text: "All reads/writes scoped by auth context org_id"}
  - {id: FR-9, text: "Audit metadata on every mutation"}
  - {id: FR-10, text: "No hard-delete in MVP"}

non_functional_requirements:
  - {id: NFR-1, area: performance, target: "Category list P95 <500ms up to 200 rows; Instance list P95 <500ms up to 1000 rows per program"}
  - {id: NFR-2, area: availability, target: "Inherits Capillary platform SLA"}
  - {id: NFR-3, area: security, target: "Tenant-scoped; no cross-org leak via ID guess"}
  - {id: NFR-4, area: auditability, target: "updated_by set from auth context on every mutation"}
  - {id: NFR-5, area: consistency, target: "Cascade deactivation transactional"}
  - {id: NFR-6, area: idempotency, target: "Re-activate active = no-op; deactivate inactive = no-op"}
  - {id: NFR-7, area: observability, target: "Structured logs + metric counters on all mutations"}

key_decisions:
  - {id: D-03, summary: "Scope = Category CRUD + Instance linking; aiRa / Matrix / Subscription out"}
  - {id: D-04, summary: "Single explicit is_active flag; no 'no-instances-means-inactive' derivation"}
  - {id: D-05, summary: "Maker-checker DESCOPED for MVP"}
  - {id: D-06, summary: "Single categoryType value 'BENEFITS' for MVP; column retained"}
  - {id: D-07, summary: "triggerEvent field dropped entirely"}
  - {id: D-08, summary: "Benefit awarding is external — this feature is config-only"}
  - {id: D-09, summary: "BenefitInstance carries no value payload"}
  - {id: D-10, summary: "categoryType column kept despite single value (YAGNI accepted)"}
  - {id: D-11, summary: "BRD §3, §5.3, §5.4, AC-BC01 trigger clause deferred to future"}
  - {id: D-12, summary: "Strict coexistence with legacy Benefits — zero FK/column changes"}
  - {id: D-13, summary: "Soft-delete only; no DELETE HTTP verb in MVP"}
  - {id: D-14, summary: "Category deactivation cascades to instances in single txn; reactivation does not auto-reactivate"}
  - {id: D-15, summary: "categoryName unique per program (program_id, name)"}
  - {id: D-16, summary: "New tables carry org_id + program_id; queries scoped by auth"}

open_questions:
  - {id: OQ-4, text: "AC-BC04/05/06 missing in BRD — intentional?", blocking: false, owner: product}
  - {id: OQ-12, text: "BRD epic numbering E2 vs E4 — which is the real epic?", blocking: false, owner: product}
  - {id: OQ-15, text: "Which existing system consumes this config and applies benefits?", blocking: "phase-6", owner: "engineering — Phase 5 research"}

constraints:
  - {id: C-01, text: "Java / Spring / Thrift / MySQL stack"}
  - {id: C-02, text: "5 repos: kalpavriksha, emf-parent, intouch-api-v3, cc-stack-crm, thrift-ifaces-pointsengine-rules"}
  - {id: C-03, text: "Category is metadata only — holds NO reward values"}
  - {id: C-04, text: "categoryName unique per program (not global, not per-org)"}
  - {id: C-08, text: "Data model: single is_active flag; no lifecycle state; no approval_request table"}
  - {id: C-09, text: "All CRUD operations immediate — no approval gate"}
  - {id: C-10, text: "BenefitInstance: no value columns"}
  - {id: C-11, text: "BenefitCategory: no trigger_event column"}
  - {id: C-12, text: "Awarding logic not in this feature — external reader applies benefits"}
  - {id: C-13, text: "BRD §3/§5.3/§5.4/AC-BC01 trigger are deferred; BA doc calls this out explicitly"}
  - {id: C-14, text: "No schema changes to existing Benefits table"}
  - {id: C-15, text: "API must NOT expose DELETE verb"}
  - {id: C-16, text: "Deactivation cascade is transactional"}
  - {id: C-17, text: "Category reactivation does not auto-reactivate instances"}
  - {id: C-18, text: "UNIQUE (program_id, name) DB constraint + service pre-check"}
  - {id: C-19, text: "New tables carry org_id + program_id; queries always org-scoped"}

codebase_verification_targets:
  - {claim: "No BenefitCategory or BenefitInstance entity exists today", repo: emf-parent, confidence: C6, phase_to_verify: 5}
  - {claim: "Existing Benefits entity uses BenefitsType = {VOUCHER, POINTS} only", repo: emf-parent, confidence: C6, phase_to_verify: 5}
  - {claim: "benefits.sql has promotion_id NOT NULL", repo: intouch-api-v3, confidence: C6, phase_to_verify: 5}
  - {claim: "EMF tier event forest (TierRenewedHelper, TierUpgradeHelper) is the likely consumer", repo: emf-parent, confidence: C3, phase_to_verify: 5, blocking_for: "phase-6-api-freeze"}
  - {claim: "Capillary platform pattern uses org_id on core tables", repos: all, confidence: C6, phase_to_verify: 5}

ready_for_phase: 2
ready_for_phase_name: "Critic + Gap Analysis"
---
