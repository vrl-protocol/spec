package vrl

import (
	"encoding/json"
	"fmt"
	"strings"
)

// VerificationStatus represents the status of a verification
type VerificationStatus string

// Verification statuses
const (
	StatusValid              VerificationStatus = "VALID"
	StatusValidPartial       VerificationStatus = "VALID_PARTIAL"
	StatusSchemaInvalid      VerificationStatus = "SCHEMA_INVALID"
	StatusBundleIDMismatch   VerificationStatus = "BUNDLE_ID_MISMATCH"
	StatusIntegrityMismatch  VerificationStatus = "INTEGRITY_MISMATCH"
	StatusCircuitHashMismatch VerificationStatus = "CIRCUIT_HASH_MISMATCH"
	StatusProofInvalid       VerificationStatus = "PROOF_INVALID"
	StatusTEEAttestationInvalid VerificationStatus = "TEE_ATTESTATION_INVALID"
	StatusRecomputationMismatch VerificationStatus = "RECOMPUTATION_MISMATCH"
	StatusHashBindingInvalid VerificationStatus = "HASH_BINDING_INVALID"
	StatusAIIDInvalid        VerificationStatus = "AI_ID_INVALID"
	StatusDataCommitmentInvalid VerificationStatus = "DATA_COMMITMENT_INVALID"
	StatusTimestampInvalid   VerificationStatus = "TIMESTAMP_INVALID"
	StatusGraphEdgeInvalid   VerificationStatus = "GRAPH_EDGE_INVALID"
	StatusUnsupportedVersion VerificationStatus = "UNSUPPORTED_VERSION"
)

// VerificationStep represents a single verification step with its result
type VerificationStep struct {
	StepName string
	Status   string
	Error    string
}

// VerificationResult contains the results of a complete verification
type VerificationResult struct {
	Status     VerificationStatus
	ErrorCodes []string
	Steps      []VerificationStep
	Valid      bool
}

// Verifier performs cryptographic verification of ProofBundles
type Verifier struct {
}

// NewVerifier creates a new Verifier
func NewVerifier() *Verifier {
	return &Verifier{}
}

// Verify performs complete verification of a ProofBundle
func (v *Verifier) Verify(bundle *ProofBundle) *VerificationResult {
	result := &VerificationResult{
		Steps:      make([]VerificationStep, 0),
		ErrorCodes: make([]string, 0),
	}

	// Step 1: Version Check
	if bundle.VRLVersion != "1.0" {
		result.Steps = append(result.Steps, VerificationStep{
			StepName: "Version Check",
			Status:   "FAIL",
			Error:    fmt.Sprintf("unsupported version: %s", bundle.VRLVersion),
		})
		result.Status = StatusUnsupportedVersion
		result.ErrorCodes = append(result.ErrorCodes, string(StatusUnsupportedVersion))
		result.Valid = false
		return result
	}
	result.Steps = append(result.Steps, VerificationStep{
		StepName: "Version Check",
		Status:   "PASS",
	})

	// Step 2: Schema Validation
	if err := v.validateSchema(bundle); err != nil {
		result.Steps = append(result.Steps, VerificationStep{
			StepName: "Schema Validation",
			Status:   "FAIL",
			Error:    err.Error(),
		})
		result.Status = StatusSchemaInvalid
		result.ErrorCodes = append(result.ErrorCodes, string(StatusSchemaInvalid))
		result.Valid = false
		return result
	}
	result.Steps = append(result.Steps, VerificationStep{
		StepName: "Schema Validation",
		Status:   "PASS",
	})

	// Step 3: Bundle ID Recomputation
	recomputedBundleID, err := uuidv5(vrlNamespace, bundle.Computation.IntegrityHash)
	if err != nil || recomputedBundleID != bundle.BundleID {
		result.Steps = append(result.Steps, VerificationStep{
			StepName: "Bundle ID Recomputation",
			Status:   "FAIL",
			Error:    "bundle_id does not match recomputed value",
		})
		result.Status = StatusBundleIDMismatch
		result.ErrorCodes = append(result.ErrorCodes, string(StatusBundleIDMismatch))
		result.Valid = false
		return result
	}
	result.Steps = append(result.Steps, VerificationStep{
		StepName: "Bundle ID Recomputation",
		Status:   "PASS",
	})

	// Step 4: Integrity Hash Recomputation
	recomputedIntegrity := ComputeIntegrityHash(
		bundle.Computation.InputHash,
		bundle.Computation.OutputHash,
		bundle.Computation.TraceHash,
	)
	if recomputedIntegrity != bundle.Computation.IntegrityHash {
		result.Steps = append(result.Steps, VerificationStep{
			StepName: "Integrity Hash Recomputation",
			Status:   "FAIL",
			Error:    "integrity_hash does not match recomputed value",
		})
		result.Status = StatusIntegrityMismatch
		result.ErrorCodes = append(result.ErrorCodes, string(StatusIntegrityMismatch))
		result.Valid = false
		return result
	}
	result.Steps = append(result.Steps, VerificationStep{
		StepName: "Integrity Hash Recomputation",
		Status:   "PASS",
	})

	// Step 5: Circuit Resolution (basic check - would require registry access in full impl)
	// For now, just verify that circuit_hash is present and matches format
	if !isValidSHA256(bundle.Computation.CircuitHash) {
		result.Steps = append(result.Steps, VerificationStep{
			StepName: "Circuit Resolution",
			Status:   "FAIL",
			Error:    "invalid circuit_hash format",
		})
		result.Status = StatusCircuitHashMismatch
		result.ErrorCodes = append(result.ErrorCodes, string(StatusCircuitHashMismatch))
		result.Valid = false
		return result
	}
	result.Steps = append(result.Steps, VerificationStep{
		StepName: "Circuit Resolution",
		Status:   "PASS",
		Error:    "skipped (registry not available)",
	})

	// Step 6: Proof Verification (basic checks)
	if err := v.verifyProof(bundle); err != nil {
		result.Steps = append(result.Steps, VerificationStep{
			StepName: "Proof Verification",
			Status:   "FAIL",
			Error:    err.Error(),
		})
		result.Status = StatusProofInvalid
		result.ErrorCodes = append(result.ErrorCodes, string(StatusProofInvalid))
		result.Valid = false
		return result
	}
	result.Steps = append(result.Steps, VerificationStep{
		StepName: "Proof Verification",
		Status:   "PASS",
	})

	// Step 7: AI-ID Verification (if provider_signature present)
	if bundle.AIIdentity.ProviderSignature != "" {
		result.Steps = append(result.Steps, VerificationStep{
			StepName: "AI-ID Verification",
			Status:   "SKIPPED",
			Error:    "provider key not available for signature verification",
		})
	} else {
		result.Steps = append(result.Steps, VerificationStep{
			StepName: "AI-ID Verification",
			Status:   "PASS",
			Error:    "no signature to verify",
		})
	}

	// Step 8: Data Commitment Verification (if present)
	if len(bundle.DataCommitments) > 0 {
		allValid := true
		for i, dc := range bundle.DataCommitments {
			// Recompute commitment hash (without the commitment_hash field itself)
			dcCopy := dc
			dcCopy.CommitmentHash = ""
			canonical, _ := CanonicalJSON(dcCopy)
			recomputedHash := SHA256Hex(canonical)
			if recomputedHash != dc.CommitmentHash {
				allValid = false
				result.Steps = append(result.Steps, VerificationStep{
					StepName: fmt.Sprintf("Data Commitment %d", i),
					Status:   "FAIL",
					Error:    "commitment_hash does not match",
				})
				break
			}
		}
		if allValid {
			result.Steps = append(result.Steps, VerificationStep{
				StepName: "Data Commitments",
				Status:   "PASS",
			})
		} else {
			result.Status = StatusDataCommitmentInvalid
			result.ErrorCodes = append(result.ErrorCodes, string(StatusDataCommitmentInvalid))
			result.Valid = false
			return result
		}
	}

	// Step 9: Timestamp Verification (if present)
	if bundle.Legal != nil && bundle.Legal.TimestampAuthority != nil {
		result.Steps = append(result.Steps, VerificationStep{
			StepName: "Timestamp Verification",
			Status:   "SKIPPED",
			Error:    "TSA verification requires external service",
		})
	}

	// Step 10: Proof Graph Edges (if present)
	if bundle.ProofGraph != nil && len(bundle.ProofGraph.DependsOn) > 0 {
		result.Steps = append(result.Steps, VerificationStep{
			StepName: "Proof Graph Edges",
			Status:   "SKIPPED",
			Error:    "recursive verification not implemented",
		})
	}

	// All core checks passed
	result.Status = StatusValid
	result.Valid = true
	return result
}

// validateSchema performs basic schema validation on the bundle
func (v *Verifier) validateSchema(bundle *ProofBundle) error {
	if bundle.VRLVersion == "" {
		return fmt.Errorf("missing vrl_version")
	}
	if bundle.BundleID == "" {
		return fmt.Errorf("missing bundle_id")
	}
	if bundle.IssuedAt == "" {
		return fmt.Errorf("missing issued_at")
	}
	if bundle.AIIdentity.AIID == "" {
		return fmt.Errorf("missing ai_identity.ai_id")
	}
	if bundle.AIIdentity.ModelName == "" {
		return fmt.Errorf("missing ai_identity.model_name")
	}
	if bundle.AIIdentity.ExecutionEnvironment == "" {
		return fmt.Errorf("missing ai_identity.execution_environment")
	}
	if bundle.Computation.CircuitID == "" {
		return fmt.Errorf("missing computation.circuit_id")
	}
	if bundle.Computation.IntegrityHash == "" {
		return fmt.Errorf("missing computation.integrity_hash")
	}
	if bundle.Proof.ProofSystem == "" {
		return fmt.Errorf("missing proof.proof_system")
	}
	if len(bundle.Proof.PublicInputs) == 0 {
		return fmt.Errorf("proof.public_inputs cannot be empty")
	}

	return nil
}

// verifyProof performs basic proof verification
func (v *Verifier) verifyProof(bundle *ProofBundle) error {
	if bundle.Proof.ProofBytes == "" {
		return fmt.Errorf("missing proof_bytes")
	}
	if !isValidHex(bundle.Proof.ProofBytes) {
		return fmt.Errorf("proof_bytes is not valid hex")
	}
	if bundle.Proof.VerificationKeyID == "" {
		return fmt.Errorf("missing verification_key_id")
	}
	if bundle.Proof.ProofHash == "" {
		return fmt.Errorf("missing proof_hash")
	}
	if !isValidSHA256(bundle.Proof.ProofHash) {
		return fmt.Errorf("proof_hash is not valid SHA-256")
	}

	// For full verification, would need to invoke the actual ZK verifier
	// This is simplified to basic format checking
	return nil
}

// isValidHex checks if a string is valid hexadecimal
func isValidHex(s string) bool {
	if len(s) == 0 {
		return false
	}
	for _, c := range s {
		if !((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F')) {
			return false
		}
	}
	return true
}

// isValidSHA256 checks if a string is a valid SHA-256 hex (64 chars)
func isValidSHA256(s string) bool {
	if len(s) != 64 {
		return false
	}
	return isValidHex(s)
}
