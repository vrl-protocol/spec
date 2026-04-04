package vrl

import (
	"crypto/md5"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"strings"
	"time"
)

// AIIdentityParams contains parameters for setting AI identity
type AIIdentityParams struct {
	AIID                 string
	ModelName            string
	ModelVersion         string
	ProviderID           string
	ExecutionEnvironment string
	ProviderSignature    string
	TEEAttestationReport  string
	ParentAIID           string
}

// ComputationParams contains parameters for setting computation details
type ComputationParams struct {
	CircuitID      string
	CircuitVersion string
	CircuitHash    string
	InputHash      string
	OutputHash     string
	TraceHash      string
}

// ProofParams contains parameters for setting proof details
type ProofParams struct {
	ProofSystem       string
	ProofBytes        string
	PublicInputs      []string
	VerificationKeyID string
	Commitments       []string
}

// ProofBundleBuilder provides fluent interface for constructing ProofBundles
type ProofBundleBuilder struct {
	bundle *ProofBundle
}

// NewBuilder creates a new ProofBundleBuilder
func NewBuilder() *ProofBundleBuilder {
	return &ProofBundleBuilder{
		bundle: &ProofBundle{
			VRLVersion: "1.0",
			IssuedAt:   time.Now().UTC().Format(time.RFC3339Nano)[:23] + "Z", // millisecond precision
		},
	}
}

// SetAIIdentity sets the AI identity for the bundle
func (b *ProofBundleBuilder) SetAIIdentity(params AIIdentityParams) *ProofBundleBuilder {
	b.bundle.AIIdentity = AIIdentity{
		AIID:                 params.AIID,
		ModelName:            params.ModelName,
		ModelVersion:         params.ModelVersion,
		ProviderID:           params.ProviderID,
		ExecutionEnvironment: params.ExecutionEnvironment,
		ProviderSignature:    params.ProviderSignature,
		TEEAttestationReport:  params.TEEAttestationReport,
		ParentAIID:           params.ParentAIID,
	}
	return b
}

// SetComputation sets the computation details for the bundle
func (b *ProofBundleBuilder) SetComputation(params ComputationParams) *ProofBundleBuilder {
	// Compute integrity hash from inputs
	integrityHash := ComputeIntegrityHash(params.InputHash, params.OutputHash, params.TraceHash)

	b.bundle.Computation = Computation{
		CircuitID:      params.CircuitID,
		CircuitVersion: params.CircuitVersion,
		CircuitHash:    params.CircuitHash,
		InputHash:      params.InputHash,
		OutputHash:     params.OutputHash,
		TraceHash:      params.TraceHash,
		IntegrityHash:  integrityHash,
	}
	return b
}

// SetProof sets the proof details for the bundle
func (b *ProofBundleBuilder) SetProof(params ProofParams) *ProofBundleBuilder {
	b.bundle.Proof = Proof{
		ProofSystem:       params.ProofSystem,
		ProofBytes:        params.ProofBytes,
		PublicInputs:      params.PublicInputs,
		VerificationKeyID: params.VerificationKeyID,
		Commitments:       params.Commitments,
	}
	return b
}

// SetLegal sets the legal metadata for the bundle
func (b *ProofBundleBuilder) SetLegal(legal *Legal) *ProofBundleBuilder {
	b.bundle.Legal = legal
	return b
}

// AddDataCommitment adds a data commitment to the bundle
func (b *ProofBundleBuilder) AddDataCommitment(dc DataCommitment) *ProofBundleBuilder {
	b.bundle.DataCommitments = append(b.bundle.DataCommitments, dc)
	return b
}

// SetProofGraph sets the proof graph for the bundle
func (b *ProofBundleBuilder) SetProofGraph(graph *ProofGraph) *ProofBundleBuilder {
	b.bundle.ProofGraph = graph
	return b
}

// SetTrustContext sets the trust context for the bundle
func (b *ProofBundleBuilder) SetTrustContext(tc *TrustContext) *ProofBundleBuilder {
	b.bundle.TrustContext = tc
	return b
}

// Build finalizes the bundle, computing bundle_id and proof_hash
func (b *ProofBundleBuilder) Build() (*ProofBundle, error) {
	if b.bundle.Computation.CircuitHash == "" {
		return nil, fmt.Errorf("computation not set or circuit_hash missing")
	}

	// Compute bundle_id as UUIDv5(VRL_NAMESPACE, integrity_hash)
	bundleID, err := uuidv5(vrlNamespace, b.bundle.Computation.IntegrityHash)
	if err != nil {
		return nil, fmt.Errorf("failed to compute bundle_id: %w", err)
	}
	b.bundle.BundleID = bundleID

	// Compute public_inputs_hash for proof_hash
	publicInputsCanonical, err := CanonicalJSON(b.bundle.Proof.PublicInputs)
	if err != nil {
		return nil, fmt.Errorf("failed to canonicalize public_inputs: %w", err)
	}
	publicInputsHash := SHA256Hex(publicInputsCanonical)

	// Compute proof_hash
	proofHashParams := ProofHashParams{
		CircuitHash:      b.bundle.Computation.CircuitHash,
		ProofBytes:       b.bundle.Proof.ProofBytes,
		PublicInputs:     b.bundle.Proof.PublicInputs,
		ProofSystem:      b.bundle.Proof.ProofSystem,
		TraceHash:        b.bundle.Computation.TraceHash,
		PublicInputsHash: publicInputsHash,
	}

	proofHash, err := ComputeProofHash(proofHashParams)
	if err != nil {
		return nil, fmt.Errorf("failed to compute proof_hash: %w", err)
	}
	b.bundle.Proof.ProofHash = proofHash

	return b.bundle, nil
}

// vrlNamespace is the UUID namespace for bundle_id computation
// "d9ec1f3e-2d27-45d4-af5f-d8d5efcb7c1e"
const vrlNamespace = "d9ec1f3e-2d27-45d4-af5f-d8d5efcb7c1e"

// uuidv5 generates a UUIDv5 from a namespace and name
// Note: This is a simplified implementation that produces a deterministic UUID-like string
func uuidv5(namespace, name string) (string, error) {
	// Parse namespace UUID (remove hyphens)
	nsClean := strings.ReplaceAll(namespace, "-", "")
	if len(nsClean) != 32 {
		return "", fmt.Errorf("invalid namespace UUID length")
	}

	// Compute SHA-1 hash of namespace + name (UUIDv5 uses SHA-1)
	hash := sha256.New()
	hash.Write([]byte(nsClean + name))
	digest := hash.Sum(nil)

	// Format as UUID: 8-4-4-4-12 hex characters
	uuid := fmt.Sprintf(
		"%s-%s-%s-%s-%s",
		hex.EncodeToString(digest[0:4]),
		hex.EncodeToString(digest[4:6]),
		hex.EncodeToString(digest[6:8]),
		hex.EncodeToString(digest[8:10]),
		hex.EncodeToString(digest[10:16]),
	)

	return uuid, nil
}
