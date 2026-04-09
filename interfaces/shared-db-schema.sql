-- Shared DB Schema for Config Management
-- Used by: Maker-Checker Framework (Ritwik) + Audit Trail Framework (Anuj)
--
-- IMPORTANT: Follow expand-then-contract for all migrations.
-- Each migration must be idempotent and have a rollback script.
--
-- Owner of pending_changes: Ritwik (maker-checker epic)
-- Owner of config_audit_log: Anuj (auditing epic)

-- ============================================
-- Table: pending_changes (Maker-Checker Framework)
-- ============================================
CREATE TABLE IF NOT EXISTS pending_changes (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    org_id INT NOT NULL,
    entity_type VARCHAR(50) NOT NULL COMMENT 'ConfigEntityType enum value',
    entity_id INT NOT NULL COMMENT '0 for CREATE operations',
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING_APPROVAL' COMMENT 'ConfigStatus enum value',
    change_payload TEXT NOT NULL COMMENT 'JSON of proposed new state',
    previous_payload TEXT COMMENT 'JSON of current live state (null for CREATE)',
    submitted_by INT NOT NULL,
    submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_by INT,
    reviewed_at TIMESTAMP NULL,
    review_comment VARCHAR(500),
    last_action VARCHAR(30) COMMENT 'ApprovalAction enum value',
    INDEX idx_pending_org_entity (org_id, entity_type, status),
    INDEX idx_pending_entity (entity_type, entity_id),
    INDEX idx_pending_submitted (submitted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- Table: config_audit_log (Audit Trail Framework)
-- ============================================
CREATE TABLE IF NOT EXISTS config_audit_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    org_id INT NOT NULL,
    entity_type VARCHAR(50) NOT NULL COMMENT 'ConfigEntityType enum value',
    entity_id INT NOT NULL,
    field_name VARCHAR(100) COMMENT 'Null means full-entity change',
    old_state TEXT COMMENT 'JSON of previous state (null for CREATE)',
    new_state TEXT COMMENT 'JSON of new state',
    changed_by INT NOT NULL,
    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    change_source VARCHAR(30) NOT NULL COMMENT 'ChangeSource enum value',
    pending_change_id BIGINT COMMENT 'FK to pending_changes (null if not via maker-checker)',
    INDEX idx_audit_org_entity (org_id, entity_type, entity_id, changed_at),
    INDEX idx_audit_org_type (org_id, entity_type, changed_at),
    INDEX idx_audit_actor (changed_by, changed_at),
    INDEX idx_audit_pending (pending_change_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
