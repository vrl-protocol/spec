from __future__ import annotations


def prove_request(*args: object, **kwargs: object):
  from zk.provers.stub_prover import prove_request as _prove_request

  return _prove_request(*args, **kwargs)

