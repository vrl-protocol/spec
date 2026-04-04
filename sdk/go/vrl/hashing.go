package vrl

import (
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"sort"
)

// CanonicalJSON marshals a value to canonical JSON with sorted keys and no whitespace
func CanonicalJSON(v interface{}) (string, error) {
	// Marshal to canonical form by unmarshaling then re-marshaling with sorted keys
	b, err := json.Marshal(v)
	if err != nil {
		return "", fmt.Errorf("marshal error: %w", err)
	}

	// Unmarshal into a generic structure to rebuild with sorted keys
	var obj interface{}
	err = json.Unmarshal(b, &obj)
	if err != nil {
		return "", fmt.Errorf("unmarshal error: %w", err)
	}

	// Re-marshal with sorted keys by using a custom approach
	canonical, err := marshalCanonical(obj)
	if err != nil {
		return "", err
	}

	return canonical, nil
}

// marshalCanonical recursively marshals a value with sorted keys
func marshalCanonical(v interface{}) (string, error) {
	switch val := v.(type) {
	case map[string]interface{}:
		// Sort keys and rebuild object
		keys := make([]string, 0, len(val))
		for k := range val {
			keys = append(keys, k)
		}
		sort.Strings(keys)

		result := "{"
		for i, k := range keys {
			if i > 0 {
				result += ","
			}
			// Marshal key
			kb, _ := json.Marshal(k)
			result += string(kb) + ":"

			// Marshal value canonically
			vStr, err := marshalCanonical(val[k])
			if err != nil {
				return "", err
			}
			result += vStr
		}
		result += "}"
		return result, nil

	case []interface{}:
		result := "["
		for i, item := range val {
			if i > 0 {
				result += ","
			}
			iStr, err := marshalCanonical(item)
			if err != nil {
				return "", err
			}
			result += iStr
		}
		result += "]"
		return result, nil

	case nil:
		return "null", nil

	case bool:
		if val {
			return "true", nil
		}
		return "false", nil

	case string:
		b, _ := json.Marshal(val)
		return string(b), nil

	case float64:
		b, _ := json.Marshal(val)
		return string(b), nil

	default:
		// Fallback for other types
		b, err := json.Marshal(val)
		if err != nil {
			return "", err
		}
		return string(b), nil
	}
}

// SHA256Hex computes the SHA-256 hash of a string and returns lowercase hex
func SHA256Hex(input string) string {
	hash := sha256.Sum256([]byte(input))
	return fmt.Sprintf("%x", hash[:])
}

// ComputeIntegrityHash computes the integrity hash from three component hashes
func ComputeIntegrityHash(inputHash, outputHash, traceHash string) string {
	concatenated := inputHash + outputHash + traceHash
	return SHA256Hex(concatenated)
}

// AIIDParams contains parameters for AI-ID computation
type AIIDParams struct {
	ModelWeightsHash string
	RuntimeHash      string
	ConfigHash       string
	ProviderID       string
	ModelName        string
	ModelVersion     string
	SpecVersion      string
}

// ComputeAIID computes the AI-ID per spec §2.2
func ComputeAIID(params AIIDParams) (string, error) {
	// Build the AI-ID input object with fields in the spec order
	obj := map[string]interface{}{
		"model_weights_hash": params.ModelWeightsHash,
		"runtime_hash":       params.RuntimeHash,
		"config_hash":        params.ConfigHash,
		"provider_id":        params.ProviderID,
		"model_name":         params.ModelName,
		"model_version":      params.ModelVersion,
		"spec_version":       params.SpecVersion,
	}

	canonical, err := CanonicalJSON(obj)
	if err != nil {
		return "", fmt.Errorf("canonical json error: %w", err)
	}

	return SHA256Hex(canonical), nil
}

// ProofHashParams contains parameters for proof hash computation
type ProofHashParams struct {
	CircuitHash      string
	ProofBytes       string
	PublicInputs     []string
	ProofSystem      string
	TraceHash        string
	PublicInputsHash string
}

// ComputeProofHash computes the proof hash per spec §11.5
func ComputeProofHash(params ProofHashParams) (string, error) {
	obj := map[string]interface{}{
		"circuit_hash":        params.CircuitHash,
		"proof_bytes":         params.ProofBytes,
		"public_inputs":       params.PublicInputs,
		"proof_system":        params.ProofSystem,
		"trace_hash":          params.TraceHash,
		"public_inputs_hash":  params.PublicInputsHash,
	}

	canonical, err := CanonicalJSON(obj)
	if err != nil {
		return "", fmt.Errorf("canonical json error: %w", err)
	}

	return SHA256Hex(canonical), nil
}
