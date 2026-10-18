#!/usr/bin/env python3
"""
ep_stack.py — Polyglot Stack & Framework Detection Engine for EP-OS
"""

import os
from typing import Dict, List, Tuple

STACK_DEFINITIONS: List[Tuple[str, List[str], str, str, str, str]] = [
    ("rust", ["Cargo.toml"], "cargo clippy --all-targets -- -D warnings", "cargo test --all-targets", "cargo build --release", "cargo audit"),
    ("go", ["go.mod"], "golangci-lint run ./...", "go test -v -race -cover ./...", "go build ./cmd/...", "govulncheck ./..."),
    ("ts", ["package.json", "tsconfig.json"], "pnpm eslint . --max-warnings 0", "pnpm vitest run --coverage", "pnpm tsup src/index.ts", "pnpm audit --audit-level high"),
    ("dart", ["pubspec.yaml"], "flutter analyze --fatal-infos", "flutter test --coverage", "flutter build apk --release", "dart pub audit"),
    ("php", ["composer.json"], "phpstan analyse --level=8", "vendor/bin/pest", "composer dump-autoload -o", "composer audit"),
    ("python", ["pyproject.toml", "requirements.txt"], "ruff check . && mypy .", "pytest --cov=.", "python -m build", "pip-audit"),
    ("dotnet", [".csproj", ".sln"], "dotnet format --verify-no-changes", "dotnet test", "dotnet build -c Release", "dotnet list package --vulnerable"),
    ("java", ["pom.xml"], "mvn checkstyle:check", "mvn test", "mvn package", "mvn dependency-check:check"),
    ("kotlin", ["build.gradle.kts"], "gradle ktlintCheck", "gradle test", "gradle build", "gradle dependencyCheckAnalyze"),
    ("swift", ["Package.swift"], "swiftlint --strict", "swift test", "swift build -c release", "swift package audit"),
    ("scala", ["build.sbt"], "sbt scalafix", "sbt test", "sbt package", "sbt dependencyCheck"),
    ("elixir", ["mix.exs"], "mix credo --strict", "mix test", "mix compile", "mix hex.audit"),
    ("cpp", ["CMakeLists.txt"], "clang-tidy", "ctest", "cmake --build .", "echo 'cpp audit'"),
]


def detect_stack(project_dir: str) -> Dict[str, str]:
    """Inspects project directory manifests to detect language and default targets."""
    if not os.path.exists(project_dir):
        return {
            "lang": "unknown",
            "lint": "echo 'No lint command'",
            "test": "echo 'No test command'",
            "build": "echo 'No build command'",
            "audit": "echo 'No audit command'",
        }
    files = os.listdir(project_dir)
    for lang, triggers, lint_cmd, test_cmd, build_cmd, audit_cmd in STACK_DEFINITIONS:
        for t in triggers:
            if t.startswith("."):
                if any(f.endswith(t) for f in files):
                    return {"lang": lang, "lint": lint_cmd, "test": test_cmd, "build": build_cmd, "audit": audit_cmd}
            elif t in files:
                return {"lang": lang, "lint": lint_cmd, "test": test_cmd, "build": build_cmd, "audit": audit_cmd}
    return {
        "lang": "generic",
        "lint": "echo 'No lint target configured'",
        "test": "echo 'No test target configured'",
        "build": "echo 'No build target configured'",
        "audit": "echo 'No audit target configured'",
    }
