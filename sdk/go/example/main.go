package main

import (
	"fmt"
	"io/ioutil"

	"github.com/vrl-protocol/spec/sdk/go/vrl"
)

func main() {
	fmt.Println("=== VRL Go SDK Examples ===\n")

	// Example 1: Building a proof bundle
	fmt.Println("Example 1: Building a Proof Bundle")
	fmt.Println("-----------------------------------")

	builder := vrl.NewBuilder()

	aiParams := vrl.AIIdentityParams{
		AIID:                 "a3f2c1d4e5b6a7f8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a",
		ModelName:            "my-model",
		ModelVersion:         "1.0.0",
		ProviderID:           "io.example",
		ExecutionEnvironment: "deterministic",
	}

	compParams := vrl.ComputationParams{
		CircuitID:      "trade/import-landed-cost@2.0.0",
		CircuitVersion: "2.0.0",
		CircuitHash:    "3fa24c7763608b01b4c7e411655ebc75ff7a906c38bd79a4cc3be0f4479cdf23",
		InputHash:      "ebf1f0aa67d10b8472fd7f1af22fc9370ecb813243f928b4f5528ab27457fea7",
		OutputHash:     "0c866369e1ab87b0d0b624c0fdeb490aa05fa2524e9368a023308a1437ec5b5b",
		TraceHash:      "e14d0cb8d4a11cf1db1def3942fa7246b72cb6989463e8d379ade6e90a0405e6",
	}

	proofParams := vrl.ProofParams{
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
		fmt.Printf("Error building bundle: %v\n", err)
		return
	}

	fmt.Printf("Created bundle: %s\n", bundle.BundleID)
	fmt.Printf("Integrity hash: %s\n", bundle.Computation.IntegrityHash)
	fmt.Printf("Proof hash: %s\n\n", bundle.Proof.ProofHash)

	// Example 2: Serializing and deserializing
	fmt.Println("Example 2: Serialize and Deserialize")
	fmt.Println("------------------------------------")

	data, err := vrl.SerializeBundle(bundle)
	if err != nil {
		fmt.Printf("Error serializing: %v\n", err)
		return
	}

	fmt.Printf("Serialized bundle size: %d bytes\n", len(data))

	recovered, err := vrl.ParseBundle(data)
	if err != nil {
		fmt.Printf("Error parsing: %v\n", err)
		return
	}

	fmt.Printf("Deserialized bundle ID: %s\n", recovered.BundleID)
	fmt.Printf("Match: %v\n\n", recovered.BundleID == bundle.BundleID)

	// Example 3: Verifying a bundle
	fmt.Println("Example 3: Verifying a Bundle")
	fmt.Println("-----------------------------")

	verifier := vrl.NewVerifier()
	result := verifier.Verify(bundle)

	fmt.Printf("Verification status: %s\n", result.Status)
	fmt.Printf("Valid: %v\n", result.Valid)
	fmt.Printf("Steps performed: %d\n\n", len(result.Steps))

	for i, step := range result.Steps {
		statusStr := step.Status
		if step.Error != "" {
			statusStr = fmt.Sprintf("%s (%s)", step.Status, step.Error)
		}
		fmt.Printf("  [%d] %s: %s\n", i+1, step.StepName, statusStr)
	}

	// Example 4: Hash functions
	fmt.Println("\nExample 4: Hash Functions")
	fmt.Println("------------------------")

	input := "hello world"
	hash := vrl.SHA256Hex(input)
	fmt.Printf("SHA256(\"%s\"): %s\n", input, hash)

	integrityHash := vrl.ComputeIntegrityHash(
		"ebf1f0aa67d10b8472fd7f1af22fc9370ecb813243f928b4f5528ab27457fea7",
		"0c866369e1ab87b0d0b624c0fdeb490aa05fa2524e9368a023308a1437ec5b5b",
		"e14d0cb8d4a11cf1db1def3942fa7246b72cb6989463e8d379ade6e90a0405e6",
	)
	fmt.Printf("Integrity hash: %s\n\n", integrityHash)

	// Example 5: Loading and verifying a bundle from JSON file
	fmt.Println("Example 5: Load and Verify from File")
	fmt.Println("------------------------------------")

	bundleData, err := ioutil.ReadFile("example/bundle.json")
	if err != nil {
		fmt.Printf("Error reading bundle file: %v\n", err)
		return
	}

	fileBundle, err := vrl.ParseBundle(bundleData)
	if err != nil {
		fmt.Printf("Error parsing bundle from file: %v\n", err)
		return
	}

	result = verifier.Verify(fileBundle)
	fmt.Printf("File bundle verification: %s\n", result.Status)
	fmt.Printf("Valid: %v\n\n", result.Valid)
}
