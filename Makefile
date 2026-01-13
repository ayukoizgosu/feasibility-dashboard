
.PHONY: help
help:
	@echo "Targets:"
	@echo "  fmt        - run formatter (project-specific)"
	@echo "  lint       - run linter (project-specific)"
	@echo "  test       - run tests (project-specific)"
	@echo "  scan       - run semgrep + gitleaks (if installed)"
	@echo "  sbom       - generate SBOM via syft (if installed)"

fmt:
	@echo "TODO: wire formatter (prettier/ruff/gofmt) for your stack"

lint:
	@echo "TODO: wire linter (eslint/ruff/golangci-lint) for your stack"

test:
	@echo "TODO: wire tests (jest/pytest/go test) for your stack"

scan:
	@command -v semgrep >/dev/null 2>&1 && semgrep scan --config p/default || echo "semgrep not installed"
	@command -v gitleaks >/dev/null 2>&1 && gitleaks detect --config gitleaks.toml || echo "gitleaks not installed"

sbom:
	@command -v syft >/dev/null 2>&1 && syft dir:. -o spdx-json=sbom/sbom.spdx.json || echo "syft not installed"
