
# SBOM Policy

## Objective
Maintain a machine-readable SBOM for each release/build to improve transparency and vulnerability response.

## Format
- SPDX JSON (default) or CycloneDX (acceptable)
- Must include direct + transitive dependencies where feasible.

## Minimum elements
Follow "minimum elements" guidance (baseline) and update as practice evolves.

## Frequency
- Generate SBOM on every CI build for main and on releases.
- Store as build artifact and attach to releases.

## Tooling
- Syft for generation
- Optional: Grype for vulnerability scanning
