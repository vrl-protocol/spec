package vrl

import (
	"strings"
	"testing"
)

// TestBuildBundle tests bundle creation with the builder
func TestBuildBundle(t *testing.T) {
	builder := NewBuilder()

	aiParams := AIIdentityParams{
		AIID:                 "a3f2c1d4e5b6a7f8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a",
		ModelName:            "test-model",
		ModelVersion:         "1.0.0",
		ProviderID:           "io.test",
		ExecutionEnvironment: "deterministic",
	}

	compParams := ComputationParams{
		CircuitID:      "test/circuit@1.0.0",
		CircuitVersion: "1.0.0",
		CircuitHash:    "3fa24c7763608b01b4c7e411655ebc75ff7a906c38bd79a4cc3be0f4479cdf23",
		InputHash:      "ebf1f0aa67d10b8472fd7f1af22fc9370ecb813243f928b4f5528ab27457fea7",
		OutputHash:     "0c866369e1ab87b0d0b624c0fdeb490aa05fa2524e9368a023308a1437ec5b5b",
		TraceHash:      "e14d0cb8d4a11cf1db1def3942fa7246b72cb6989463e8d379ade6e90a0405e6",
	}

	proofParams := ProofParams{
		ProofSystem:       "sha256-deterministic",
		ProofBytes:        "0a1b2c3d",
		PublicInputs:      []string{"1a2b3c4d", "2b3c4d5e"},
		VerificationKeyID: "aadfa62983a64cb674b1b9b1c4379d8a01e02948fed731506de4bcf2950012a0",
	}

	bundle, err := builder.
		SetAIIdentity(aiParams).
		SetComputation(compParams).
		SetProof(proofParams).
		Build()

	if err != nil {
		t.Fatalf("Build failed: %v", err)
	}

	if bundle.BundleID == "" {
		t.Error("bundle_id should be set")
	}

	if bundle.VRLVersion != "1.0" {
		t.Errorf("vrl_version should be '1.0', got %s", bundle.VRLVersion)
	}

	if bundle.AIIdentity.AIID != aiParams.AIID {
		t.Errorf("AIID mismatch")
	}

	if bundle.Computation.IntegrityHash == "" {
		t.Error("integrity_hash should be computed")
	}

	if bundle.Proof.ProofHash == "" {
		t.Error("proof_hash should be computed")
	}

	t.Logf("Created bundle with ID: %s", bundle.BundleID)
}

// TestRoundTrip tests serialize -> deserialize -> compare
func TestRoundTrip(t *testing.T) {
	builder := NewBuilder()

	aiParams := AIIdentityParams{
		AIID:                 "f1e2d3c4b5a69788695041322314affa16718192021222324252627282930",
		ModelName:            "llama-3",
		ModelVersion:         "3.0.0",
		ProviderID:           "self",
		ExecutionEnvironment: "tee",
	}

	compParams := ComputationParams{
		CircuitID:      "general/tee-attestation@1.0.0",
		CircuitVersion: "1.0.0",
		CircuitHash:    "b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3",
		InputHash:      "c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4",
		OutputHash:     "d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5",
		TraceHash:      "e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6",
	}

	proofParams := ProofParams{
		ProofSystem:       "tee-intel-tdx",
		ProofBytes:        "deadbeef",
		PublicInputs:      []string{""},
		VerificationKeyID: "intel-tdx-root-ca-2024",
	}

	original, err := builder.
		SetAIIdentity(aiParams).
		SetComputation(compParams).
		SetProof(proofParams).
		Build()

	if err != nil {
		t.Fatalf("Build failed: %v", err)
	}

	// Serialize
	data, err := SerializeBundle(original)
	if err != nil {
		t.Fatalf("Serialize failed: %v", err)
	}

	// Deserialize
	recovered, err := ParseBundle(data)
	if err != nil {
		t.Fatalf("Parse failed: %v", err)
	}

	// Compare key fields
	if recovered.BundleID != original.BundleID {
		t.Errorf("bundle_id mismatch: %s != %s", recovered.BundleID, original.BundleID)
	}

	if recovered.Computation.IntegrityHash != original.Computation.IntegrityHash {
		t.Errorf("integrity_hash mismatch")
	}

	if recovered.Proof.ProofHash != original.Proof.ProofHash {
		t.Errorf("proof_hash mismatch")
	}

	t.Log("Round-trip test passed")
}

// TestVerifyValid tests verification of a valid bundle
func TestVerifyValid(t *testing.T) {
	builder := NewBuilder()

	aiParams := AIIdentityParams{
		AIID:                 "a3f2c1d4e5b6a7f8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a",
		ModelName:            "valid-model",
		ModelVersion:         "1.0.0",
		ProviderID:           "io.test",
		ExecutionEnvironment: "deterministic",
	}

	compParams := ComputationParams{
		CircuitID:      "test/circuit@1.0.0",
		CircuitVersion: "1.0.0",
		CircuitHash:    "3fa24c7763608b01b4c7e411655ebc75ff7a906c38bd79a4cc3be0f4479cdf23",
		InputHash:      "ebf1f0aa67d10b8472fd7f1af22fc9370ecb813243f928b4f5528ab27457fea7",
		OutputHash:     "0c866369e1ab87b0d0b624c0fdeb490aa05fa2524e9368a023308a1437ec5b5b",
		TraceHash:      "e14d0cb8d4a11cf1db1def3942fa7246b72cb6989463e8d379ade6e90a0405e6",
	}

	proofParams := ProofParams{
		ProofSystem:       "sha256-deterministic",
		ProofBytes:        "0a1b2c3d",
		PublicInputs:      []string{"1a2b3c4d", "2b3c4d5e"},
		VerificationKeyID: "aadfa62983a64cb674b1b9b1c4379d8a01e02948fed731506de4bcf2950012a0",
	}

	bundle, err := builder.
		SetAIIdentity(aiParams).
		SetComputation(compParams).
		SetProof(proofParams).
		Build()

	if err != nil {
		t.Fatalf("Build failed: %v", err)
	}

	verifier := NewVerifier()
	result := verifier.Verify(bundle)

	if !result.Valid {
		t.Errorf("Expected valid bundle, got status: %s", result.Status)
		for _, ec := range result.ErrorCodes {
			t.Logf("  Error: %s", ec)
		}
	}

	if result.Status != StatusValid {
		t.Errorf("Expected status VALID, got %s", result.Status)
	}

	t.Logf("Verification passed with %d checks", len(result.Steps))
	for _, step := range result.Steps {
		t.Logf("  %s: %s", step.StepName, step.Status)
	}
}

// TestVerifyTampered tests verification of a tampered bundle
func TestVerifyTampered(t *testing.T) {
	builder := NewBuilder()

	aiParams := AIIdentityParams{
		AIID:                 "a3f2c1d4e5b6a7f8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a",
		ModelName:            "tampered-model",
		ModelVersion:         "1.0.0",
		ProviderID:           "io.test",
		ExecutionEnvironment: "deterministic",
	}

	compParams := ComputationParams{
		CircuitID:      "test/circuit@1.0.0",
		CircuitVersion: "1.0.0",
		CircuitHash:    "3fa24c7763608b01b4c7e411655ebc75ff7a906c38bd79a4cc3be0f4479cdf23",
		InputHash:      "ebf1f0aa67d10b8472fd7f1af22fc9370ecb813243f928b4f5528ab27457fea7",
		OutputHash:     "0c866369e1ab87b0d0b624c0fdeb490aa05fa2524e9368a023308a1437ec5b5b",
		TraceHash:      "e14d0cb8d4a11cf1db1def3942fa7246b72cb6989463e8d379ade6e90a0405e6",
	}

	proofParams := ProofParams{
		ProofSystem:       "sha256-deterministic",
		ProofBytes:        "0a1b2c3d",
		PublicInputs:      []string{"1a2b3c4d", "2b3c4d5e"},
		VerificationKeyID: "aadfa62983a64cb674b1b9b1c4379d8a01e02948fed731506de4bcf2950012a0",
	}

	bundle, err := builder.
		SetAIIdentity(aiParams).
		SetComputation(compParams).
		SetProof(proofParams).
		Build()

	if err != nil {
		t.Fatalf("Build failed: %v", err)
	}

	// Tamper with integrity_hash
	bundle.Computation.IntegrityHash = "0000000000000000000000000000000000000000000000000000000000000000"

	verifier := NewVerifier()
	result := verifier.Verify(bundle)

	if result.Valid {
		t.Error("Expected tampered bundle to be invalid")
	}

	if result.Status != StatusIntegrityMismatch {
		t.Errorf("Expected status INTEGRITY_MISMATCH, got %s", result.Status)
	}

	if len(result.ErrorCodes) == 0 {
		t.Error("Expected error codes")
	}

	t.Logf("Tamper detection passed: %s", result.Status)
}

// TestCanonicalJSON tests canonical JSON serialization
func TestCanonicalJSON(t *testing.T) {
	obj := map[string]interface{}{
		"z": 1,
		"a": "hello",
		"m": []interface{}{3, 1, 2},
	}

	canonical, err := CanonicalJSON(obj)
	if err != nil {
		t.Fatalf("CanonicalJSON failed: %v", err)
	}

	// Expected: {"a":"hello","m":[3,1,2],"z":1}
	expected := `{"a":"hello","m":[3,1,2],"z":1}`

	if canonical != expected {
		t.Errorf("Expected %s, got %s", expected, canonical)
	}

	t.Logf("Canonical JSON: %s", canonical)
}

// TestSHA256Hex tests SHA256 hex computation
func TestSHA256Hex(t *testing.T) {
	input := "hello world"
	result := SHA256Hex(input)

	// Verify format: 64 character lowercase hex
	if len(result) != 64 {
		t.Errorf("Expected 64 character hex, got %d", len(result))
	}

	if strings.ToLower(result) != result {
		t.Error("Expected lowercase hex")
	}

	// Verify it's valid hex
	for _, c := range result {
		if !((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f')) {
			t.Errorf("Invalid hex character: %c", c)
		}
	}

	// Known hash for "hello world"
	expectedHash := "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
	if result != expectedHash {
		t.Errorf("Expected %s, got %s", expectedHash, result)
	}

	t.Logf("SHA256 hash: %s", result)
}

// TestComputeIntegrityHash tests integrity hash computation
func TestComputeIntegrityHash(t *testing.T) {
	inputHash := "ebf1f0aa67d10b8472fd7f1af22fc9370ecb813243f928b4f5528ab27457fea7"
	outputHash := "0c866369e1ab87b0d0b624c0fdeb490aa05fa2524e9368a023308a1437ec5b5b"
	traceHash := "e14d0cb8d4a11cf1db1def3942fa7246b72cb6989463e8d379ade6e90a0405e6"

	result := ComputeIntegrityHash(inputHash, outputHash, traceHash)

	// Verify format
	if len(result) != 64 {
		t.Errorf("Expected 64 character hash, got %d", len(result))
	}

	// Should be deterministic
	result2 := ComputeIntegrityHash(inputHash, outputHash, traceHash)
	if result != result2 {
		t.Error("Expected deterministic hash computation")
	}

	t.Logf("Integrity hash: %s", result)
}

// TestComputeAIID tests AI-ID computation
func TestComputeAIID(t *testing.T) {
	params := AIIDParams{
		ModelWeightsHash: "abc123def456",
		RuntimeHash:      "xyz789uvw012",
		ConfigHash:       "config123hash456",
		ProviderID:       "io.test",
		ModelName:        "test-model",
		ModelVersion:     "1.0.0",
		SpecVersion:      "vrl/ai-id/1.0",
	}

	aiid, err := ComputeAIID(params)
	if err != nil {
		t.Fatalf("ComputeAIID failed: %v", err)
	}

	// Verify format
	if len(aiid) != 64 {
		t.Errorf("Expected 64 character AI-ID, got %d", len(aiid))
	}

	// Should be deterministic
	aiid2, _ := ComputeAIID(params)
	if aiid != aiid2 {
		t.Error("Expected deterministic AI-ID computation")
	}

	// Changing any param should change the AI-ID
	params2 := params
	params2.ModelVersion = "2.0.0"
	aiid3, _ := ComputeAIID(params2)
	if aiid == aiid3 {
		t.Error("Expected different AI-ID when parameters change")
	}

	t.Logf("AI-ID: %s", aiid)
}

// TestComputeProofHash tests proof hash computation
func TestComputeProofHash(t *testing.T) {
	params := ProofHashParams{
		CircuitHash:      "3fa24c7763608b01b4c7e411655ebc75ff7a906c38bd79a4cc3be0f4479cdf23",
		ProofBytes:       "0a1b2c3d",
		PublicInputs:     []string{"1a2b3c4d", "2b3c4d5e"},
		ProofSystem:      "sha256-deterministic",
		TraceHash:        "e14d0cb8d4a11cf1db1def3942fa7246b72cb6989463e8d379ade6e90a0405e6",
		PublicInputsHash: "hash123",
	}

	result, err := ComputeProofHash(params)
	if err != nil {
		t.Fatalf("ComputeProofHash failed: %v", err)
	}

	// Verify format
	if len(result) != 64 {
		t.Errorf("Expected 64 character hash, got %d", len(result))
	}

	// Should be deterministic
	result2, _ := ComputeProofHash(params)
	if result != result2 {
		t.Error("Expected deterministic proof hash computation")
	}

	t.Logf("Proof hash: %s", result)
}

// TestDataCommitment tests data commitment creation and verification
func TestDataCommitment(t *testing.T) {
	dc := DataCommitment{
		DatasetID:      "cbp/hts-tariff-rules",
		DatasetVersion: "2026.1.0",
		DatasetHash:    "d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5",
		ProviderID:     "gov.us.cbp",
		CommittedAt:    "2026-04-01T00:00:00.000Z",
	}

	// Compute commitment hash
	dcCopy := dc
	dcCopy.CommitmentHash = ""
	canonical, err := CanonicalJSON(dcCopy)
	if err != nil {
		t.Fatalf("CanonicalJSON failed: %v", err)
	}

	commitmentHash := SHA256Hex(canonical)
	dc.CommitmentHash = commitmentHash

	// Verify it can be reconstructed
	dcCopy2 := dc
	dcCopy2.CommitmentHash = ""
	canonical2, _ := CanonicalJSON(dcCopy2)
	commitmentHash2 := SHA256Hex(canonical2)

	if commitmentHash != commitmentHash2 {
		t.Error("Commitment hash verification failed")
	}

	t.Logf("Data commitment hash: %s", dc.CommitmentHash)
}
