"""Field arithmetic utilities for Halo2 PLONK over Pasta Fp.

All operations are deterministic and use the same scalar field as the Rust
Halo2 backend (`pasta::Fp`), so witness generation and native proving stay
field-consistent.
"""
from __future__ import annotations

FIELD_ORDER: int = 28948022309329048855892746252171976963363056481941647379679742748393362948097
N: int = 8  # domain size (must be power of 2, >= number of circuit gates)


def _find_omega() -> int:
    exponent = (FIELD_ORDER - 1) // N
    for candidate in range(2, 512):
        omega = pow(candidate, exponent, FIELD_ORDER)
        if pow(omega, N, FIELD_ORDER) == 1 and pow(omega, N // 2, FIELD_ORDER) != 1:
            return omega
    raise RuntimeError('Unable to derive a primitive 8th root of unity for Pasta Fp')


OMEGA: int = _find_omega()


def field_inv(x: int) -> int:
    return pow(x, FIELD_ORDER - 2, FIELD_ORDER)


def poly_eval(coeffs: list[int], x: int) -> int:
    """Evaluate polynomial (in coefficient form, low-degree first) at x."""
    result = 0
    x_pow = 1
    for c in coeffs:
        result = (result + c * x_pow) % FIELD_ORDER
        x_pow = x_pow * x % FIELD_ORDER
    return result


def intt(values: list[int]) -> list[int]:
    """Inverse NTT: return polynomial coefficients from evaluations on the domain."""
    n = len(values)
    omega_inv = field_inv(OMEGA)
    n_inv = field_inv(n)
    coeffs: list[int] = []
    for k in range(n):
        s = 0
        for j in range(n):
            s = (s + values[j] * pow(omega_inv, j * k, FIELD_ORDER)) % FIELD_ORDER
        coeffs.append(s * n_inv % FIELD_ORDER)
    return coeffs


def poly_divmod_linear(poly: list[int], z: int) -> tuple[list[int], int]:
    """Divide poly(X) by (X - z)."""
    n = len(poly)
    q = [0] * (n - 1)
    running = 0
    for i in range(n - 1, 0, -1):
        running = (poly[i] + running) % FIELD_ORDER
        q[i - 1] = running
        running = running * z % FIELD_ORDER
    remainder = (poly[0] + running) % FIELD_ORDER
    return q, remainder


def kzg_open_coeffs(poly_coeffs: list[int], z: int, v: int) -> list[int]:
    """Compute quotient polynomial coefficients for the deterministic opening check."""
    p = list(poly_coeffs)
    p[0] = (p[0] - v) % FIELD_ORDER
    q, _remainder = poly_divmod_linear(p, z)
    return q


def poly_mul(a: list[int], b: list[int]) -> list[int]:
    """Multiply two polynomials in coefficient form over FIELD_ORDER."""
    if not a or not b:
        return [0]
    n = len(a) + len(b) - 1
    result = [0] * n
    for i, ai in enumerate(a):
        if ai == 0:
            continue
        for j, bj in enumerate(b):
            result[i + j] = (result[i + j] + ai * bj) % FIELD_ORDER
    return result


def poly_add(a: list[int], b: list[int]) -> list[int]:
    """Add two polynomials in coefficient form over FIELD_ORDER."""
    n = max(len(a), len(b))
    result = [0] * n
    for i, v in enumerate(a):
        result[i] = (result[i] + v) % FIELD_ORDER
    for i, v in enumerate(b):
        result[i] = (result[i] + v) % FIELD_ORDER
    return result


def poly_scalar_mul(p: list[int], scalar: int) -> list[int]:
    """Multiply polynomial by a scalar field element."""
    return [(c * scalar) % FIELD_ORDER for c in p]


def poly_divmod(dividend: list[int], divisor: list[int]) -> tuple[list[int], list[int]]:
    """Polynomial long division over FIELD_ORDER."""
    remainder = list(dividend)
    quotient: list[int] = []
    deg_div = len(divisor) - 1
    lead_inv = pow(divisor[-1], FIELD_ORDER - 2, FIELD_ORDER)

    while len(remainder) > deg_div:
        coeff = remainder[-1] * lead_inv % FIELD_ORDER
        quotient.append(coeff)
        for i in range(len(divisor)):
            idx = len(remainder) - len(divisor) + i
            remainder[idx] = (remainder[idx] - coeff * divisor[i]) % FIELD_ORDER
        remainder.pop()

    quotient.reverse()
    return quotient, remainder


def vanishing_poly(n: int) -> list[int]:
    """Return coefficients of Z_H(X) = X^n - 1."""
    coeffs = [0] * (n + 1)
    coeffs[0] = FIELD_ORDER - 1
    coeffs[n] = 1
    return coeffs


def fr_to_bytes(v: int) -> bytes:
    return v.to_bytes(32, 'big')


def fr_from_bytes(b: bytes) -> int:
    return int.from_bytes(b, 'big')

