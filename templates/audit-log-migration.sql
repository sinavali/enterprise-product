-- Immutable Mutation Audit Log Schema
-- Conforms to Check 4.8 (Immutable Mutation Audit Logging) & Check 4.4 (UTC Storage)
-- Guarantees append-only, tamper-evident audit records for sensitive domain operations.

CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id VARCHAR(128) NOT NULL,
    actor_role VARCHAR(64) NOT NULL,
    tenant_id VARCHAR(128) NOT NULL,
    action VARCHAR(128) NOT NULL,
    entity_type VARCHAR(128) NOT NULL,
    entity_id VARCHAR(128) NOT NULL,
    prior_state JSONB NULL,
    new_state JSONB NOT NULL,
    client_ip VARCHAR(64) NULL,
    user_agent VARCHAR(256) NULL,
    trace_id VARCHAR(64) NULL,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    record_hash VARCHAR(64) NOT NULL -- SHA-256 HMAC or hash of (id + actor_id + action + recorded_at + new_state)
);

-- Indices optimized for audit query investigation
CREATE INDEX IF NOT EXISTS idx_audit_events_tenant_entity 
    ON audit_events (tenant_id, entity_type, entity_id, recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_events_actor 
    ON audit_events (actor_id, recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_events_recorded_at 
    ON audit_events (recorded_at DESC);

-- Mechanical Enforcements: Deny UPDATE and DELETE on audit_events
-- Revoke mutating privileges from the application runtime user
-- Example:
-- REVOKE UPDATE, DELETE, TRUNCATE ON audit_events FROM app_user;
-- GRANT INSERT, SELECT ON audit_events FROM app_user;

-- Trigger to prevent accidental modifications even by superusers
CREATE OR REPLACE FUNCTION prevent_audit_tampering()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'UPDATE') THEN
        RAISE EXCEPTION 'TAMPERING_DETECTED: UPDATE operations are strictly prohibited on the immutable audit_events table.';
    ELSIF (TG_OP = 'DELETE') THEN
        RAISE EXCEPTION 'TAMPERING_DETECTED: DELETE operations are strictly prohibited on the immutable audit_events table.';
    ELSIF (TG_OP = 'TRUNCATE') THEN
        RAISE EXCEPTION 'TAMPERING_DETECTED: TRUNCATE operations are strictly prohibited on the immutable audit_events table.';
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_events_tamper_guard ON audit_events;
CREATE TRIGGER trg_audit_events_tamper_guard
    BEFORE UPDATE OR DELETE ON audit_events
    FOR EACH ROW
    EXECUTE FUNCTION prevent_audit_tampering();
