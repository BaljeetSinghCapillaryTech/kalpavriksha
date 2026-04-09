/**
 * Shared Thrift IDL for config management shared modules.
 * Used by Maker-Checker Framework and Audit Trail Framework.
 *
 * Owner: Ritwik (maker-checker enums/structs) + Anuj (audit enums/structs)
 * Consumers: tier-category, tier-benefits, supplementary-partner-program
 *
 * EXPAND-CONTRACT RULE: Only ADD methods and optional fields.
 * Never remove existing methods. Mark deprecated methods with comments.
 */

namespace java com.capillary.shopbook.points.entity

enum ConfigEntityType {
    TIER = 1,
    BENEFIT = 2,
    BENEFIT_CATEGORY = 3,
    SUPPLEMENTARY_PARTNER_PROGRAM = 4
}

enum ConfigStatus {
    DRAFT = 1,
    PENDING_APPROVAL = 2,
    ACTIVE = 3,
    STOPPED = 4
}

enum ApprovalAction {
    SUBMIT_FOR_APPROVAL = 1,
    APPROVE = 2,
    REJECT = 3,
    REQUEST_CHANGES = 4
}

enum ChangeSource {
    DIRECT_EDIT = 1,
    MAKER_CHECKER_APPROVE = 2,
    IMPORT = 3,
    AIRA = 4,
    SYSTEM = 5
}

struct PendingChangeRecord {
    1: required i64 id;
    2: required i32 orgId;
    3: required ConfigEntityType entityType;
    4: required i32 entityId;
    5: required ConfigStatus status;
    6: required string changePayload;
    7: optional string previousPayload;
    8: required i32 submittedBy;
    9: required i64 submittedAtMillis;
    10: optional i32 reviewedBy;
    11: optional i64 reviewedAtMillis;
    12: optional string reviewComment;
    13: optional ApprovalAction lastAction;
}

struct ConfigAuditRecord {
    1: required i64 id;
    2: required i32 orgId;
    3: required ConfigEntityType entityType;
    4: required i32 entityId;
    5: optional string fieldName;
    6: optional string oldState;
    7: optional string newState;
    8: required i32 changedBy;
    9: required i64 changedAtMillis;
    10: required ChangeSource changeSource;
    11: optional i64 pendingChangeId;
}
