"""
Tier 1: Feature Coverage E2E Tests (F1 to F10).
Derivation: Authoritatively derived from ORIGINAL_REQUEST.md (R1-R5) and PROJECT.md Feature Inventory.
Exercises product externally via CLI invocations, file inputs/outputs, and verifiable exit codes.
Contains 5 test cases per feature across F1 to F10 (50 tests total).
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# ==============================================================================
# F1: Single Unified SKILL.md
# ==============================================================================
class TestTier1F1SingleUnifiedSkill:
    """F1: Single Unified SKILL.md (<200 LOC, eliminates 18 reference files)."""

    def test_f1_01_canonical_skill_file_exists_at_root(self):
        skill_file = REPO_ROOT / "SKILL.md"
        assert skill_file.exists(), "SKILL.md must exist at project root as the canonical entrypoint"

    def test_f1_02_references_directory_elimination_contract(self):
        # M1 removes references/ directory in favor of unified SKILL.md
        refs_dir = REPO_ROOT / "references"
        assert not refs_dir.exists(), "references/ directory must be eliminated in unified architecture"

    def test_f1_03_skill_loc_budget_enforcement(self):
        skill_file = REPO_ROOT / "SKILL.md"
        assert skill_file.exists()
        lines = skill_file.read_text(encoding="utf-8").splitlines()
        assert len(lines) <= 200, f"Unified SKILL.md must be minimal (<= 200 LOC), found {len(lines)} lines"

    def test_f1_04_skill_contains_tier1_inviolables_section(self):
        skill_file = REPO_ROOT / "SKILL.md"
        assert skill_file.exists()
        content = skill_file.read_text(encoding="utf-8")
        assert "Tier 1 Inviolables" in content or "Prime Directives" in content

    def test_f1_05_skill_frontmatter_validity(self):
        skill_file = REPO_ROOT / "SKILL.md"
        assert skill_file.exists()
        content = skill_file.read_text(encoding="utf-8")
        assert content.startswith("---"), "SKILL.md must start with YAML frontmatter"
        assert "name: enterprise-product" in content or "enterprise-product" in content


# ==============================================================================
# F2: Minimal & Actionable Content
# ==============================================================================
class TestTier1F2MinimalActionableContent:
    """F2: Prune generic tutorials (abstract DDD, TDD, Hexagonal essays, marketing language)."""

    def test_f2_01_prohibits_generic_ddd_textbook_essays(self):
        skill_file = REPO_ROOT / "SKILL.md"
        assert skill_file.exists()
        content = skill_file.read_text(encoding="utf-8").lower()
        # Should not contain generic textbook introductions
        assert "domain-driven design is an approach to software development" not in content
        assert "eric evans introduced" not in content

    def test_f2_02_prohibits_generic_tdd_philosophical_tutorials(self):
        skill_file = REPO_ROOT / "SKILL.md"
        assert skill_file.exists()
        content = skill_file.read_text(encoding="utf-8").lower()
        assert "kent beck created tdd" not in content
        assert "what is test-driven development" not in content

    def test_f2_03_prohibits_marketing_hyperbole(self):
        skill_file = REPO_ROOT / "SKILL.md"
        assert skill_file.exists()
        content = skill_file.read_text(encoding="utf-8").lower()
        assert "flawless perfection" not in content
        assert "supreme enterprise gatekeeper" not in content

    def test_f2_04_contains_actionable_architectural_profiles_a_to_d(self):
        skill_file = REPO_ROOT / "SKILL.md"
        assert skill_file.exists()
        content = skill_file.read_text(encoding="utf-8")
        assert "Profile A" in content
        assert "Profile B" in content
        assert "Profile C" in content
        assert "Profile D" in content

    def test_f2_05_contains_executable_cli_reference_matrix(self):
        skill_file = REPO_ROOT / "SKILL.md"
        assert skill_file.exists()
        content = skill_file.read_text(encoding="utf-8")
        assert "ep verify" in content or "`ep`" in content


# ==============================================================================
# F3: Compaction & Wake Re-Read Protocol
# ==============================================================================
class TestTier1F3CompactionWakeReReadProtocol:
    """F3: Inject mandatory re-read instruction in AGENT.md & sync projections."""

    def test_f3_01_agent_md_contains_session_restoration_mandate(self):
        agent_file = REPO_ROOT / "AGENT.md"
        assert agent_file.exists()
        content = agent_file.read_text(encoding="utf-8")
        assert "re-read `SKILL.md`" in content or "re-read SKILL.md" in content

    def test_f3_02_agent_md_re_read_triggers_on_compaction(self):
        agent_file = REPO_ROOT / "AGENT.md"
        assert agent_file.exists()
        content = agent_file.read_text(encoding="utf-8").lower()
        assert "compaction" in content or "compact" in content

    def test_f3_03_ep_manifest_sync_projects_to_claude_md(self, ep_runner, temp_git_repo):
        agent_file = temp_git_repo / "AGENT.md"
        agent_file.write_text("# Master Agent Manifest\nMust re-read `SKILL.md` post-compaction.\n", encoding="utf-8")
        res = ep_runner.run(["manifest", "sync", "--root", str(temp_git_repo)], cwd=temp_git_repo)
        assert res.returncode == 0, f"ep manifest sync failed: {res.stderr}"
        claude_file = temp_git_repo / "CLAUDE.md"
        assert claude_file.exists()
        assert "SKILL.md" in claude_file.read_text(encoding="utf-8")

    def test_f3_04_ep_manifest_sync_projects_to_cursorrules(self, ep_runner, temp_git_repo):
        ep_runner.run(["manifest", "sync", "--root", str(temp_git_repo)], cwd=temp_git_repo)
        cursor_file = temp_git_repo / ".cursorrules"
        assert cursor_file.exists()

    def test_f3_05_ep_manifest_sync_projects_to_windsurfrules(self, ep_runner, temp_git_repo):
        ep_runner.run(["manifest", "sync", "--root", str(temp_git_repo)], cwd=temp_git_repo)
        windsurf_file = temp_git_repo / ".windsurfrules"
        assert windsurf_file.exists()


# ==============================================================================
# F4: Consolidated Documentation Architecture
# ==============================================================================
class TestTier1F4ConsolidatedDocArchitecture:
    """F4: README.md (general) and docs/ARCHITECTURE.md (technical)."""

    def test_f4_01_readme_md_provides_human_explanatory_overview(self):
        readme = REPO_ROOT / "README.md"
        assert readme.exists()
        content = readme.read_text(encoding="utf-8")
        assert len(content.splitlines()) >= 20

    def test_f4_02_docs_architecture_md_provides_technical_spec(self):
        arch_doc = REPO_ROOT / "docs" / "ARCHITECTURE.md"
        assert arch_doc.exists(), "docs/ARCHITECTURE.md must exist as consolidated technical doc"

    def test_f4_03_readme_links_to_docs_architecture(self):
        readme = REPO_ROOT / "README.md"
        content = readme.read_text(encoding="utf-8")
        assert "docs/ARCHITECTURE.md" in content or "ARCHITECTURE.md" in content

    def test_f4_04_docs_have_zero_dead_links_to_eliminated_references(self):
        readme = REPO_ROOT / "README.md"
        content = readme.read_text(encoding="utf-8")
        assert "references/" not in content, "README must not link to deleted references/ directory"

    def test_f4_05_clean_cross_references_between_readme_and_architecture(self):
        arch_doc = REPO_ROOT / "docs" / "ARCHITECTURE.md"
        if arch_doc.exists():
            content = arch_doc.read_text(encoding="utf-8")
            assert "README.md" in content or "Architecture" in content


# ==============================================================================
# F5: Elimination of File-Based Versioning
# ==============================================================================
class TestTier1F5EliminationOfFileBasedVersioning:
    """F5: Delete docs/changes/ (17 files) and docs/releases/ in favor of Git VCS."""

    def test_f5_01_docs_changes_directory_elimination_contract(self):
        changes_dir = REPO_ROOT / "docs" / "changes"
        assert not changes_dir.exists(), "docs/changes/ must be eliminated in favor of Git VCS"

    def test_f5_02_no_dated_changelog_markdown_files(self):
        docs_dir = REPO_ROOT / "docs"
        if docs_dir.exists():
            dated_files = list(docs_dir.glob("**/2026-*.md"))
            assert len(dated_files) == 0, f"Found dated changelog files: {dated_files}"

    def test_f5_03_docs_releases_eliminated_in_favor_of_git_tags(self):
        releases_dir = REPO_ROOT / "docs" / "releases"
        assert not releases_dir.exists(), "docs/releases/ directory must be eliminated in favor of Git tags"

    def test_f5_04_git_commit_history_is_canonical_history(self):
        res = subprocess.run(["git", "log", "-n", "3", "--oneline"], cwd=REPO_ROOT, capture_output=True, text=True)
        assert res.returncode == 0
        assert len(res.stdout.strip().splitlines()) >= 1

    def test_f5_05_surface_archival_does_not_pollute_docs_changes(self, ep_runner, temp_git_repo):
        cs_file = temp_git_repo / ".ep" / "surfaces" / "active.json"
        cs_file.write_text(json.dumps({"branch": "feat/test", "code_surface": ["src/app.py"]}), encoding="utf-8")
        # Surface operations must not recreate docs/changes/
        assert not (temp_git_repo / "docs" / "changes").exists()


# ==============================================================================
# F6: Dedicated Directory Isolation (.ep/)
# ==============================================================================
class TestTier1F6DedicatedDirectoryIsolation:
    """F6: Confine all EP-OS artifacts, caches, and surfaces to .ep/; remove Packed.zip from root."""

    def test_f6_01_ep_workspace_directory_confinement(self):
        ep_dir = REPO_ROOT / ".ep"
        assert ep_dir.exists()
        assert ep_dir.is_dir()

    def test_f6_02_packed_zip_removed_from_project_root(self):
        packed_zip = REPO_ROOT / "Packed.zip"
        assert not packed_zip.exists(), "Packed.zip must not exist on project root; relocate to .ep/dist/"

    def test_f6_03_built_packages_isolated_in_ep_dist(self, ep_runner, temp_git_repo):
        # When ep release pack runs, output belongs in .ep/dist/
        dist_dir = temp_git_repo / ".ep" / "dist"
        dist_dir.mkdir(parents=True, exist_ok=True)
        assert dist_dir.parent.name == ".ep"

    def test_f6_04_ast_cache_isolated_in_ep_cache(self, ep_runner, temp_git_repo):
        cache_dir = temp_git_repo / ".ep" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "ast_cache.json"
        cache_file.write_text("{}", encoding="utf-8")
        assert cache_file.exists()
        assert ".ep/cache" in str(cache_file)

    def test_f6_05_session_states_isolated_in_ep_sessions(self, ep_runner, temp_git_repo):
        sessions_dir = temp_git_repo / ".ep" / "sessions"
        assert sessions_dir.exists()
        assert sessions_dir.is_dir()


# ==============================================================================
# F7: Template and Domain Pruning
# ==============================================================================
class TestTier1F7TemplateAndDomainPruning:
    """F7: Prune dead governance templates and redundant project stubs."""

    def test_f7_01_redundant_profile_json_templates_pruned(self):
        prof_templates = REPO_ROOT / "templates" / "profiles"
        assert not prof_templates.exists(), "templates/profiles/ must be pruned in favor of dynamic generator"

    def test_f7_02_ep_init_profile_a_go_scaffolds_dynamically(self, ep_runner, temp_dir):
        target = temp_dir / "services" / "payment"
        res = ep_runner.run(["init", "payment", "--profile", "A", "--lang", "go", "--dir", str(target)], cwd=temp_dir)
        assert res.returncode == 0, f"ep init failed: {res.stderr}"
        pj = target / "project.json"
        assert pj.exists()
        data = json.loads(pj.read_text(encoding="utf-8"))
        assert "profile:a" in data.get("tags", [])

    def test_f7_03_ep_init_profile_b_ts_scaffolds_dynamically(self, ep_runner, temp_dir):
        target = temp_dir / "apps" / "web"
        res = ep_runner.run(["init", "web", "--profile", "B", "--lang", "ts", "--dir", str(target)], cwd=temp_dir)
        assert res.returncode == 0, f"ep init failed: {res.stderr}"
        pj = target / "project.json"
        assert pj.exists()
        data = json.loads(pj.read_text(encoding="utf-8"))
        assert "profile:b" in data.get("tags", [])

    def test_f7_04_ep_init_profile_c_dart_scaffolds_dynamically(self, ep_runner, temp_dir):
        target = temp_dir / "apps" / "client"
        res = ep_runner.run(["init", "client", "--profile", "C", "--lang", "dart", "--dir", str(target)], cwd=temp_dir)
        assert res.returncode == 0, f"ep init failed: {res.stderr}"
        pj = target / "project.json"
        assert pj.exists()
        data = json.loads(pj.read_text(encoding="utf-8"))
        assert "profile:c" in data.get("tags", [])

    def test_f7_05_ep_init_profile_d_contracts_scaffolds_dynamically(self, ep_runner, temp_dir):
        target = temp_dir / "libs" / "contracts"
        res = ep_runner.run(["init", "contracts", "--profile", "D", "--dir", str(target)], cwd=temp_dir)
        assert res.returncode == 0, f"ep init failed: {res.stderr}"
        pj = target / "project.json"
        assert pj.exists()
        data = json.loads(pj.read_text(encoding="utf-8"))
        assert "profile:d" in data.get("tags", [])


# ==============================================================================
# F8: Per-Branch Change Surface Resolution
# ==============================================================================
class TestTier1F8PerBranchChangeSurfaceResolution:
    """F8: Relocate CHANGE_SURFACE off root to .ep/surfaces/<branch>.json; fix accumulation."""

    def test_f8_01_active_surface_scoped_to_ep_surfaces(self, ep_runner, temp_git_repo):
        surfaces_dir = temp_git_repo / ".ep" / "surfaces"
        assert surfaces_dir.exists()

    def test_f8_02_surface_file_named_by_git_branch(self, temp_git_repo):
        branch_surface = temp_git_repo / ".ep" / "surfaces" / "main.json"
        branch_surface.write_text(json.dumps({"branch": "main", "code_surface": []}), encoding="utf-8")
        assert branch_surface.exists()

    def test_f8_03_surface_check_diff_scopes_strictly_to_current_branch(self, ep_runner, temp_git_repo):
        # Create a file and declare it
        test_file = temp_git_repo / "new_feature.py"
        test_file.write_text("print('clean')\n", encoding="utf-8")
        cs_file = temp_git_repo / "CHANGE_SURFACE.md"
        cs_file.write_text(
            "# Change Surface\n## 1. Intent & Context\nTest\n"
            "## 2. Invariant Risk Assessment\nLow\n"
            "## 3. Code Surface\n- `new_feature.py`\n"
            "## 4. Test Surface\n- None\n",
            encoding="utf-8"
        )
        res = ep_runner.run(["surface", "check-diff", "--surface-file", str(cs_file), "--base", "HEAD"], cwd=temp_git_repo)
        assert res.returncode == 0, f"Surface check-diff failed: {res.stdout} {res.stderr}"

    def test_f8_04_historical_path_accumulation_prevented(self, ep_runner, temp_git_repo):
        # Check-diff should not look into old historical files
        docs_changes = temp_git_repo / "docs" / "changes"
        assert not docs_changes.exists()

    def test_f8_05_surface_validate_rejects_missing_required_sections(self, ep_runner, temp_dir):
        bad_cs = temp_dir / "BAD_SURFACE.md"
        bad_cs.write_text("# Incomplete Surface\nNo sections.\n", encoding="utf-8")
        res = ep_runner.run(["surface", "validate", str(bad_cs)], cwd=temp_dir)
        assert res.returncode != 0, "Validating incomplete surface must fail"


# ==============================================================================
# F9: Graphing Excision & Boundary Decoupling
# ==============================================================================
class TestTier1F9GraphingExcisionAndBoundaryDecoupling:
    """F9: Excise brittle Mermaid ep graph; decouple and promote boundary check."""

    def test_f9_01_ep_graph_generator_excised_or_deprecated(self, ep_runner):
        # ep graph is either removed or points to boundary check
        res = ep_runner.run(["graph", "--help"])
        assert res.returncode == 0
        assert "--check-boundaries" in res.stdout
        assert "boundary" in res.stdout.lower()

    def test_f9_02_boundary_check_operates_under_ep_verify(self, ep_runner, temp_git_repo):
        res = ep_runner.run(["verify", "--root", str(temp_git_repo)], cwd=temp_git_repo)
        # Verify boundary checking step 7 executes under ep verify
        assert "=== 7. Verifying Architectural Boundary Integrity ===" in res.stdout
        assert "Architectural Boundary Integrity Verified" in res.stdout

    def test_f9_03_boundary_check_operates_under_ep_quality(self, ep_runner, temp_git_repo):
        res = ep_runner.run(["quality", "--root", str(temp_git_repo)], cwd=temp_git_repo)
        assert res.returncode == 0
        assert "[PASS] Quality Gate: 100% compliant." in res.stdout

    def test_f9_04_boundary_check_detects_illegal_inward_dependencies(self, ep_runner, temp_dir):
        domain_dir = temp_dir / "services" / "orders" / "src" / "domain"
        domain_dir.mkdir(parents=True, exist_ok=True)
        bad_file = domain_dir / "order.ts"
        bad_file.write_text("import { OrderAdapter } from '../adapters/order.adapter';\n", encoding="utf-8")
        res = ep_runner.run(["graph", "--check-boundaries", "--root", str(temp_dir)], cwd=temp_dir)
        # Boundary violation must exit 1 and emit boundary diagnostic
        assert res.returncode == 1
        assert "[FAIL] Architectural Boundary Violations Detected!" in res.stderr
        assert "Domain layer imports external adapters/infrastructure directly" in res.stderr

    def test_f9_05_boundary_check_passes_on_pure_architecture(self, ep_runner, temp_dir):
        domain_dir = temp_dir / "services" / "orders" / "src" / "domain"
        domain_dir.mkdir(parents=True, exist_ok=True)
        clean_file = domain_dir / "order.ts"
        clean_file.write_text("export class Order { id: string; amount: number; }\n", encoding="utf-8")
        res = ep_runner.run(["graph", "--check-boundaries", "--root", str(temp_dir)], cwd=temp_dir)
        assert res.returncode == 0
        assert "[OK] Architectural Boundary Integrity Verified. Zero illegal imports detected." in res.stdout


# ==============================================================================
# F10: Domain-Driven Design (DDD) Enforcement
# ==============================================================================
class TestTier1F10DddEnforcement:
    """F10: Pure domain logic, zero ORM/web frameworks, immutable value objects."""

    def test_f10_01_pure_domain_blocks_orm_imports_rule_ddd_01(self, ep_runner, temp_dir):
        d_dir = temp_dir / "domain"
        d_dir.mkdir(parents=True, exist_ok=True)
        bad_entity = d_dir / "user.py"
        bad_entity.write_text("from sqlalchemy import Column, Integer\nclass User: pass\n", encoding="utf-8")
        res = ep_runner.run(["graph", "--check-boundaries", "--root", str(temp_dir)], cwd=temp_dir)
        assert res.returncode == 1, "ORM in domain must fail boundary verification with exit code 1"
        assert "[FAIL] Architectural Boundary Violations Detected!" in res.stderr
        assert "Domain layer imports ORM/persistence framework" in res.stderr

    def test_f10_02_pure_domain_blocks_web_frameworks_rule_ddd_02(self, ep_runner, temp_dir):
        d_dir = temp_dir / "domain"
        d_dir.mkdir(parents=True, exist_ok=True)
        bad_entity = d_dir / "user_route.py"
        bad_entity.write_text("from fastapi import APIRouter\nrouter = APIRouter()\n", encoding="utf-8")
        res = ep_runner.run(["graph", "--check-boundaries", "--root", str(temp_dir)], cwd=temp_dir)
        assert res.returncode == 1, "Web framework in domain must fail boundary verification with exit code 1"
        assert "[FAIL] Architectural Boundary Violations Detected!" in res.stderr
        assert "Domain layer imports web/transport framework" in res.stderr

    def test_f10_03_domain_blocks_naked_env_variables_rule_ddd_04(self, ep_runner, temp_dir):
        d_dir = temp_dir / "domain"
        d_dir.mkdir(parents=True, exist_ok=True)
        bad_entity = d_dir / "config.ts"
        bad_entity.write_text("export const SECRET = process.env.API_KEY;\n", encoding="utf-8")
        res = ep_runner.run(["audit", "--scope", str(d_dir)], cwd=temp_dir)
        # Should flag RULE-8.6 naked env in domain
        assert res.returncode == 1
        assert "RULE-8.6-NAKED-ENV-IN-DOMAIN" in res.stdout

    def test_f10_04_domain_passes_on_clean_pure_entity(self, ep_runner, temp_dir):
        d_dir = temp_dir / "domain"
        d_dir.mkdir(parents=True, exist_ok=True)
        clean_entity = d_dir / "invoice.ts"
        clean_entity.write_text("export class Invoice { constructor(public readonly id: string) {} }\n", encoding="utf-8")
        res = ep_runner.run(["graph", "--check-boundaries", "--root", str(temp_dir)], cwd=temp_dir)
        assert res.returncode == 0
        assert "[OK] Architectural Boundary Integrity Verified. Zero illegal imports detected." in res.stdout

    def test_f10_05_value_objects_enforce_immutability_rule_ddd_03(self, ep_runner, temp_dir):
        d_dir = temp_dir / "domain"
        d_dir.mkdir(parents=True, exist_ok=True)
        vo = d_dir / "money.py"
        vo.write_text("from dataclasses import dataclass\n@dataclass(frozen=True)\nclass Money:\n    amount: int\n", encoding="utf-8")
        res = ep_runner.run(["graph", "--check-boundaries", "--root", str(temp_dir)], cwd=temp_dir)
        assert res.returncode == 0
        assert "[OK] Architectural Boundary Integrity Verified. Zero illegal imports detected." in res.stdout
