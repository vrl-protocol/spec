package main

import (
	"flag"
	"fmt"
	"io/ioutil"
	"os"

	"github.com/vrl-protocol/spec/sdk/go/vrl"
)

func main() {
	flag.Parse()
	args := flag.Args()

	if len(args) == 0 {
		fmt.Fprintf(os.Stderr, "Usage: vrl-verify <bundle.json>\n")
		os.Exit(2)
	}

	bundlePath := args[0]

	// Read bundle file
	data, err := ioutil.ReadFile(bundlePath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error reading file %s: %v\n", bundlePath, err)
		os.Exit(1)
	}

	// Parse bundle
	bundle, err := vrl.ParseBundle(data)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error parsing bundle: %v\n", err)
		os.Exit(1)
	}

	// Verify bundle
	verifier := vrl.NewVerifier()
	result := verifier.Verify(bundle)

	// Print results
	fmt.Printf("VRL Bundle Verification Report\n")
	fmt.Printf("==============================\n")
	fmt.Printf("Bundle ID:     %s\n", bundle.BundleID)
	fmt.Printf("Status:        %s\n", result.Status)
	fmt.Printf("Valid:         %v\n", result.Valid)
	fmt.Printf("\n")

	fmt.Printf("Verification Steps:\n")
	for i, step := range result.Steps {
		status := step.Status
		if step.Error != "" {
			status = fmt.Sprintf("%s (%s)", step.Status, step.Error)
		}
		fmt.Printf("  [%d] %-35s %s\n", i+1, step.StepName, status)
	}
	fmt.Printf("\n")

	if len(result.ErrorCodes) > 0 {
		fmt.Printf("Error Codes:\n")
		for _, ec := range result.ErrorCodes {
			fmt.Printf("  - %s\n", ec)
		}
		fmt.Printf("\n")
	}

	// Additional bundle information
	fmt.Printf("Bundle Information:\n")
	fmt.Printf("  VRL Version:              %s\n", bundle.VRLVersion)
	fmt.Printf("  Issued At:                %s\n", bundle.IssuedAt)
	fmt.Printf("  AI-ID:                    %s\n", bundle.AIIdentity.AIID)
	fmt.Printf("  Model:                    %s %s\n", bundle.AIIdentity.ModelName, bundle.AIIdentity.ModelVersion)
	fmt.Printf("  Circuit:                  %s\n", bundle.Computation.CircuitID)
	fmt.Printf("  Proof System:             %s\n", bundle.Proof.ProofSystem)
	fmt.Printf("  Integrity Hash:           %s\n", bundle.Computation.IntegrityHash)
	fmt.Printf("  Proof Hash:               %s\n", bundle.Proof.ProofHash)

	if bundle.Legal != nil {
		fmt.Printf("  Jurisdictions:            %v\n", bundle.Legal.Jurisdictions)
		fmt.Printf("  Compliance Flags:         %v\n", bundle.Legal.ComplianceFlags)
	}

	if bundle.ProofGraph != nil {
		fmt.Printf("  Causal Depth:             %d\n", bundle.ProofGraph.CausalDepth)
		fmt.Printf("  Privacy Tier:             %s\n", bundle.ProofGraph.PrivacyTier)
	}

	if bundle.TrustContext != nil {
		fmt.Printf("  Trust Score:              %.2f\n", bundle.TrustContext.TrustScoreAtIssuance)
		fmt.Printf("  Circuit Tier:             %s\n", bundle.TrustContext.CircuitCertificationTier)
	}

	fmt.Printf("\n")

	// Exit code
	if result.Valid {
		fmt.Printf("Result: PASS\n")
		os.Exit(0)
	} else {
		fmt.Printf("Result: FAIL\n")
		os.Exit(1)
	}
}
