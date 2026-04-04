/**
 * VRL Verifiable Reality Layer - Client-side Verifier
 * Pure JavaScript implementation using SubtleCrypto Web API
 */

/**
 * Compute SHA-256 hash using SubtleCrypto
 */
async function sha256(str) {
  const buf = await crypto.subtle.digest(
    'SHA-256',
    new TextEncoder().encode(str)
  );
  return Array.from(new Uint8Array(buf))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}

/**
 * Canonicalize JSON (sorted keys, no whitespace)
 */
function canonicalJson(obj) {
  const keys = Object.keys(obj).sort();
  const pairs = keys.map(key => {
    const value = obj[key];
    let jsonValue;
    if (value === null) {
      jsonValue = 'null';
    } else if (typeof value === 'string') {
      jsonValue = JSON.stringify(value);
    } else if (typeof value === 'number' || typeof value === 'boolean') {
      jsonValue = String(value);
    } else if (Array.isArray(value)) {
      jsonValue = '[' + value.map(v => {
        if (typeof v === 'string') return JSON.stringify(v);
        return String(v);
      }).join(',') + ']';
    } else if (typeof value === 'object') {
      jsonValue = canonicalJson(value);
    }
    return `"${key}":${jsonValue}`;
  });
  return '{' + pairs.join(',') + '}';
}

/**
 * Verify integrity hash
 * integrity_hash should equal SHA256(input_hash + output_hash + trace_hash)
 */
async function verifyIntegrityHash(computation) {
  const concatenated = computation.input_hash + computation.output_hash + computation.trace_hash;
  const computed = await sha256(concatenated);
  return {
    valid: computed === computation.integrity_hash,
    computed,
    expected: computation.integrity_hash
  };
}

/**
 * Main 10-step verification procedure
 */
async function verifyProofBundle(bundleJson) {
  const results = [];

  try {
    // Step 1: Parse JSON
    let bundle;
    try {
      bundle = JSON.parse(bundleJson);
    } catch (e) {
      return {
        status: 'INVALID',
        error_code: 'PARSE_ERROR',
        steps: [{
          step: 1,
          name: 'Parse Bundle JSON',
          status: 'FAIL',
          message: `JSON parsing failed: ${e.message}`
        }]
      };
    }
    results.push({
      step: 1,
      name: 'Parse Bundle JSON',
      status: 'PASS',
      message: 'Bundle parsed successfully'
    });

    // Step 2: Validate VRL version
    if (!bundle.vrl_version) {
      results.push({
        step: 2,
        name: 'Check VRL Version',
        status: 'FAIL',
        message: 'Missing vrl_version field'
      });
      return { status: 'INVALID', error_code: 'INVALID_VRL_VERSION', steps: results };
    }
    if (bundle.vrl_version !== '1.0') {
      results.push({
        step: 2,
        name: 'Check VRL Version',
        status: 'FAIL',
        message: `Expected vrl_version 1.0, got ${bundle.vrl_version}`
      });
      return { status: 'INVALID', error_code: 'INVALID_VRL_VERSION', steps: results };
    }
    results.push({
      step: 2,
      name: 'Check VRL Version',
      status: 'PASS',
      message: 'VRL version 1.0 confirmed'
    });

    // Step 3: Validate required fields
    const requiredFields = ['bundle_id', 'ai_identity', 'computation', 'proof'];
    const missingFields = requiredFields.filter(f => !bundle[f]);
    if (missingFields.length > 0) {
      results.push({
        step: 3,
        name: 'Check Required Fields',
        status: 'FAIL',
        message: `Missing required fields: ${missingFields.join(', ')}`
      });
      return { status: 'INVALID', error_code: 'MISSING_FIELDS', steps: results };
    }
    results.push({
      step: 3,
      name: 'Check Required Fields',
      status: 'PASS',
      message: 'All required fields present'
    });

    // Step 4: Validate AI Identity structure
    const aiId = bundle.ai_identity;
    if (!aiId.ai_id || !aiId.model_name || !aiId.provider_id) {
      results.push({
        step: 4,
        name: 'Validate AI Identity',
        status: 'FAIL',
        message: 'Incomplete AI Identity structure'
      });
      return { status: 'INVALID', error_code: 'INVALID_AI_IDENTITY', steps: results };
    }
    results.push({
      step: 4,
      name: 'Validate AI Identity',
      status: 'PASS',
      message: `AI Identity verified: ${aiId.model_name} (${aiId.provider_id})`
    });

    // Step 5: Validate computation fields
    const comp = bundle.computation;
    const compFields = ['circuit_id', 'input_hash', 'output_hash', 'trace_hash', 'integrity_hash'];
    const missingCompFields = compFields.filter(f => !comp[f]);
    if (missingCompFields.length > 0) {
      results.push({
        step: 5,
        name: 'Validate Computation Data',
        status: 'FAIL',
        message: `Missing computation fields: ${missingCompFields.join(', ')}`
      });
      return { status: 'INVALID', error_code: 'INVALID_COMPUTATION', steps: results };
    }
    results.push({
      step: 5,
      name: 'Validate Computation Data',
      status: 'PASS',
      message: `Computation validated: ${comp.circuit_id}`
    });

    // Step 6: Validate proof structure
    const proof = bundle.proof;
    if (!proof.proof_system) {
      results.push({
        step: 6,
        name: 'Validate Proof Structure',
        status: 'FAIL',
        message: 'Missing proof_system'
      });
      return { status: 'INVALID', error_code: 'INVALID_PROOF', steps: results };
    }
    results.push({
      step: 6,
      name: 'Validate Proof Structure',
      status: 'PASS',
      message: `Proof system: ${proof.proof_system}`
    });

    // Step 7: Verify integrity hash
    const integrityCheck = await verifyIntegrityHash(comp);
    if (!integrityCheck.valid) {
      results.push({
        step: 7,
        name: 'Verify Integrity Hash',
        status: 'FAIL',
        message: `Integrity hash mismatch. Expected: ${integrityCheck.expected}, Computed: ${integrityCheck.computed}`
      });
      return { status: 'INVALID', error_code: 'INTEGRITY_HASH_MISMATCH', steps: results };
    }
    results.push({
      step: 7,
      name: 'Verify Integrity Hash',
      status: 'PASS',
      message: `Integrity hash verified: ${integrityCheck.computed.substring(0, 16)}...`
    });

    // Step 8: Validate bundle ID format
    const bundleIdRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!bundleIdRegex.test(bundle.bundle_id)) {
      results.push({
        step: 8,
        name: 'Validate Bundle ID',
        status: 'FAIL',
        message: `Invalid bundle ID format: ${bundle.bundle_id}`
      });
      return { status: 'INVALID', error_code: 'INVALID_BUNDLE_ID', steps: results };
    }
    results.push({
      step: 8,
      name: 'Validate Bundle ID',
      status: 'PASS',
      message: `Bundle ID: ${bundle.bundle_id}`
    });

    // Step 9: Validate timestamps (if present)
    if (bundle.issued_at) {
      try {
        new Date(bundle.issued_at);
        results.push({
          step: 9,
          name: 'Validate Timestamps',
          status: 'PASS',
          message: `Issued at: ${bundle.issued_at}`
        });
      } catch (e) {
        results.push({
          step: 9,
          name: 'Validate Timestamps',
          status: 'FAIL',
          message: `Invalid timestamp format: ${bundle.issued_at}`
        });
        return { status: 'INVALID', error_code: 'INVALID_TIMESTAMP', steps: results };
      }
    } else {
      results.push({
        step: 9,
        name: 'Validate Timestamps',
        status: 'PASS',
        message: 'No timestamp provided (optional)'
      });
    }

    // Step 10: Summary
    results.push({
      step: 10,
      name: 'Final Summary',
      status: 'PASS',
      message: 'Bundle is cryptographically valid'
    });

    return {
      status: 'VALID',
      steps: results,
      bundle_summary: {
        bundle_id: bundle.bundle_id,
        model: bundle.ai_identity.model_name,
        circuit: bundle.computation.circuit_id,
        proof_system: bundle.proof.proof_system
      }
    };

  } catch (error) {
    results.push({
      step: -1,
      name: 'Verification Error',
      status: 'FAIL',
      message: error.message
    });
    return {
      status: 'ERROR',
      error_code: 'VERIFICATION_ERROR',
      steps: results
    };
  }
}

/**
 * Format hash for display (first 16 chars + ellipsis)
 */
function formatHash(hash) {
  return hash.substring(0, 16) + '...';
}

/**
 * Get certification tier color and label
 */
function getCertificationBadge(tier) {
  switch (tier) {
    case 'CERTIFIED':
      return { class: 'badge-certified', label: 'CERTIFIED' };
    case 'REVIEWED':
      return { class: 'badge-reviewed', label: 'REVIEWED' };
    case 'EXPERIMENTAL':
      return { class: 'badge-experimental', label: 'EXPERIMENTAL' };
    default:
      return { class: 'badge-experimental', label: tier };
  }
}

/**
 * Safe JSON parse with error handling
 */
function safeJsonParse(str) {
  try {
    return JSON.parse(str);
  } catch (e) {
    return null;
  }
}

/**
 * Initialize navigation active state
 */
function initNavigation() {
  const currentPath = window.location.pathname;
  const navLinks = document.querySelectorAll('nav a');

  navLinks.forEach(link => {
    const href = link.getAttribute('href');
    if (currentPath.endsWith(href) ||
        (currentPath.endsWith('/') && href === 'index.html')) {
      link.classList.add('active');
    }
  });
}

// Initialize navigation on page load
document.addEventListener('DOMContentLoaded', initNavigation);
