-- Migration 003: persist verified proof metadata and bundle
--
-- Aligns the proofs table with the production evidence model so persisted
-- evidence includes:
--   - fast-path integrity hash
--   - real ZK final proof hash
--   - proof system
--   - circuit binding
--   - verification key binding
--   - canonical proof bundle
--   - proof_verified flag

ALTER TABLE proofs
    ADD COLUMN IF NOT EXISTS integrity_hash TEXT;

ALTER TABLE proofs
    ADD COLUMN IF NOT EXISTS proof_system TEXT;

ALTER TABLE proofs
    ADD COLUMN IF NOT EXISTS circuit_hash TEXT;

ALTER TABLE proofs
    ADD COLUMN IF NOT EXISTS verification_key_hash TEXT;

ALTER TABLE proofs
    ADD COLUMN IF NOT EXISTS proof_bundle JSONB;

ALTER TABLE proofs
    ADD COLUMN IF NOT EXISTS proof_verified BOOLEAN NOT NULL DEFAULT FALSE;

UPDATE proofs
SET
    integrity_hash = COALESCE(integrity_hash, final_proof),
    proof_system = COALESCE(proof_system, 'legacy'),
    circuit_hash = COALESCE(circuit_hash, ''),
    verification_key_hash = COALESCE(verification_key_hash, ''),
    proof_bundle = COALESCE(
        proof_bundle,
        jsonb_build_object(
            'legacy', true,
            'final_proof', final_proof,
            'integrity_hash', COALESCE(integrity_hash, final_proof)
        )
    )
WHERE
    integrity_hash IS NULL
    OR proof_system IS NULL
    OR circuit_hash IS NULL
    OR verification_key_hash IS NULL
    OR proof_bundle IS NULL;

ALTER TABLE proofs
    ALTER COLUMN integrity_hash SET NOT NULL;

ALTER TABLE proofs
    ALTER COLUMN proof_system SET NOT NULL;

ALTER TABLE proofs
    ALTER COLUMN circuit_hash SET NOT NULL;

ALTER TABLE proofs
    ALTER COLUMN verification_key_hash SET NOT NULL;

ALTER TABLE proofs
    ALTER COLUMN proof_bundle SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'proofs_bundle_object'
    ) THEN
        ALTER TABLE proofs
            ADD CONSTRAINT proofs_bundle_object CHECK (jsonb_typeof(proof_bundle) = 'object');
    END IF;
END
$$;
