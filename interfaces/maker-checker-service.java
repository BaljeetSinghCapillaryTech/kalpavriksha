package com.capillary.shopbook.points.services.makerchecker;

import com.capillary.shopbook.points.entity.ApprovalAction;
import com.capillary.shopbook.points.entity.ConfigEntityType;
import com.capillary.shopbook.points.entity.ConfigStatus;
import com.capillary.shopbook.points.entity.PendingChange;
import com.fasterxml.jackson.databind.JsonNode;

import java.util.List;

/**
 * Shared Module: Maker-Checker Framework
 * Owner: Ritwik (maker-checker epic)
 *
 * Entity-agnostic approval workflow service. Works with any ConfigEntityType.
 * Consumers call submitForApproval() when creating/editing config entities
 * with maker-checker enabled. Approvers call review() to approve/reject.
 *
 * Integration: On APPROVE, automatically calls ConfigAuditService.record()
 * with change_source = MAKER_CHECKER_APPROVE.
 */
public interface MakerCheckerService {

    /**
     * Submit a config change for approval. Creates a PendingChange record
     * with status = PENDING_APPROVAL.
     *
     * @param orgId          org context (tenant isolation)
     * @param entityType     what kind of entity (TIER, BENEFIT, etc.)
     * @param entityId       the ID of the entity being changed (0 for CREATE operations)
     * @param changePayload  JSON representation of the proposed new state
     * @param submittedBy    user ID of the submitter
     * @return the created PendingChange record
     */
    PendingChange submitForApproval(int orgId, ConfigEntityType entityType,
                                     int entityId, String changePayload, int submittedBy);

    /**
     * Review a pending change.
     *
     * @param pendingChangeId  ID of the pending change record
     * @param action           APPROVE, REJECT, or REQUEST_CHANGES
     * @param reviewedBy       user ID of the reviewer
     * @param comment          mandatory for REJECT and REQUEST_CHANGES; optional for APPROVE
     * @return updated PendingChange with new status
     * @throws IllegalStateException if the transition is invalid
     * @throws IllegalArgumentException if comment is missing for REJECT/REQUEST_CHANGES
     */
    PendingChange review(long pendingChangeId, ApprovalAction action,
                          int reviewedBy, String comment);

    /**
     * List pending changes for an org, filterable by entity type and status.
     *
     * @param orgId       org context
     * @param entityType  filter by entity type (nullable = all types)
     * @param status      filter by status (nullable = all statuses)
     * @param offset      pagination offset
     * @param limit       pagination limit
     * @return list of matching PendingChange records
     */
    List<PendingChange> listPendingChanges(int orgId, ConfigEntityType entityType,
                                            ConfigStatus status, int offset, int limit);

    /**
     * Validate that a status transition is allowed.
     * Throws IllegalStateException if not.
     *
     * Valid transitions:
     *   DRAFT -> SUBMIT_FOR_APPROVAL -> PENDING_APPROVAL
     *   PENDING_APPROVAL -> APPROVE -> ACTIVE
     *   PENDING_APPROVAL -> REJECT -> DRAFT
     *   PENDING_APPROVAL -> REQUEST_CHANGES -> DRAFT
     *   ACTIVE -> STOP -> STOPPED
     */
    void validateTransition(ConfigStatus currentStatus, ApprovalAction action);

    /**
     * Get the diff between current live state and proposed change.
     *
     * @param pendingChangeId ID of the pending change
     * @return JSON diff (field-level old/new values)
     */
    JsonNode getDiff(long pendingChangeId);
}
