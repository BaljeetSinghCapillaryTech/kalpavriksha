package com.capillary.shopbook.points.services.audit;

import com.capillary.shopbook.points.entity.ChangeSource;
import com.capillary.shopbook.points.entity.ConfigAuditEntry;
import com.capillary.shopbook.points.entity.ConfigEntityType;

import java.util.List;

/**
 * Shared Module: Audit Trail Framework
 * Owner: Anuj (auditing epic)
 *
 * Entity-agnostic audit trail service. Records configuration changes
 * with full old/new state capture as JSON. Supports filtering, pagination,
 * and CSV export.
 *
 * Integration: Called by MakerCheckerService on APPROVE action.
 * Also called directly by any service for non-approval changes.
 */
public interface ConfigAuditService {

    /**
     * Record a config change.
     *
     * Called automatically by MakerCheckerService on APPROVE,
     * or manually by services for direct edits.
     *
     * @param orgId          org context (tenant isolation)
     * @param entityType     what kind of entity
     * @param entityId       which entity changed
     * @param fieldName      specific field that changed (null for full-entity changes)
     * @param oldState       JSON of previous state (null for CREATE operations)
     * @param newState       JSON of new state
     * @param changedBy      user ID who made or approved the change
     * @param changeSource   how the change happened (DIRECT_EDIT, MAKER_CHECKER_APPROVE, etc.)
     * @return the created ConfigAuditEntry
     */
    ConfigAuditEntry record(int orgId, ConfigEntityType entityType, int entityId,
                             String fieldName, String oldState, String newState,
                             int changedBy, ChangeSource changeSource);

    /**
     * Query audit history for a specific entity.
     *
     * @param orgId       org context
     * @param entityType  entity type
     * @param entityId    entity ID
     * @param filter      query filter (date range, actor, field, etc.)
     * @return list of audit entries, sorted by changedAt DESC
     */
    List<ConfigAuditEntry> getHistory(int orgId, ConfigEntityType entityType,
                                       int entityId, AuditQueryFilter filter);

    /**
     * Query audit history across all entities of a type.
     * Used for the audit listing page.
     *
     * @param orgId       org context
     * @param entityType  entity type (nullable = all types)
     * @param filter      query filter
     * @param offset      pagination offset
     * @param limit       pagination limit
     * @return paginated list of audit entries
     */
    List<ConfigAuditEntry> listChanges(int orgId, ConfigEntityType entityType,
                                        AuditQueryFilter filter, int offset, int limit);

    /**
     * Count total audit entries matching filter (for pagination).
     */
    long countChanges(int orgId, ConfigEntityType entityType, AuditQueryFilter filter);

    /**
     * Export audit history as CSV bytes.
     *
     * @param orgId       org context
     * @param entityType  entity type
     * @param filter      query filter
     * @return CSV content as byte array
     */
    byte[] exportCsv(int orgId, ConfigEntityType entityType, AuditQueryFilter filter);
}
