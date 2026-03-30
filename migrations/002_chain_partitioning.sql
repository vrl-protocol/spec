-- Migration 002: Partitioned audit chains
--
-- Adds chain_id to audit_log so the single global advisory lock can be
-- replaced with 64 per-chain locks.  Existing rows default to chain 0,
-- which is the correct genesis value (ZERO_HASH starts each chain).
--
-- Apply with:
--   psql "$VRL_DATABASE_URL" -f migrations/002_chain_partitioning.sql

ALTER TABLE audit_log
    ADD COLUMN IF NOT EXISTS chain_id SMALLINT NOT NULL DEFAULT 0;

-- Composite index used by two hot queries:
--   (1) FETCH_LATEST_AUDIT_HASH_FOR_CHAIN: chain_id = $1 ORDER BY id DESC LIMIT 1
--   (2) FETCH_AUDIT_CHAIN_SQL:             ORDER BY chain_id ASC, id ASC
CREATE INDEX IF NOT EXISTS idx_audit_log_chain_id_id
    ON audit_log (chain_id, id);

-- Let vrl_writer and vrl_reader see the new column (column-level grants
-- are not required when table-level GRANT SELECT already covers it, but
-- being explicit avoids surprises with future column security policies).
COMMENT ON COLUMN audit_log.chain_id IS
    'Partition key: int(input_hash[:16], 16) % AUDIT_CHAIN_PARTITIONS (64). '
    'Each chain is independently verifiable with its own ZERO_HASH genesis.';
