DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vrl_writer') THEN
        CREATE ROLE vrl_writer NOINHERIT LOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vrl_reader') THEN
        CREATE ROLE vrl_reader NOINHERIT LOGIN;
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS requests (
    id UUID PRIMARY KEY,
    input_hash TEXT NOT NULL,
    raw_input JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT requests_input_hash_unique UNIQUE (input_hash),
    CONSTRAINT requests_raw_input_object CHECK (jsonb_typeof(raw_input) = 'object')
);

CREATE TABLE IF NOT EXISTS results (
    id UUID PRIMARY KEY,
    request_id UUID NOT NULL REFERENCES requests(id),
    output_hash TEXT NOT NULL,
    raw_output JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT results_request_unique UNIQUE (request_id),
    CONSTRAINT results_raw_output_object CHECK (jsonb_typeof(raw_output) = 'object')
);

CREATE TABLE IF NOT EXISTS proofs (
    id UUID PRIMARY KEY,
    request_id UUID NOT NULL REFERENCES requests(id),
    trace_hash TEXT NOT NULL,
    final_proof TEXT NOT NULL,
    integrity_hash TEXT NOT NULL,
    proof_system TEXT NOT NULL,
    circuit_hash TEXT NOT NULL,
    verification_key_hash TEXT NOT NULL,
    proof_bundle JSONB NOT NULL,
    proof_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT proofs_request_unique UNIQUE (request_id),
    CONSTRAINT proofs_bundle_object CHECK (jsonb_typeof(proof_bundle) = 'object')
);

CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,
    reference_id UUID,
    event_payload JSONB NOT NULL,
    prev_hash TEXT,
    current_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT audit_log_event_payload_object CHECK (jsonb_typeof(event_payload) = 'object')
);

CREATE INDEX IF NOT EXISTS idx_requests_created_at ON requests(created_at);
CREATE INDEX IF NOT EXISTS idx_results_request_id ON results(request_id);
CREATE INDEX IF NOT EXISTS idx_results_created_at ON results(created_at);
CREATE INDEX IF NOT EXISTS idx_proofs_request_id ON proofs(request_id);
CREATE INDEX IF NOT EXISTS idx_proofs_created_at ON proofs(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_log_reference_id ON audit_log(reference_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at);

CREATE OR REPLACE FUNCTION raise_append_only_violation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'Append-only table % does not allow % operations', TG_TABLE_NAME, TG_OP;
END;
$$;

DROP TRIGGER IF EXISTS requests_append_only_guard ON requests;
CREATE TRIGGER requests_append_only_guard
BEFORE UPDATE OR DELETE ON requests
FOR EACH ROW EXECUTE FUNCTION raise_append_only_violation();

DROP TRIGGER IF EXISTS results_append_only_guard ON results;
CREATE TRIGGER results_append_only_guard
BEFORE UPDATE OR DELETE ON results
FOR EACH ROW EXECUTE FUNCTION raise_append_only_violation();

DROP TRIGGER IF EXISTS proofs_append_only_guard ON proofs;
CREATE TRIGGER proofs_append_only_guard
BEFORE UPDATE OR DELETE ON proofs
FOR EACH ROW EXECUTE FUNCTION raise_append_only_violation();

DROP TRIGGER IF EXISTS audit_log_append_only_guard ON audit_log;
CREATE TRIGGER audit_log_append_only_guard
BEFORE UPDATE OR DELETE ON audit_log
FOR EACH ROW EXECUTE FUNCTION raise_append_only_violation();

ALTER TABLE requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE results ENABLE ROW LEVEL SECURITY;
ALTER TABLE proofs ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

ALTER TABLE requests FORCE ROW LEVEL SECURITY;
ALTER TABLE results FORCE ROW LEVEL SECURITY;
ALTER TABLE proofs FORCE ROW LEVEL SECURITY;
ALTER TABLE audit_log FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS requests_writer_insert_policy ON requests;
CREATE POLICY requests_writer_insert_policy ON requests
    FOR INSERT TO vrl_writer
    WITH CHECK (true);

DROP POLICY IF EXISTS requests_reader_select_policy ON requests;
CREATE POLICY requests_reader_select_policy ON requests
    FOR SELECT TO vrl_reader, vrl_writer
    USING (true);

DROP POLICY IF EXISTS results_writer_insert_policy ON results;
CREATE POLICY results_writer_insert_policy ON results
    FOR INSERT TO vrl_writer
    WITH CHECK (true);

DROP POLICY IF EXISTS results_reader_select_policy ON results;
CREATE POLICY results_reader_select_policy ON results
    FOR SELECT TO vrl_reader, vrl_writer
    USING (true);

DROP POLICY IF EXISTS proofs_writer_insert_policy ON proofs;
CREATE POLICY proofs_writer_insert_policy ON proofs
    FOR INSERT TO vrl_writer
    WITH CHECK (true);

DROP POLICY IF EXISTS proofs_reader_select_policy ON proofs;
CREATE POLICY proofs_reader_select_policy ON proofs
    FOR SELECT TO vrl_reader, vrl_writer
    USING (true);

DROP POLICY IF EXISTS audit_log_writer_insert_policy ON audit_log;
CREATE POLICY audit_log_writer_insert_policy ON audit_log
    FOR INSERT TO vrl_writer
    WITH CHECK (true);

DROP POLICY IF EXISTS audit_log_reader_select_policy ON audit_log;
CREATE POLICY audit_log_reader_select_policy ON audit_log
    FOR SELECT TO vrl_reader, vrl_writer
    USING (true);

REVOKE UPDATE, DELETE ON requests, results, proofs, audit_log FROM PUBLIC, vrl_writer, vrl_reader;
REVOKE TRUNCATE ON requests, results, proofs, audit_log FROM PUBLIC, vrl_writer, vrl_reader;
REVOKE ALL ON requests, results, proofs, audit_log FROM PUBLIC;

GRANT INSERT ON requests, results, proofs, audit_log TO vrl_writer;
GRANT SELECT ON requests, results, proofs, audit_log TO vrl_reader, vrl_writer;
GRANT USAGE, SELECT ON SEQUENCE audit_log_id_seq TO vrl_writer, vrl_reader;
