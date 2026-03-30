use ff::{Field, PrimeField};
use halo2_proofs::{
    circuit::{AssignedCell, Layouter, SimpleFloorPlanner, Value},
    dev::MockProver,
    pasta::{EqAffine, Fp},
    plonk::{
        create_proof, keygen_pk, keygen_vk, verify_proof, Advice, Circuit, Column,
        ConstraintSystem, Error, Instance, Selector, SingleVerifier,
    },
    poly::commitment::Params,
    poly::Rotation,
    transcript::{Blake2bRead, Blake2bWrite, Challenge255},
};
use rand_chacha::ChaCha20Rng;
use rand_core::SeedableRng;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::{
    collections::BTreeMap,
    env,
    fs,
    io::{self, Read},
    path::{Path, PathBuf},
};

const BACKEND_VERSION: &str = "halo2-plonk-pasta-v1";
const PARAMS_K: u32 = 6;
const EXPECTED_GATE_COUNT: usize = 8;
const EXPECTED_BINDINGS: usize = 12;
const EXPECTED_INSTANCE_VALUES: usize = 13;

#[derive(Debug, Deserialize)]
struct CompileInput {
    circuit_hash: String,
    version: String,
    binding_targets: Vec<String>,
    constraint_count: usize,
    key_root: String,
}

#[derive(Debug, Deserialize)]
struct ProveInput {
    circuit_hash: String,
    trace_hash: String,
    public_inputs_hash: String,
    witness_hash: String,
    a_col: Vec<String>,
    b_col: Vec<String>,
    c_col: Vec<String>,
    instance_values: Vec<String>,
    key_root: String,
}

#[derive(Debug, Deserialize)]
struct VerifyInput {
    circuit_hash: String,
    trace_hash: String,
    public_inputs_hash: String,
    proof_bytes_hex: String,
    instance_values: Vec<String>,
    key_root: String,
}

#[derive(Debug, Serialize)]
struct CompileOutput {
    circuit_hash: String,
    proving_key_id: String,
    verification_key_id: String,
    params_k: u32,
    backend_version: String,
    proving_manifest_path: String,
    verification_manifest_path: String,
}

#[derive(Debug, Serialize)]
struct ProveOutput {
    proof_bytes_hex: String,
    commitments: Vec<String>,
    metadata: BTreeMap<String, String>,
}

#[derive(Debug, Serialize)]
struct VerifyOutput {
    valid: bool,
    reason: String,
    checks: Vec<String>,
    metadata: BTreeMap<String, String>,
}

#[derive(Debug, Serialize)]
struct KeyManifest {
    backend_version: String,
    circuit_hash: String,
    role: String,
    key_id: String,
    params_k: u32,
    cache_mode: String,
}

#[derive(Clone, Debug)]
struct ImportConfig {
    a: Column<Advice>,
    b: Column<Advice>,
    c: Column<Advice>,
    instance: Column<Instance>,
    mul_selector: Selector,
    add_selector: Selector,
}

#[derive(Clone, Debug)]
struct ImportCircuit {
    a_col: Vec<Fp>,
    b_col: Vec<Fp>,
    c_col: Vec<Fp>,
    public_bindings: Vec<Fp>,
}

impl ImportCircuit {
    fn empty(binding_count: usize) -> Self {
        Self {
            a_col: vec![Fp::ZERO; EXPECTED_GATE_COUNT],
            b_col: vec![Fp::ZERO; EXPECTED_GATE_COUNT],
            c_col: vec![Fp::ZERO; EXPECTED_GATE_COUNT],
            public_bindings: vec![Fp::ZERO; binding_count],
        }
    }
}

impl Circuit<Fp> for ImportCircuit {
    type Config = ImportConfig;
    type FloorPlanner = SimpleFloorPlanner;

    fn without_witnesses(&self) -> Self {
        ImportCircuit::empty(self.public_bindings.len())
    }

    fn configure(meta: &mut ConstraintSystem<Fp>) -> Self::Config {
        let a = meta.advice_column();
        let b = meta.advice_column();
        let c = meta.advice_column();
        let instance = meta.instance_column();
        meta.enable_equality(a);
        meta.enable_equality(b);
        meta.enable_equality(c);
        meta.enable_equality(instance);

        let mul_selector = meta.selector();
        let add_selector = meta.selector();

        meta.create_gate("mul_gate", |meta| {
            let s = meta.query_selector(mul_selector);
            let a_cur = meta.query_advice(a, Rotation::cur());
            let b_cur = meta.query_advice(b, Rotation::cur());
            let c_cur = meta.query_advice(c, Rotation::cur());
            vec![s * (a_cur * b_cur - c_cur)]
        });

        meta.create_gate("add_gate", |meta| {
            let s = meta.query_selector(add_selector);
            let a_cur = meta.query_advice(a, Rotation::cur());
            let b_cur = meta.query_advice(b, Rotation::cur());
            let c_cur = meta.query_advice(c, Rotation::cur());
            vec![s * (a_cur + b_cur - c_cur)]
        });

        ImportConfig {
            a,
            b,
            c,
            instance,
            mul_selector,
            add_selector,
        }
    }

    fn synthesize(
        &self,
        config: Self::Config,
        mut layouter: impl Layouter<Fp>,
    ) -> Result<(), Error> {
        let (landed_cost_cell, binding_cells) = layouter.assign_region(
            || "import_landed_cost",
            |mut region| {
                let mut landed_cost_cell: Option<AssignedCell<Fp, Fp>> = None;
                let mut binding_cells: Vec<AssignedCell<Fp, Fp>> = Vec::with_capacity(self.public_bindings.len());

                for row in 0..EXPECTED_GATE_COUNT {
                    let a_cell = region.assign_advice(|| "a", config.a, row, || Value::known(self.a_col[row]))?;
                    let b_cell = region.assign_advice(|| "b", config.b, row, || Value::known(self.b_col[row]))?;
                    let c_cell = region.assign_advice(|| "c", config.c, row, || Value::known(self.c_col[row]))?;
                    if row < 5 {
                        config.mul_selector.enable(&mut region, row)?;
                    } else {
                        config.add_selector.enable(&mut region, row)?;
                    }
                    let _ = a_cell;
                    let _ = b_cell;
                    if row == 7 {
                        landed_cost_cell = Some(c_cell.clone());
                    }
                }

                for (offset, value) in self.public_bindings.iter().enumerate() {
                    let cell = region.assign_advice(|| "binding", config.a, EXPECTED_GATE_COUNT + offset, || Value::known(*value))?;
                    binding_cells.push(cell);
                }

                Ok((landed_cost_cell.expect("landed cost cell must exist"), binding_cells))
            },
        )?;

        layouter.constrain_instance(landed_cost_cell.cell(), config.instance, 0)?;
        for (index, cell) in binding_cells.iter().enumerate() {
            layouter.constrain_instance(cell.cell(), config.instance, index + 1)?;
        }
        Ok(())
    }
}

fn sha256_hex_bytes(data: &[u8]) -> String {
    hex::encode(Sha256::digest(data))
}

fn sha256_hex_str(data: &str) -> String {
    sha256_hex_bytes(data.as_bytes())
}

fn fp_from_decimal(value: &str) -> Result<Fp, String> {
    Fp::from_str_vartime(value).ok_or_else(|| format!("invalid field element: {value}"))
}

fn parse_fp_vec(values: &[String]) -> Result<Vec<Fp>, String> {
    values.iter().map(|value| fp_from_decimal(value)).collect()
}

fn deterministic_rng_seed(circuit_hash: &str, trace_hash: &str, public_inputs_hash: &str, witness_hash: &str) -> [u8; 32] {
    let mut hasher = Sha256::new();
    hasher.update(circuit_hash.as_bytes());
    hasher.update(trace_hash.as_bytes());
    hasher.update(public_inputs_hash.as_bytes());
    hasher.update(witness_hash.as_bytes());
    hasher.finalize().into()
}

fn ensure_key_root(path: &str) -> Result<(PathBuf, PathBuf), String> {
    let root = PathBuf::from(path);
    let proving = root.join("proving_key");
    let verifying = root.join("verification_key");
    fs::create_dir_all(&proving).map_err(|err| err.to_string())?;
    fs::create_dir_all(&verifying).map_err(|err| err.to_string())?;
    Ok((proving, verifying))
}

fn key_ids(circuit_hash: &str) -> (String, String) {
    let proving_key_id = sha256_hex_str(&format!("{}:proving:{}:{}", BACKEND_VERSION, PARAMS_K, circuit_hash));
    let verification_key_id = sha256_hex_str(&format!("{}:verification:{}:{}", BACKEND_VERSION, PARAMS_K, circuit_hash));
    (proving_key_id, verification_key_id)
}

fn write_manifest(path: &Path, manifest: &KeyManifest) -> Result<(), String> {
    let body = serde_json::to_string_pretty(manifest).map_err(|err| err.to_string())?;
    fs::write(path, body).map_err(|err| err.to_string())
}

fn compile_keys(input: CompileInput) -> Result<CompileOutput, String> {
    if input.constraint_count != EXPECTED_GATE_COUNT {
        return Err(format!("unexpected gate count: {}", input.constraint_count));
    }
    if input.binding_targets.len() != EXPECTED_INSTANCE_VALUES {
        return Err(format!("unexpected binding target count: {}", input.binding_targets.len()));
    }
    let (proving_dir, verifying_dir) = ensure_key_root(&input.key_root)?;
    let (proving_key_id, verification_key_id) = key_ids(&input.circuit_hash);
    let proving_manifest_path = proving_dir.join(format!("{}_{}.json", input.version, input.circuit_hash));
    let verification_manifest_path = verifying_dir.join(format!("{}_{}.json", input.version, input.circuit_hash));

    let proving_manifest = KeyManifest {
        backend_version: BACKEND_VERSION.to_string(),
        circuit_hash: input.circuit_hash.clone(),
        role: "proving".to_string(),
        key_id: proving_key_id.clone(),
        params_k: PARAMS_K,
        cache_mode: "deterministic-regeneration".to_string(),
    };
    let verification_manifest = KeyManifest {
        backend_version: BACKEND_VERSION.to_string(),
        circuit_hash: input.circuit_hash.clone(),
        role: "verification".to_string(),
        key_id: verification_key_id.clone(),
        params_k: PARAMS_K,
        cache_mode: "deterministic-regeneration".to_string(),
    };

    write_manifest(&proving_manifest_path, &proving_manifest)?;
    write_manifest(&verification_manifest_path, &verification_manifest)?;

    Ok(CompileOutput {
        circuit_hash: input.circuit_hash,
        proving_key_id,
        verification_key_id,
        params_k: PARAMS_K,
        backend_version: BACKEND_VERSION.to_string(),
        proving_manifest_path: proving_manifest_path.to_string_lossy().to_string(),
        verification_manifest_path: verification_manifest_path.to_string_lossy().to_string(),
    })
}

fn build_circuit(input: &ProveInput) -> Result<(ImportCircuit, Vec<Fp>), String> {
    if input.a_col.len() != EXPECTED_GATE_COUNT || input.b_col.len() != EXPECTED_GATE_COUNT || input.c_col.len() != EXPECTED_GATE_COUNT {
        return Err("unexpected wire column length".to_string());
    }
    if input.instance_values.len() != EXPECTED_INSTANCE_VALUES {
        return Err(format!("unexpected instance value length: {}", input.instance_values.len()));
    }
    let instance_values = parse_fp_vec(&input.instance_values)?;
    let public_bindings = instance_values[1..].to_vec();
    Ok((
        ImportCircuit {
            a_col: parse_fp_vec(&input.a_col)?,
            b_col: parse_fp_vec(&input.b_col)?,
            c_col: parse_fp_vec(&input.c_col)?,
            public_bindings,
        },
        instance_values,
    ))
}

fn prove(input: ProveInput) -> Result<ProveOutput, String> {
    let _compile = compile_keys(CompileInput {
        circuit_hash: input.circuit_hash.clone(),
        version: "import-landed-cost-plonk-v2-halo2".to_string(),
        binding_targets: vec!["landed_cost_fp".to_string(); EXPECTED_INSTANCE_VALUES],
        constraint_count: EXPECTED_GATE_COUNT,
        key_root: input.key_root.clone(),
    })?;
    let params: Params<EqAffine> = Params::new(PARAMS_K);
    let (circuit, instance_values) = build_circuit(&input)?;
    let mock_prover = MockProver::run(PARAMS_K, &circuit, vec![instance_values.clone()])
        .map_err(|err| format!("mock prover setup failed: {err:?}"))?;
    mock_prover
        .verify()
        .map_err(|failures| format!("circuit constraint failure: {failures:?}"))?;
    let empty_circuit = ImportCircuit::empty(EXPECTED_BINDINGS);
    let vk = keygen_vk(&params, &empty_circuit).map_err(|err| format!("keygen_vk failed: {err:?}"))?;
    let pk = keygen_pk(&params, vk, &empty_circuit).map_err(|err| format!("keygen_pk failed: {err:?}"))?;

    let mut transcript = Blake2bWrite::<Vec<u8>, EqAffine, Challenge255<_>>::init(vec![]);
    let instance_refs: [&[Fp]; 1] = [&instance_values[..]];
    let mut rng = ChaCha20Rng::from_seed(deterministic_rng_seed(
        &input.circuit_hash,
        &input.trace_hash,
        &input.public_inputs_hash,
        &input.witness_hash,
    ));
    create_proof(
        &params,
        &pk,
        &[circuit],
        &[&instance_refs],
        &mut rng,
        &mut transcript,
    )
    .map_err(|err| format!("create_proof failed: {err:?}"))?;

    let proof = transcript.finalize();
    let (proving_key_id, verification_key_id) = key_ids(&input.circuit_hash);
    let mut metadata = BTreeMap::new();
    metadata.insert("backend_version".to_string(), BACKEND_VERSION.to_string());
    metadata.insert("circuit_hash".to_string(), input.circuit_hash);
    metadata.insert("trace_hash".to_string(), input.trace_hash);
    metadata.insert("public_inputs_hash".to_string(), input.public_inputs_hash);
    metadata.insert("proving_key_id".to_string(), proving_key_id);
    metadata.insert("verification_key_id".to_string(), verification_key_id);
    metadata.insert("params_k".to_string(), PARAMS_K.to_string());

    Ok(ProveOutput {
        proof_bytes_hex: hex::encode(proof),
        commitments: vec![],
        metadata,
    })
}

fn verify(input: VerifyInput) -> Result<VerifyOutput, String> {
    let _compile = compile_keys(CompileInput {
        circuit_hash: input.circuit_hash.clone(),
        version: "import-landed-cost-plonk-v2-halo2".to_string(),
        binding_targets: vec!["landed_cost_fp".to_string(); EXPECTED_INSTANCE_VALUES],
        constraint_count: EXPECTED_GATE_COUNT,
        key_root: input.key_root.clone(),
    })?;
    if input.instance_values.len() != EXPECTED_INSTANCE_VALUES {
        return Err(format!("unexpected instance value length: {}", input.instance_values.len()));
    }
    let params: Params<EqAffine> = Params::new(PARAMS_K);
    let empty_circuit = ImportCircuit::empty(EXPECTED_BINDINGS);
    let vk = keygen_vk(&params, &empty_circuit).map_err(|err| format!("keygen_vk failed: {err:?}"))?;
    let instance_values = parse_fp_vec(&input.instance_values)?;
    let proof_bytes = hex::decode(&input.proof_bytes_hex).map_err(|err| format!("invalid proof hex: {err}"))?;
    let strategy = SingleVerifier::new(&params);
    let instance_refs: [&[Fp]; 1] = [&instance_values[..]];
    let mut transcript = Blake2bRead::<_, EqAffine, Challenge255<_>>::init(&proof_bytes[..]);
    let verification_result = verify_proof(&params, &vk, strategy, &[&instance_refs], &mut transcript);
    let verified = verification_result.is_ok();
    let (proving_key_id, verification_key_id) = key_ids(&input.circuit_hash);
    let mut metadata = BTreeMap::new();
    metadata.insert("backend_version".to_string(), BACKEND_VERSION.to_string());
    metadata.insert("circuit_hash".to_string(), input.circuit_hash);
    metadata.insert("trace_hash".to_string(), input.trace_hash);
    metadata.insert("public_inputs_hash".to_string(), input.public_inputs_hash);
    metadata.insert("proving_key_id".to_string(), proving_key_id);
    metadata.insert("verification_key_id".to_string(), verification_key_id);
    metadata.insert("params_k".to_string(), PARAMS_K.to_string());

    Ok(VerifyOutput {
        valid: verified,
        reason: if verified {
            "Halo2 proof verified".to_string()
        } else {
            format!("Halo2 proof verification failed: {:?}", verification_result.err())
        },
        checks: if verified {
            vec![
                "public_instance_binding_ok".to_string(),
                "proof_bytes_valid".to_string(),
                "halo2_verification_ok".to_string(),
            ]
        } else {
            vec!["halo2_verification_failed".to_string()]
        },
        metadata,
    })
}

fn read_stdin() -> Result<String, String> {
    let mut buf = String::new();
    io::stdin().read_to_string(&mut buf).map_err(|err| err.to_string())?;
    Ok(buf)
}

fn print_json<T: Serialize>(value: &T) -> Result<(), String> {
    let body = serde_json::to_string(value).map_err(|err| err.to_string())?;
    println!("{}", body);
    Ok(())
}

fn main() {
    let mut args = env::args();
    let _program = args.next();
    let Some(command) = args.next() else {
        eprintln!("expected command: compile|prove|verify");
        std::process::exit(2);
    };

    let input = match read_stdin() {
        Ok(input) => input,
        Err(err) => {
            eprintln!("failed to read stdin: {err}");
            std::process::exit(1);
        }
    };

    let result = match command.as_str() {
        "compile" => serde_json::from_str::<CompileInput>(&input)
            .map_err(|err| err.to_string())
            .and_then(compile_keys)
            .and_then(|output| print_json(&output)),
        "prove" => serde_json::from_str::<ProveInput>(&input)
            .map_err(|err| err.to_string())
            .and_then(prove)
            .and_then(|output| print_json(&output)),
        "verify" => serde_json::from_str::<VerifyInput>(&input)
            .map_err(|err| err.to_string())
            .and_then(verify)
            .and_then(|output| print_json(&output)),
        other => Err(format!("unknown command: {other}")),
    };

    if let Err(err) = result {
        eprintln!("{err}");
        std::process::exit(1);
    }
}
