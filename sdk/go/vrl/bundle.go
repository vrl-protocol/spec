package vrl

import (
	"encoding/json"
	"fmt"
)

// ParseBundle parses a JSON byte slice into a ProofBundle
func ParseBundle(data []byte) (*ProofBundle, error) {
	var bundle ProofBundle
	err := json.Unmarshal(data, &bundle)
	if err != nil {
		return nil, fmt.Errorf("failed to parse bundle: %w", err)
	}
	return &bundle, nil
}

// SerializeBundle serializes a ProofBundle into JSON bytes
func SerializeBundle(bundle *ProofBundle) ([]byte, error) {
	data, err := json.MarshalIndent(bundle, "", "  ")
	if err != nil {
		return nil, fmt.Errorf("failed to serialize bundle: %w", err)
	}
	return data, nil
}

// SerializeBundleCompact serializes a ProofBundle into compact JSON bytes (no formatting)
func SerializeBundleCompact(bundle *ProofBundle) ([]byte, error) {
	data, err := json.Marshal(bundle)
	if err != nil {
		return nil, fmt.Errorf("failed to serialize bundle: %w", err)
	}
	return data, nil
}
