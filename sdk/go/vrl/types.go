package vrl

// ProofSystem represents the cryptographic mechanism used for proof generation.
type ProofSystem string

// Registered proof systems
const (
	PlonkHalo2Pasta    ProofSystem = "plonk-halo2-pasta"
	PlonkHalo2BN254    ProofSystem = "plonk-halo2-bn254"
	Groth16BN254       ProofSystem = "groth16-bn254"
	Stark              ProofSystem = "stark"
	ZkML               ProofSystem = "zk-ml"
	TeeIntelTDX        ProofSystem = "tee-intel-tdx"
	TeeAmdSevSnp       ProofSystem = "tee-amd-sev-snp"
	TeeAWSNitro        ProofSystem = "tee-aws-nitro"
	SHA256Deterministic ProofSystem = "sha256-deterministic"
	APIHashBinding     ProofSystem = "api-hash-binding"
)

// ExecutionEnvironment represents the execution context for AI/computation
type ExecutionEnvironment string

// Execution environments
const (
	ExecutionDeterministic ExecutionEnvironment = "deterministic"
	ExecutionTEE           ExecutionEnvironment = "tee"
	ExecutionZkML          ExecutionEnvironment = "zk-ml"
	ExecutionAPIAttested   ExecutionEnvironment = "api-attested"
	ExecutionUnattested    ExecutionEnvironment = "unattested"
)

// PrivacyTier controls graph edge visibility
type PrivacyTier string

// Privacy tiers
const (
	PrivacyPublic      PrivacyTier = "public"
	PrivacyPermissioned PrivacyTier = "permissioned"
	PrivacyPrivate     PrivacyTier = "private"
)

// ProofBundle is the complete, portable artifact containing all VRL proof data
type ProofBundle struct {
	VRLVersion      string              `json:"vrl_version"`
	BundleID        string              `json:"bundle_id"`
	IssuedAt        string              `json:"issued_at"`
	AIIdentity      AIIdentity          `json:"ai_identity"`
	Computation     Computation         `json:"computation"`
	Proof           Proof               `json:"proof"`
	DataCommitments []DataCommitment    `json:"data_commitments,omitempty"`
	Legal           *Legal              `json:"legal,omitempty"`
	ProofGraph      *ProofGraph         `json:"proof_graph,omitempty"`
	TrustContext    *TrustContext       `json:"trust_context,omitempty"`
}

// AIIdentity claims the identity, version, and attestation of the AI model
type AIIdentity struct {
	AIID                 string `json:"ai_id"`
	ModelName            string `json:"model_name"`
	ModelVersion         string `json:"model_version"`
	ProviderID           string `json:"provider_id"`
	ExecutionEnvironment string `json:"execution_environment"`
	ProviderSignature    string `json:"provider_signature,omitempty"`
	TEEAttestationReport  string `json:"tee_attestation_report,omitempty"`
	ParentAIID           string `json:"parent_ai_id,omitempty"`
}

// Computation records the hashed artefacts of the computation
type Computation struct {
	CircuitID      string `json:"circuit_id"`
	CircuitVersion string `json:"circuit_version"`
	CircuitHash    string `json:"circuit_hash"`
	InputHash      string `json:"input_hash"`
	OutputHash     string `json:"output_hash"`
	TraceHash      string `json:"trace_hash"`
	IntegrityHash  string `json:"integrity_hash"`
}

// Proof contains the cryptographic proof and its metadata
type Proof struct {
	ProofSystem       string   `json:"proof_system"`
	ProofBytes        string   `json:"proof_bytes"`
	PublicInputs      []string `json:"public_inputs"`
	VerificationKeyID string   `json:"verification_key_id"`
	Commitments       []string `json:"commitments,omitempty"`
	ProofHash         string   `json:"proof_hash"`
}

// DataCommitment binds the bundle to a specific version of an external dataset
type DataCommitment struct {
	DatasetID         string `json:"dataset_id"`
	DatasetVersion    string `json:"dataset_version"`
	DatasetHash       string `json:"dataset_hash"`
	ProviderID        string `json:"provider_id"`
	ProviderSignature string `json:"provider_signature,omitempty"`
	CommittedAt       string `json:"committed_at"`
	CommitmentHash    string `json:"commitment_hash"`
}

// Legal contains legal and compliance metadata
type Legal struct {
	Jurisdictions         []string           `json:"jurisdictions,omitempty"`
	AdmissibilityStandard string             `json:"admissibility_standard,omitempty"`
	ComplianceFlags       []string           `json:"compliance_flags,omitempty"`
	TimestampAuthority    *TimestampAuthority `json:"timestamp_authority,omitempty"`
	ImmutableAnchor       *ImmutableAnchor   `json:"immutable_anchor,omitempty"`
}

// TimestampAuthority provides RFC 3161-compliant timestamp proof
type TimestampAuthority struct {
	TSAToken         string `json:"tsa_token"`
	TSAProvider      string `json:"tsa_provider"`
	TSAHashAlgorithm string `json:"tsa_hash_algorithm"`
}

// ImmutableAnchor records a blockchain commitment to the bundle
type ImmutableAnchor struct {
	Chain       string `json:"chain"`
	TxHash      string `json:"tx_hash"`
	BlockNumber int64  `json:"block_number"`
	AnchoredAt  string `json:"anchored_at"`
}

// ProofGraph is the DAG formed by bundles referencing each other
type ProofGraph struct {
	DependsOn            []string   `json:"depends_on,omitempty"`
	ProducedBy           string     `json:"produced_by,omitempty"`
	CausalDepth          int        `json:"causal_depth,omitempty"`
	GraphRootHash        string     `json:"graph_root_hash,omitempty"`
	PrivacyTier          string     `json:"privacy_tier,omitempty"`
}

// TrustContext provides metadata about the prover and trust scoring
type TrustContext struct {
	ProverID                string   `json:"prover_id,omitempty"`
	ProverVersion           string   `json:"prover_version,omitempty"`
	TrustScoreAtIssuance    float64  `json:"trust_score_at_issuance,omitempty"`
	CircuitCertificationTier string  `json:"circuit_certification_tier,omitempty"`
	AnomalyFlags            []string `json:"anomaly_flags,omitempty"`
}
