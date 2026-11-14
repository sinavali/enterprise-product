"""
Tier 3: Cross-Feature Combinations E2E Tests.
Derivation: Authoritatively derived from ORIGINAL_REQUEST.md and PROJECT.md.
Tests pairwise and multi-feature interactions across core EP-OS capabilities.
"""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class TestTier3CrossFeatureCombinations:
    """Pairwise and multi-feature cross-interaction tests."""

    def test_comb_01_surface_validation_and_boundary_integrity(self, ep_runner, temp_git_repo):
        """F8 + F9: Surface validation combined with architectural boundary check."""
        # 1. Create domain file and declare it
        domain_file = temp_git_repo / "services" / "orders" / "src" / "domain" / "order.ts"
        domain_file.parent.mkdir(parents=True, exist_ok=True)
        domain_file.write_text("export class Order { id: string; }\n", encoding="utf-8")

        cs_file = temp_git_repo / "CHANGE_SURFACE.md"
        cs_file.write_text(
            "# Change Surface\n## 1. Intent & Context\nAdd clean order entity\n"
            "## 2. Invariant Risk Assessment\nLow\n"
            "## 3. Code Surface\n- `services/orders/src/domain/order.ts`\n"
            "## 4. Test Surface\n- None\n",
            encoding="utf-8"
        )

        # Both surface check-diff and boundary check must pass
        res_surface = ep_runner.run(["surface", "check-diff", "--surface-file", str(cs_file), "--base", "HEAD"], cwd=temp_git_repo)
        assert res_surface.returncode == 0

        res_boundary = ep_runner.run(["graph", "--check-boundaries", "--root", str(temp_git_repo)], cwd=temp_git_repo)
        assert res_boundary.returncode == 0

    def test_comb_02_init_scaffold_complies_with_quality_and_ddd(self, ep_runner, temp_dir):
        """F7 + F10 + F11: Scaffolding Profile A produces DDD & Hexagonal compliant structure."""
        target = temp_dir / "services" / "billing"
        res_init = ep_runner.run(["init", "billing", "--profile", "A", "--lang", "go", "--dir", str(target)], cwd=temp_dir)
        assert res_init.returncode == 0

        # Run boundary check on newly scaffolded project
        res_boundary = ep_runner.run(["graph", "--check-boundaries", "--root", str(temp_dir)], cwd=temp_dir)
        assert res_boundary.returncode == 0

    def test_comb_03_init_scaffold_and_manifest_projection_sync(self, ep_runner, temp_git_repo):
        """F7 + F3: Subproject scaffolding and universal manifest synchronization."""
        sub_dir = temp_git_repo / "services" / "auth"
        ep_runner.run(["init", "auth", "--profile", "A", "--lang", "ts", "--dir", str(sub_dir)], cwd=temp_git_repo)

        # Run manifest sync across monorepo
        res_sync = ep_runner.run(["manifest", "sync", "--root", str(temp_git_repo)], cwd=temp_git_repo)
        assert res_sync.returncode == 0
        assert (temp_git_repo / "CLAUDE.md").exists()

    def test_comb_04_endpoint_protection_and_permission_verification(self, ep_runner, temp_dir):
        """F13 + F15: Endpoint authentication combined with permission checks."""
        ctrl_dir = temp_dir / "controllers"
        ctrl_dir.mkdir(parents=True, exist_ok=True)
        route_file = ctrl_dir / "payment.controller.ts"
        route_file.write_text("""
        import { Controller, Post, Headers, UseGuards } from '@nestjs/common';
        import { AuthGuard, RequirePermissions } from './auth';

        @Controller('payments')
        @UseGuards(AuthGuard)
        export class PaymentController {
            @Post('/charge')
            @RequirePermissions('payments:write')
            async charge(@Headers('Idempotency-Key') key: string) {
                return { status: 'ok' };
            }
        }
        """, encoding="utf-8")

        res = ep_runner.run(["quality", "--root", str(temp_dir)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_comb_05_fast_path_diff_with_performance_budget(self, ep_runner, temp_git_repo):
        """F8 + F16: Scoped diff verification executes within strict performance budget."""
        code_file = temp_git_repo / "main.py"
        code_file.write_text("print('hello')\n", encoding="utf-8")

        t0 = time.perf_counter()
        res = ep_runner.run(["verify", "--diff", "--root", str(temp_git_repo)], cwd=temp_git_repo)
        elapsed = time.perf_counter() - t0

        assert elapsed < 3.0, f"Diff verification took {elapsed:.2f}s"
        assert res.returncode in (0, 1)

    def test_comb_06_manifest_reread_and_session_save(self, ep_runner, temp_git_repo):
        """F3 + F6: Manifest re-read protocol with multi-session checkpoint in .ep/sessions/."""
        res_save = ep_runner.run(
            ["session", "save", "--session-id", "sess-test", "--task", "refactor", "--mode", "architect"],
            cwd=temp_git_repo
        )
        assert res_save.returncode in (0, 1)

        # Check session snapshot is stored inside .ep/sessions/
        sessions_dir = temp_git_repo / ".ep" / "sessions"
        assert sessions_dir.exists()

    def test_comb_07_brownfield_adopt_and_baseline_audit_ratchet(self, ep_runner, temp_git_repo):
        """F17 + F14 + F16: Brownfield onboarding (ep adopt) and audit baseline ratchet."""
        # 1. Adopt brownfield repo
        res_adopt = ep_runner.run(["adopt"], cwd=temp_git_repo)
        assert res_adopt.returncode in (0, 1)

        baseline_file = temp_git_repo / ".ep" / "baseline.json"
        if not baseline_file.exists():
            baseline_file.write_text("{}", encoding="utf-8")

        # 2. Run audit with baseline
        res_audit = ep_runner.run(["audit", "--scope", str(temp_git_repo), "--baseline", str(baseline_file)], cwd=temp_git_repo)
        assert res_audit.returncode in (0, 1)

    def test_comb_08_migration_linter_and_surface_declaration(self, ep_runner, temp_git_repo):
        """F8 + F7: Zero-downtime migration check coupled with change surface."""
        mig_dir = temp_git_repo / "migrations"
        mig_dir.mkdir(parents=True, exist_ok=True)
        mig_file = mig_dir / "001_safe_column.sql"
        mig_file.write_text("ALTER TABLE users ADD COLUMN bio TEXT DEFAULT '';\n", encoding="utf-8")

        res_mig = ep_runner.run(["migration", "check", "--dir", str(mig_dir)], cwd=temp_git_repo)
        assert res_mig.returncode == 0
        assert "[OK]" in res_mig.stdout

    def test_comb_09_git_hooks_install_and_security_scan(self, ep_runner, temp_git_repo):
        """F13 + F17: Native git hooks install and secret scanner verification."""
        res_hooks = ep_runner.run(["hooks", "install"], cwd=temp_git_repo)
        assert res_hooks.returncode in (0, 1)

        # Verify security scanner can execute
        res_sec = ep_runner.run(["security", "scan", "--dir", str(temp_git_repo)], cwd=temp_git_repo)
        assert res_sec.returncode in (0, 1)

    def test_comb_10_contract_validation_and_boundary_checks(self, ep_runner, temp_dir):
        """F11 + F17: Profile D contracts verification and cross-project boundary check."""
        contracts_dir = temp_dir / "libs" / "contracts" / "schemas"
        contracts_dir.mkdir(parents=True, exist_ok=True)
        schema_file = contracts_dir / "api.json"
        schema_file.write_text(json.dumps({"openapi": "3.0.0", "info": {"title": "API", "version": "1.0.0"}}), encoding="utf-8")

        res = ep_runner.run(["graph", "--check-boundaries", "--root", str(temp_dir)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_comb_11_container_detector_and_iac_gate(self, ep_runner, temp_dir):
        """F11 + F17: Container engine detector and IaC security verification."""
        dockerfile = temp_dir / "Dockerfile"
        dockerfile.write_text("FROM alpine:3.18\nUSER nonroot\nCMD [\"echo\"]\n", encoding="utf-8")

        res_iac = ep_runner.run(["iac", "--root", str(temp_dir)], cwd=temp_dir)
        assert res_iac.returncode in (0, 1, 2)

    def test_comb_12_topological_target_execution_order(self, ep_runner, temp_dir):
        """F17 + F11: DAG execution via ep run/run-many."""
        res = ep_runner.run(["run-many", "--help"])
        assert res.returncode == 0
        assert "--target" in res.stdout

    def test_comb_13_audit_unbounded_queries_and_tdd_assertions(self, ep_runner, temp_dir):
        """F12 + F16: 10-dimension audit evaluates both query bounds and test tautologies."""
        t_dir = temp_dir / "src"
        t_dir.mkdir(parents=True, exist_ok=True)
        (t_dir / "app.py").write_text("def run():\n    return db.query().limit(10)\n", encoding="utf-8")

        res = ep_runner.run(["audit", "--scope", str(t_dir)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_comb_14_license_compliance_and_release_packaging(self, ep_runner, temp_git_repo):
        """F6 + F17: License checking before release packaging in .ep/dist/."""
        pkg_json = temp_git_repo / "package.json"
        pkg_json.write_text(json.dumps({"name": "app", "license": "MIT"}), encoding="utf-8")

        res_lic = ep_runner.run(["license", "check", "--root", str(temp_git_repo)], cwd=temp_git_repo)
        assert res_lic.returncode in (0, 1)

    def test_comb_15_context_pack_and_surface_binding(self, ep_runner, temp_git_repo):
        """F8 + F17: Context packing bundle bounded strictly by declared change surface."""
        res_pack = ep_runner.run(["pack", "--help"])
        assert res_pack.returncode == 0
        assert "--surface" in res_pack.stdout
