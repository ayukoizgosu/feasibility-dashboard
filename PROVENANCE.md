
# Build provenance goals (SLSA-oriented)

## Why
Capture verifiable metadata about how artifacts were built.

## Current (target level)
- Build L1: provenance exists (at least) for releases.
- Build L2+: consider signed provenance as maturity increases.

## What we will produce
- SBOM per build
- CI workflow metadata (commit SHA, builder, timestamps)
- Optional: signed provenance/attestation if supported by platform

## Next steps
- Add provenance generation to CI for release artifacts
- Store attestations with artifacts or release assets
