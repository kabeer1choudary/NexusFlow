HISTORY_FUNCTION = """
CREATE OR REPLACE FUNCTION nxflow_resource_audit() RETURNS trigger AS $$
DECLARE
    v_actor text;
    v_source text;
    v_before jsonb;
    v_after jsonb;
    v_delta jsonb;
    v_id uuid;
    v_version integer;
    v_change text;
BEGIN
    v_actor := coalesce(current_setting('nxflow.actor', true), 'system');
    v_source := coalesce(current_setting('nxflow.source', true), 'api');

    IF TG_OP = 'DELETE' THEN
        v_before := to_jsonb(OLD);
        v_after := NULL;
        v_id := OLD.id;
        v_version := OLD.version;
        v_change := 'delete';
    ELSIF TG_OP = 'INSERT' THEN
        v_before := NULL;
        v_after := to_jsonb(NEW);
        v_id := NEW.id;
        v_version := NEW.version;
        v_change := 'create';
    ELSE
        v_before := to_jsonb(OLD);
        v_after := to_jsonb(NEW);
        v_id := NEW.id;
        v_version := NEW.version;
        v_change := 'update';

        SELECT jsonb_object_agg(k, jsonb_build_object('before', v_before->k, 'after', v_after->k))
        INTO v_delta
        FROM (
            SELECT jsonb_object_keys(v_before) AS k
            UNION
            SELECT jsonb_object_keys(v_after)
        ) AS keys
        WHERE v_before->k IS DISTINCT FROM v_after->k;
    END IF;

    INSERT INTO resource_history
        (resource_id, version, change_type, actor, source, before, after, delta)
    VALUES
        (v_id, v_version, v_change, v_actor, v_source, v_before, v_after, v_delta);

    RETURN NULL;
END;
$$ LANGUAGE plpgsql
"""

IMMUTABLE_FUNCTION = """
CREATE OR REPLACE FUNCTION nxflow_history_immutable() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'resource_history is append-only';
END;
$$ LANGUAGE plpgsql
"""

TRIGGER_STATEMENTS = [
    HISTORY_FUNCTION,
    IMMUTABLE_FUNCTION,
    "DROP TRIGGER IF EXISTS trg_resources_audit ON resources",
    "CREATE TRIGGER trg_resources_audit AFTER INSERT OR UPDATE OR DELETE ON resources "
    "FOR EACH ROW EXECUTE FUNCTION nxflow_resource_audit()",
    "DROP TRIGGER IF EXISTS trg_history_immutable ON resource_history",
    "CREATE TRIGGER trg_history_immutable BEFORE UPDATE OR DELETE ON resource_history "
    "FOR EACH ROW EXECUTE FUNCTION nxflow_history_immutable()",
    "REVOKE UPDATE, DELETE ON resource_history FROM PUBLIC",
]
