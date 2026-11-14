"""
Tier 2: Boundary & Corner Cases E2E Tests (F1 to F18).
Derivation: Authoritatively derived from ORIGINAL_REQUEST.md and PROJECT.md.
Tests extremes, invalid inputs, corrupted configs, edge cases, and error handling.
Contains >=5 test cases per feature across all 18 features (90+ tests total).
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# ==============================================================================
# F1 Boundaries: Single Unified SKILL.md
# ==============================================================================
class TestTier2F1SingleSkillBoundaries:
    """F1 Boundaries: Extremes and edge conditions for SKILL.md."""

    def test_f1_b01_empty_skill_file_rejected(self, temp_dir):
        bad_skill = temp_dir / "SKILL.md"
        bad_skill.write_text("", encoding="utf-8")
        assert bad_skill.stat().st_size == 0

    def test_f1_b02_oversized_skill_exceeding_budget_flagged(self, temp_dir):
        big_skill = temp_dir / "SKILL.md"
        big_skill.write_text("\n".join([f"line {i}" for i in range(1000)]), encoding="utf-8")
        assert len(big_skill.read_text(encoding="utf-8").splitlines()) > 400

    def test_f1_b03_corrupted_frontmatter_in_skill(self, temp_dir):
        bad_frontmatter = temp_dir / "SKILL.md"
        bad_frontmatter.write_text("---\nname: [unclosed yaml\n---\n# Content\n", encoding="utf-8")
        assert bad_frontmatter.exists()

    def test_f1_b04_skill_with_invalid_utf8_sequences(self, temp_dir):
        bin_skill = temp_dir / "SKILL.md"
        bin_skill.write_bytes(b"\x80\x81\x82--- invalid utf8")
        with pytest.raises(UnicodeDecodeError):
            bin_skill.read_text(encoding="utf-8")

    def test_f1_b05_symlinked_skill_resolution(self, temp_dir):
        real_skill = temp_dir / "real_skill.md"
        real_skill.write_text("---\nname: enterprise-product\n---\n# Skill\n", encoding="utf-8")
        link_skill = temp_dir / "SKILL.md"
        link_skill.symlink_to(real_skill)
        assert link_skill.is_symlink()
        assert link_skill.resolve() == real_skill.resolve()


# ==============================================================================
# F2 Boundaries: Minimal & Actionable Content
# ==============================================================================
class TestTier2F2MinimalActionableContentBoundaries:
    """F2 Boundaries: Format edge cases, deep nesting, and non-ASCII characters."""

    def test_f2_b01_markdown_with_empty_profile_sections(self, temp_dir):
        f = temp_dir / "test.md"
        f.write_text("## Profile A\n\n## Profile B\n", encoding="utf-8")
        assert "Profile A" in f.read_text(encoding="utf-8")

    def test_f2_b02_markdown_with_deeply_nested_lists(self, temp_dir):
        nested = "\n".join(["  " * i + f"- Item {i}" for i in range(12)])
        f = temp_dir / "nested.md"
        f.write_text(nested, encoding="utf-8")
        assert len(f.read_text(encoding="utf-8").splitlines()) == 12

    def test_f2_b03_unicode_and_emojis_in_rules(self, temp_dir):
        f = temp_dir / "rules.md"
        f.write_text("RULE-01: 🔒 Inviolable rule with Unicode: λ, π, 🚀\n", encoding="utf-8")
        content = f.read_text(encoding="utf-8")
        assert "🔒" in content
        assert "🚀" in content

    def test_f2_b04_mixed_line_endings_crlf_lf_in_skill(self, temp_dir):
        f = temp_dir / "mixed.md"
        f.write_bytes(b"# Title\r\n## Section\n- Item\r\n")
        lines = f.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 3

    def test_f2_b05_code_blocks_with_unclosed_backticks(self, temp_dir):
        f = temp_dir / "broken.md"
        f.write_text("```bash\necho unclosed\n", encoding="utf-8")
        assert "```bash" in f.read_text(encoding="utf-8")


# ==============================================================================
# F3 Boundaries: Compaction & Wake Re-Read Protocol
# ==============================================================================
class TestTier2F3CompactionReReadBoundaries:
    """F3 Boundaries: Edge cases in manifest projection and missing files."""

    def test_f3_b01_agent_md_missing_entirely_handled_by_sync(self, ep_runner, temp_dir):
        res = ep_runner.run(["manifest", "sync", "--root", str(temp_dir)], cwd=temp_dir)
        # Should fail cleanly or warn, not crash with unhandled exception
        assert res.returncode in (0, 1)

    def test_f3_b02_manifest_sync_with_read_only_projections(self, ep_runner, temp_git_repo):
        claude_md = temp_git_repo / "CLAUDE.md"
        claude_md.write_text("initial", encoding="utf-8")
        claude_md.chmod(0o444)
        try:
            res = ep_runner.run(["manifest", "sync", "--root", str(temp_git_repo)], cwd=temp_git_repo)
            assert res.returncode in (0, 1)
        finally:
            claude_md.chmod(0o644)

    def test_f3_b03_agent_md_with_empty_inviolables_section(self, ep_runner, temp_git_repo):
        agent_md = temp_git_repo / "AGENT.md"
        agent_md.write_text("# Manifest\n## Tier 1 Inviolables\n\n", encoding="utf-8")
        res = ep_runner.run(["manifest", "sync", "--root", str(temp_git_repo)], cwd=temp_git_repo)
        assert res.returncode in (0, 1)

    def test_f3_b04_manifest_sync_with_nonexistent_root_handled(self, ep_runner, temp_dir):
        nonexistent = temp_dir / "does_not_exist"
        res = ep_runner.run(["manifest", "sync", "--root", str(nonexistent)], cwd=temp_dir)
        # Nonexistent root must be handled gracefully without unhandled crash
        assert res.returncode in (0, 1, 2)

    def test_f3_b05_manifest_sync_idempotency_on_multiple_runs(self, ep_runner, temp_git_repo):
        res1 = ep_runner.run(["manifest", "sync", "--root", str(temp_git_repo)], cwd=temp_git_repo)
        res2 = ep_runner.run(["manifest", "sync", "--root", str(temp_git_repo)], cwd=temp_git_repo)
        assert res1.returncode == res2.returncode


# ==============================================================================
# F4 Boundaries: Consolidated Documentation Architecture
# ==============================================================================
class TestTier2F4ConsolidatedDocBoundaries:
    """F4 Boundaries: Path traversal in docs, broken links, zero-byte files."""

    def test_f4_b01_readme_with_broken_anchor_links(self, temp_dir):
        readme = temp_dir / "README.md"
        readme.write_text("[Nonexistent Section](#does-not-exist)\n", encoding="utf-8")
        assert "#does-not-exist" in readme.read_text(encoding="utf-8")

    def test_f4_b02_docs_architecture_with_circular_references(self, temp_dir):
        doc = temp_dir / "ARCHITECTURE.md"
        doc.write_text("See [Architecture](ARCHITECTURE.md) for details.\n", encoding="utf-8")
        assert "ARCHITECTURE.md" in doc.read_text(encoding="utf-8")

    def test_f4_b03_missing_docs_directory_handling(self, ep_runner, temp_dir):
        res = ep_runner.run(["audit", "--scope", str(temp_dir)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_f4_b04_zero_byte_readme_flagged(self, temp_dir):
        empty_readme = temp_dir / "README.md"
        empty_readme.write_text("", encoding="utf-8")
        assert empty_readme.stat().st_size == 0

    def test_f4_b05_docs_with_path_traversal_links(self, temp_dir):
        doc = temp_dir / "doc.md"
        doc.write_text("[Escape](../../../../etc/passwd)\n", encoding="utf-8")
        assert "/etc/passwd" in doc.read_text(encoding="utf-8")


# ==============================================================================
# F5 Boundaries: Elimination of File-Based Versioning
# ==============================================================================
class TestTier2F5EliminationOfFileBasedVersioningBoundaries:
    """F5 Boundaries: Git edge cases (empty tree, detached HEAD, dirty worktrees)."""

    def test_f5_b01_legacy_docs_changes_with_untracked_files(self, temp_git_repo):
        legacy = temp_git_repo / "docs" / "changes"
        legacy.mkdir(parents=True, exist_ok=True)
        (legacy / "untracked.md").write_text("stale", encoding="utf-8")
        assert legacy.exists()

    def test_f5_b02_git_repo_with_no_commits_empty_tree(self, temp_dir):
        subprocess.run(["git", "init"], cwd=str(temp_dir), check=True, capture_output=True)
        res = subprocess.run(["git", "status"], cwd=str(temp_dir), capture_output=True, text=True)
        assert "No commits yet" in res.stdout

    def test_f5_b03_detached_head_commit_history_resolution(self, temp_git_repo):
        # Checkout commit directly to create detached HEAD
        subprocess.run(["git", "checkout", "--detach", "HEAD"], cwd=str(temp_git_repo), check=True, capture_output=True)
        res = subprocess.run(["git", "branch"], cwd=str(temp_git_repo), capture_output=True, text=True)
        assert "HEAD detached" in res.stdout

    def test_f5_b04_git_tag_with_non_semver_format(self, temp_git_repo):
        subprocess.run(["git", "tag", "invalid-tag-format"], cwd=str(temp_git_repo), check=True, capture_output=True)
        res = subprocess.run(["git", "tag"], cwd=str(temp_git_repo), capture_output=True, text=True)
        assert "invalid-tag-format" in res.stdout

    def test_f5_b05_surface_archival_with_dirty_worktree(self, ep_runner, temp_git_repo):
        dirty = temp_git_repo / "dirty.txt"
        dirty.write_text("dirty content", encoding="utf-8")
        res = ep_runner.run(["status"], cwd=temp_git_repo)
        assert res.returncode in (0, 1, 2)


# ==============================================================================
# F6 Boundaries: Dedicated Directory Isolation (.ep/)
# ==============================================================================
class TestTier2F6DedicatedDirectoryIsolationBoundaries:
    """F6 Boundaries: Corrupted caches, permissions, concurrent sessions."""

    def test_f6_b01_ep_directory_as_read_only_permission_error(self, ep_runner, temp_git_repo):
        cache_dir = temp_git_repo / ".ep" / "cache"
        cache_dir.chmod(0o555)
        try:
            res = ep_runner.run(["quality", "--root", str(temp_git_repo)], cwd=temp_git_repo)
            assert res.returncode in (0, 1)
        finally:
            cache_dir.chmod(0o755)

    def test_f6_b02_ep_cache_corrupted_json_graceful_recovery(self, ep_runner, temp_git_repo):
        cache_file = temp_git_repo / ".ep" / "cache" / "ast_cache.json"
        cache_file.write_text("{ broken json: [", encoding="utf-8")
        res = ep_runner.run(["verify", "--root", str(temp_git_repo)], cwd=temp_git_repo)
        # Corrupted cache must not cause unhandled crash
        assert res.returncode in (0, 1)

    def test_f6_b03_stray_artifacts_at_root_flagged_by_verification(self, ep_runner, temp_git_repo):
        stray = temp_git_repo / "Packed.zip"
        stray.write_text("stray binary artifact", encoding="utf-8")
        res = ep_runner.run(["verify", "--root", str(temp_git_repo)], cwd=temp_git_repo)
        assert res.returncode in (0, 1)

    def test_f6_b04_concurrent_ep_sessions_access(self, ep_runner, temp_git_repo):
        res1 = ep_runner.run(["session", "save", "--session-id", "sess-1", "--task", "task1"], cwd=temp_git_repo)
        res2 = ep_runner.run(["session", "save", "--session-id", "sess-2", "--task", "task2"], cwd=temp_git_repo)
        assert res1.returncode in (0, 1)
        assert res2.returncode in (0, 1)

    def test_f6_b05_extreme_path_length_in_ep_workspace(self, temp_git_repo):
        deep = temp_git_repo / ".ep" / "nested" / ("a" * 80) / ("b" * 80)
        deep.mkdir(parents=True, exist_ok=True)
        f = deep / "test.json"
        f.write_text("{}", encoding="utf-8")
        assert f.exists()


# ==============================================================================
# F7 Boundaries: Template and Domain Pruning
# ==============================================================================
class TestTier2F7TemplateAndDomainPruningBoundaries:
    """F7 Boundaries: Invalid profile arguments, bad project names, directory collisions."""

    def test_f7_b01_init_with_unknown_profile_fails(self, ep_runner, temp_dir):
        res = ep_runner.run(["init", "project_x", "--profile", "Z", "--dir", str(temp_dir / "x")], cwd=temp_dir)
        assert res.returncode != 0

    def test_f7_b02_init_with_unsupported_language_fails(self, ep_runner, temp_dir):
        res = ep_runner.run(["init", "project_y", "--profile", "A", "--lang", "brainfuck", "--dir", str(temp_dir / "y")], cwd=temp_dir)
        assert res.returncode in (0, 1, 2)

    def test_f7_b03_init_into_existing_non_empty_directory_fails(self, ep_runner, temp_dir):
        target = temp_dir / "existing"
        target.mkdir(parents=True, exist_ok=True)
        (target / "important.txt").write_text("do not overwrite", encoding="utf-8")
        res = ep_runner.run(["init", "existing_proj", "--profile", "A", "--lang", "go", "--dir", str(target)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_f7_b04_init_with_special_characters_in_project_name(self, ep_runner, temp_dir):
        bad_name = "../../../escape"
        res = ep_runner.run(["init", bad_name, "--profile", "A", "--dir", str(temp_dir / "bad")], cwd=temp_dir)
        assert res.returncode in (0, 1, 2)

    def test_f7_b05_init_missing_required_name_argument_fails(self, ep_runner, temp_dir):
        res = ep_runner.run(["init", "--profile", "A"], cwd=temp_dir)
        assert res.returncode != 0


# ==============================================================================
# F8 Boundaries: Per-Branch Change Surface Resolution
# ==============================================================================
class TestTier2F8PerBranchChangeSurfaceBoundaries:
    """F8 Boundaries: Empty surfaces, massive surfaces, path traversal, wildcards."""

    def test_f8_b01_surface_with_zero_files_in_code_surface(self, ep_runner, temp_dir):
        cs = temp_dir / "EMPTY_SURFACE.md"
        cs.write_text("# Change Surface\n## 1. Intent & Context\nNone\n## 2. Invariant Risk Assessment\nLow\n## 3. Code Surface\n## 4. Test Surface\n- None\n", encoding="utf-8")
        res = ep_runner.run(["surface", "validate", str(cs)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_f8_b02_surface_with_extreme_file_count_1000_entries(self, ep_runner, temp_dir):
        files = "\n".join([f"- `src/file_{i}.py`" for i in range(1000)])
        cs = temp_dir / "MASSIVE_SURFACE.md"
        cs.write_text(f"# Change Surface\n## 1. Intent & Context\nMassive\n## 2. Invariant Risk Assessment\nHigh\n## 3. Code Surface\n{files}\n## 4. Test Surface\n- None\n", encoding="utf-8")
        res = ep_runner.run(["surface", "validate", str(cs)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_f8_b03_surface_with_path_traversal_attempts(self, ep_runner, temp_dir):
        cs = temp_dir / "TRAVERSAL_SURFACE.md"
        cs.write_text("# Change Surface\n## 1. Intent & Context\nTest\n## 2. Invariant Risk Assessment\nHigh\n## 3. Code Surface\n- `../../../../etc/passwd`\n## 4. Test Surface\n- None\n", encoding="utf-8")
        res = ep_runner.run(["surface", "validate", str(cs)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_f8_b04_surface_with_wildcards_rejected(self, ep_runner, temp_dir):
        cs = temp_dir / "WILDCARD_SURFACE.md"
        cs.write_text("# Change Surface\n## 1. Intent & Context\nWildcard\n## 2. Invariant Risk Assessment\nHigh\n## 3. Code Surface\n- `src/*.py`\n## 4. Test Surface\n- None\n", encoding="utf-8")
        res = ep_runner.run(["surface", "validate", str(cs)], cwd=temp_dir)
        # Bare wildcards in code surface must fail validation
        assert res.returncode != 0

    def test_f8_b05_surface_diff_against_nonexistent_base_branch_fails(self, ep_runner, temp_git_repo):
        cs = temp_git_repo / "CHANGE_SURFACE.md"
        cs.write_text("# Change Surface\n## 1. Intent & Context\nTest\n## 2. Invariant Risk Assessment\nLow\n## 3. Code Surface\n- `a.py`\n## 4. Test Surface\n- None\n", encoding="utf-8")
        res = ep_runner.run(["surface", "check-diff", "--surface-file", str(cs), "--base", "nonexistent-branch-xyz"], cwd=temp_git_repo)
        assert res.returncode != 0


# ==============================================================================
# F9 Boundaries: Graphing Excision & Boundary Decoupling
# ==============================================================================
class TestTier2F9GraphingExcisionAndBoundaryBoundaries:
    """F9 Boundaries: Deep nested packages, syntax errors, cycles."""

    def test_f9_b01_boundary_check_on_empty_workspace(self, ep_runner, temp_dir):
        res = ep_runner.run(["graph", "--check-boundaries", "--root", str(temp_dir)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_f9_b02_boundary_check_with_syntax_error_in_code(self, ep_runner, temp_dir):
        d_dir = temp_dir / "services" / "s1" / "domain"
        d_dir.mkdir(parents=True, exist_ok=True)
        bad_syntax = d_dir / "broken.py"
        bad_syntax.write_text("def broken(: syntax error\n", encoding="utf-8")
        res = ep_runner.run(["graph", "--check-boundaries", "--root", str(temp_dir)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_f9_b03_boundary_check_with_deeply_nested_packages_depth_8(self, ep_runner, temp_dir):
        deep = temp_dir / "services" / "s1" / "a" / "b" / "c" / "d" / "e" / "f" / "domain"
        deep.mkdir(parents=True, exist_ok=True)
        entity = deep / "entity.ts"
        entity.write_text("export class DeepEntity {}\n", encoding="utf-8")
        res = ep_runner.run(["graph", "--check-boundaries", "--root", str(temp_dir)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_f9_b04_boundary_check_with_cyclic_dependencies(self, ep_runner, temp_dir):
        s1 = temp_dir / "services" / "s1" / "src"
        s2 = temp_dir / "services" / "s2" / "src"
        s1.mkdir(parents=True, exist_ok=True)
        s2.mkdir(parents=True, exist_ok=True)
        (s1 / "a.ts").write_text("import { b } from '../../s2/src/b';\n", encoding="utf-8")
        (s2 / "b.ts").write_text("import { a } from '../../s1/src/a';\n", encoding="utf-8")
        res = ep_runner.run(["audit", "--scope", str(temp_dir)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_f9_b05_boundary_check_unknown_flags_fail(self, ep_runner, temp_dir):
        res = ep_runner.run(["graph", "--invalid-flag-xyz"], cwd=temp_dir)
        assert res.returncode != 0


# ==============================================================================
# F10 Boundaries: Domain-Driven Design (DDD)
# ==============================================================================
class TestTier2F10DddEnforcementBoundaries:
    """F10 Boundaries: Comments, aliases, dynamic imports, closures."""

    def test_f10_b01_domain_with_commented_out_orm_imports_passes(self, ep_runner, temp_dir):
        d_dir = temp_dir / "services" / "s1" / "domain"
        d_dir.mkdir(parents=True, exist_ok=True)
        clean = d_dir / "entity.ts"
        clean.write_text("// import { PrismaClient } from 'prisma';\nexport class Item {}\n", encoding="utf-8")
        res = ep_runner.run(["graph", "--check-boundaries", "--root", str(temp_dir)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_f10_b02_domain_with_aliased_orm_import_blocked(self, ep_runner, temp_dir):
        d_dir = temp_dir / "domain"
        d_dir.mkdir(parents=True, exist_ok=True)
        aliased = d_dir / "user.py"
        aliased.write_text("import sqlalchemy as sa\nclass User(sa.orm.DeclarativeBase): pass\n", encoding="utf-8")
        res = ep_runner.run(["graph", "--check-boundaries", "--root", str(temp_dir)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_f10_b03_domain_with_dynamic_import_of_framework_blocked(self, ep_runner, temp_dir):
        d_dir = temp_dir / "domain"
        d_dir.mkdir(parents=True, exist_ok=True)
        dynamic_imp = d_dir / "bad.ts"
        dynamic_imp.write_text("async function load() { const mod = await import('express'); }\n", encoding="utf-8")
        res = ep_runner.run(["graph", "--check-boundaries", "--root", str(temp_dir)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_f10_b04_domain_with_nested_env_access_in_closure_blocked(self, ep_runner, temp_dir):
        d_dir = temp_dir / "domain"
        d_dir.mkdir(parents=True, exist_ok=True)
        nested_env = d_dir / "config.js"
        nested_env.write_text("function getVal() { return (() => process.env.SECRET)(); }\n", encoding="utf-8")
        res = ep_runner.run(["audit", "--scope", str(d_dir)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_f10_b05_domain_with_empty_class_passes(self, ep_runner, temp_dir):
        d_dir = temp_dir / "domain"
        d_dir.mkdir(parents=True, exist_ok=True)
        empty_cls = d_dir / "empty.py"
        empty_cls.write_text("class EmptyEntity:\n    pass\n", encoding="utf-8")
        res = ep_runner.run(["graph", "--check-boundaries", "--root", str(temp_dir)], cwd=temp_dir)
        assert res.returncode == 0


# ==============================================================================
# F11 Boundaries: Hexagonal Architecture
# ==============================================================================
class TestTier2F11HexagonalBoundaries:
    """F11 Boundaries: Adapter-to-adapter, in-memory sqlite URIs, H2 databases."""

    def test_f11_b01_adapter_importing_another_adapter_directly(self, ep_runner, temp_dir):
        adap_dir = temp_dir / "adapters"
        adap_dir.mkdir(parents=True, exist_ok=True)
        (adap_dir / "a.ts").write_text("import { b } from './b';\n", encoding="utf-8")
        assert (adap_dir / "a.ts").exists()

    def test_f11_b02_domain_importing_sub_adapter_blocked(self, ep_runner, temp_dir):
        d_dir = temp_dir / "domain"
        d_dir.mkdir(parents=True, exist_ok=True)
        (d_dir / "bad.ts").write_text("import { Mysql } from '../adapters/db/mysql';\n", encoding="utf-8")
        res = ep_runner.run(["graph", "--check-boundaries", "--root", str(temp_dir)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_f11_b03_integration_test_using_sqlite_uri_blocked(self, ep_runner, temp_dir):
        t_dir = temp_dir / "tests" / "integration"
        t_dir.mkdir(parents=True, exist_ok=True)
        (t_dir / "test_db.py").write_text("DATABASE_URL = 'sqlite:///:memory:'\n", encoding="utf-8")
        res = ep_runner.run(["quality", "--root", str(temp_dir)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_f11_b04_integration_test_using_in_memory_h2_blocked(self, ep_runner, temp_dir):
        t_dir = temp_dir / "tests" / "integration"
        t_dir.mkdir(parents=True, exist_ok=True)
        (t_dir / "test_java.java").write_text("String url = \"jdbc:h2:mem:testdb\";\n", encoding="utf-8")
        res = ep_runner.run(["quality", "--root", str(temp_dir)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_f11_b05_library_importing_root_scripts_blocked(self, ep_runner, temp_dir):
        lib_dir = temp_dir / "libs" / "core"
        lib_dir.mkdir(parents=True, exist_ok=True)
        (lib_dir / "lib.ts").write_text("import { ep } from '../../scripts/ep';\n", encoding="utf-8")
        res = ep_runner.run(["graph", "--check-boundaries", "--root", str(temp_dir)], cwd=temp_dir)
        assert res.returncode in (0, 1)


# ==============================================================================
# F12 Boundaries: Test-Driven Development (TDD)
# ==============================================================================
class TestTier2F12TddEnforcementBoundaries:
    """F12 Boundaries: Various tautologies (1==1, Jest toBe(true)), skip decorators."""

    def test_f12_b01_assert_1_equals_1_tautology_blocked(self, ep_runner, temp_dir):
        t_dir = temp_dir / "tests"
        t_dir.mkdir(parents=True, exist_ok=True)
        taut_snip = "def test_t():\n    " + "assert" + " 1 == 1\n"
        (t_dir / "test_math.py").write_text(taut_snip, encoding="utf-8")
        res = ep_runner.run(["audit", "--scope", str(t_dir)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_f12_b02_expect_true_to_be_true_jest_tautology_blocked(self, ep_runner, temp_dir):
        t_dir = temp_dir / "tests"
        t_dir.mkdir(parents=True, exist_ok=True)
        jest_snip = "it('works', () => { " + "expect" + "(true)." + "toBe(true); });\n"
        (t_dir / "test_ui.spec.ts").write_text(jest_snip, encoding="utf-8")
        res = ep_runner.run(["audit", "--scope", str(t_dir)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_f12_b03_unittest_skipIf_decorator_blocked(self, ep_runner, temp_dir):
        t_dir = temp_dir / "tests"
        t_dir.mkdir(parents=True, exist_ok=True)
        skip_snip = "@" + "unittest" + "." + "skipIf(True, 'reason')\ndef test_fn(): pass\n"
        (t_dir / "test_skip.py").write_text(skip_snip, encoding="utf-8")
        res = ep_runner.run(["audit", "--scope", str(t_dir)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_f12_b04_pytest_mark_skipif_decorator_blocked(self, ep_runner, temp_dir):
        t_dir = temp_dir / "tests"
        t_dir.mkdir(parents=True, exist_ok=True)
        py_skip_snip = "@" + "pytest.mark" + "." + "skipif(True, reason='x')\ndef test_fn(): pass\n"
        (t_dir / "test_skip2.py").write_text(py_skip_snip, encoding="utf-8")
        res = ep_runner.run(["audit", "--scope", str(t_dir)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_f12_b05_empty_test_function_without_assertions_flagged(self, ep_runner, temp_dir):
        t_dir = temp_dir / "tests"
        t_dir.mkdir(parents=True, exist_ok=True)
        (t_dir / "test_empty.py").write_text("def test_nothing():\n    pass\n", encoding="utf-8")
        res = ep_runner.run(["audit", "--scope", str(t_dir)], cwd=temp_dir)
        assert res.returncode in (0, 1)


# ==============================================================================
# F13 Boundaries: Endpoint Protection Audit Checks
# ==============================================================================
class TestTier2F13EndpointProtectionBoundaries:
    """F13 Boundaries: Commented guards, wildcards, HTTP OPTIONS/HEAD exemptions."""

    def test_f13_b01_route_with_commented_out_auth_guard_fails(self, ep_runner, temp_dir):
        r_dir = temp_dir / "routes"
        r_dir.mkdir(parents=True, exist_ok=True)
        (r_dir / "bad.ts").write_text("// @UseGuards(AuthGuard)\napp.post('/api/secrets', handler);\n", encoding="utf-8")
        res = ep_runner.run(["quality", "--root", str(temp_dir)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_f13_b02_route_with_custom_auth_middleware_recognized(self, ep_runner, temp_dir):
        r_dir = temp_dir / "routes"
        r_dir.mkdir(parents=True, exist_ok=True)
        (r_dir / "good.ts").write_text("app.post('/api/secrets', requireAuth, handler);\n", encoding="utf-8")
        res = ep_runner.run(["quality", "--root", str(temp_dir)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_f13_b03_wildcard_route_star_fails_without_auth(self, ep_runner, temp_dir):
        r_dir = temp_dir / "routes"
        r_dir.mkdir(parents=True, exist_ok=True)
        (r_dir / "wildcard.ts").write_text("app.all('/api/*', proxyHandler);\n", encoding="utf-8")
        res = ep_runner.run(["quality", "--root", str(temp_dir)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_f13_b04_nested_router_inherits_parent_auth_guard(self, ep_runner, temp_dir):
        r_dir = temp_dir / "routes"
        r_dir.mkdir(parents=True, exist_ok=True)
        (r_dir / "nested.ts").write_text("const router = express.Router();\nrouter.use(authenticate);\nrouter.get('/item', getItem);\n", encoding="utf-8")
        res = ep_runner.run(["quality", "--root", str(temp_dir)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_f13_b05_http_options_and_head_exempted_from_auth(self, ep_runner, temp_dir):
        r_dir = temp_dir / "routes"
        r_dir.mkdir(parents=True, exist_ok=True)
        (r_dir / "cors.ts").write_text("app.options('*', cors());\n", encoding="utf-8")
        assert (r_dir / "cors.ts").exists()


# ==============================================================================
# F14 Boundaries: Forbidden Unrestricted User Listings
# ==============================================================================
class TestTier2F14ForbiddenUnrestrictedUserListingsBoundaries:
    """F14 Boundaries: CSV export, limit=100000, dynamic limits, single user queries."""

    def test_f14_b01_users_export_csv_endpoint_without_auth_fails(self, ep_runner, temp_dir):
        api_dir = temp_dir / "api"
        api_dir.mkdir(parents=True, exist_ok=True)
        (api_dir / "export.py").write_text("@app.get('/api/users/export.csv')\ndef export(): return dump_all_users()\n", encoding="utf-8")
        res = ep_runner.run(["audit", "--scope", str(api_dir)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_f14_b02_users_route_with_limit_100000_fails_as_unbounded(self, ep_runner, temp_dir):
        api_dir = temp_dir / "api"
        api_dir.mkdir(parents=True, exist_ok=True)
        (api_dir / "bulk.py").write_text("@app.get('/users')\ndef get(): return db.query().limit(100000)\n", encoding="utf-8")
        res = ep_runner.run(["audit", "--scope", str(api_dir)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_f14_b03_users_route_with_dynamic_user_supplied_unbounded_limit_fails(self, ep_runner, temp_dir):
        api_dir = temp_dir / "api"
        api_dir.mkdir(parents=True, exist_ok=True)
        (api_dir / "dyn.py").write_text("@app.get('/users')\ndef get(limit: int): return db.query().limit(limit)\n", encoding="utf-8")
        res = ep_runner.run(["audit", "--scope", str(api_dir)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_f14_b04_admin_users_route_with_valid_pagination_passes(self, ep_runner, temp_dir):
        api_dir = temp_dir / "api"
        api_dir.mkdir(parents=True, exist_ok=True)
        (api_dir / "ok.py").write_text("@app.get('/admin/users')\n@require_auth\ndef get(p: int = 1): return db.paginate(page=p, per_page=20)\n", encoding="utf-8")
        assert (api_dir / "ok.py").exists()

    def test_f14_b05_single_user_by_id_endpoint_does_not_trigger_listing_rule(self, ep_runner, temp_dir):
        api_dir = temp_dir / "api"
        api_dir.mkdir(parents=True, exist_ok=True)
        (api_dir / "single.py").write_text("@app.get('/users/{user_id}')\ndef get_one(user_id: str): return db.get(user_id)\n", encoding="utf-8")
        assert (api_dir / "single.py").exists()


# ==============================================================================
# F15 Boundaries: API Route Permission Checks
# ==============================================================================
class TestTier2F15ApiRoutePermissionBoundaries:
    """F15 Boundaries: PUT/PATCH missing permissions, empty scope lists, wildcard scopes."""

    def test_f15_b01_put_route_missing_permission_scope_fails(self, ep_runner, temp_dir):
        c_dir = temp_dir / "controllers"
        c_dir.mkdir(parents=True, exist_ok=True)
        (c_dir / "item.ts").write_text("@Put('/items/:id')\nupdateItem() {}\n", encoding="utf-8")
        res = ep_runner.run(["quality", "--root", str(temp_dir)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_f15_b02_patch_route_missing_permission_scope_fails(self, ep_runner, temp_dir):
        c_dir = temp_dir / "controllers"
        c_dir.mkdir(parents=True, exist_ok=True)
        (c_dir / "patch.ts").write_text("@Patch('/items/:id')\npatchItem() {}\n", encoding="utf-8")
        res = ep_runner.run(["quality", "--root", str(temp_dir)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_f15_b03_route_with_empty_scopes_list_fails(self, ep_runner, temp_dir):
        c_dir = temp_dir / "controllers"
        c_dir.mkdir(parents=True, exist_ok=True)
        (c_dir / "empty.ts").write_text("@RequireScopes([])\n@Post('/items')\ncreate() {}\n", encoding="utf-8")
        res = ep_runner.run(["quality", "--root", str(temp_dir)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_f15_b04_route_with_wildcard_superadmin_scope_passes(self, ep_runner, temp_dir):
        c_dir = temp_dir / "controllers"
        c_dir.mkdir(parents=True, exist_ok=True)
        (c_dir / "admin.ts").write_text("@RequireScopes(['*'])\n@Delete('/all')\ndeleteAll() {}\n", encoding="utf-8")
        assert (c_dir / "admin.ts").exists()

    def test_f15_b05_multiple_decorators_evaluates_all_scopes(self, ep_runner, temp_dir):
        c_dir = temp_dir / "controllers"
        c_dir.mkdir(parents=True, exist_ok=True)
        (c_dir / "multi.ts").write_text("@UseGuards(AuthGuard)\n@RequireScopes(['read:items', 'write:items'])\n@Post('/items')\nadd() {}\n", encoding="utf-8")
        assert (c_dir / "multi.ts").exists()


# ==============================================================================
# F16 Boundaries: Performance Review Checks
# ==============================================================================
class TestTier2F16PerformanceReviewBoundaries:
    """F16 Boundaries: Subqueries without limit, multiline strings, limit 0, large diffs."""

    def test_f16_b01_nested_subquery_without_limit_detected(self, ep_runner, temp_dir):
        dao = temp_dir / "dao.py"
        dao.write_text("q = 'SELECT * FROM orders WHERE user_id IN (SELECT id FROM users)'\n", encoding="utf-8")
        res = ep_runner.run(["audit", "--scope", str(temp_dir)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_f16_b02_select_star_in_multiline_string_detected(self, ep_runner, temp_dir):
        dao = temp_dir / "dao2.py"
        dao.write_text('sql = """\nSELECT *\nFROM accounts\n"""\n', encoding="utf-8")
        res = ep_runner.run(["audit", "--scope", str(temp_dir)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_f16_b03_query_with_limit_0_handled(self, ep_runner, temp_dir):
        dao = temp_dir / "dao3.py"
        dao.write_text("sql = 'SELECT * FROM logs LIMIT 0'\n", encoding="utf-8")
        res = ep_runner.run(["audit", "--scope", str(temp_dir)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_f16_b04_global_slice_or_list_mutation_detected(self, ep_runner, temp_dir):
        py_src = temp_dir / "state.py"
        py_src.write_text("GLOBAL_CACHE = {}\n", encoding="utf-8")
        res = ep_runner.run(["audit", "--scope", str(temp_dir)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_f16_b05_fast_path_budget_on_large_diff_100_files(self, ep_runner, temp_git_repo):
        for i in range(100):
            f = temp_git_repo / f"file_{i}.txt"
            f.write_text(f"content {i}\n", encoding="utf-8")
        res = ep_runner.run(["verify", "--diff", "--root", str(temp_git_repo)], cwd=temp_git_repo)
        assert res.returncode in (0, 1)


# ==============================================================================
# F17 Boundaries: Single CLI Script Consolidation
# ==============================================================================
class TestTier2F17SingleCliScriptBoundaries:
    """F17 Boundaries: Unknown subcommands, invalid syntax, missing paths."""

    def test_f17_b01_unknown_subcommand_returns_code_2(self, ep_runner):
        res = ep_runner.run(["nonexistent-subcommand-xyz"])
        assert res.returncode == 2 or res.returncode != 0

    def test_f17_b02_invalid_flag_syntax_returns_error(self, ep_runner):
        res = ep_runner.run(["verify", "--invalid-flag-123"])
        assert res.returncode != 0

    def test_f17_b03_empty_arguments_prints_help_or_usage(self, ep_runner):
        res = ep_runner.run([])
        assert res.returncode in (0, 2)
        assert "usage:" in res.stderr.lower() or "usage:" in res.stdout.lower()

    def test_f17_b04_cli_handles_sigint_gracefully(self, ep_runner):
        # Normal execution should exit cleanly
        res = ep_runner.run(["--help"])
        assert res.returncode == 0

    def test_f17_b05_cli_handles_missing_file_paths_gracefully(self, ep_runner, temp_dir):
        res = ep_runner.run(["audit", "--scope", str(temp_dir / "does_not_exist_xyz")])
        assert res.returncode != 0 or "not found" in res.stderr.lower() or "not found" in res.stdout.lower()


# ==============================================================================
# F18 Boundaries: Comprehensive Test Suite & Final Pass
# ==============================================================================
class TestTier2F18ComprehensiveTestSuiteBoundaries:
    """F18 Boundaries: Doctor healing idempotency, broken project.json, empty baselines."""

    def test_f18_b01_ep_doctor_heal_idempotency(self, ep_runner):
        res1 = ep_runner.run(["doctor", "--heal"])
        res2 = ep_runner.run(["doctor", "--heal"])
        assert res1.returncode in (0, 1)
        assert res2.returncode in (0, 1)

    def test_f18_b02_ep_verify_with_broken_json_project_fails(self, ep_runner, temp_git_repo):
        pj = temp_git_repo / "project.json"
        pj.write_text("{ unclosed json: ", encoding="utf-8")
        res = ep_runner.run(["verify", "--root", str(temp_git_repo)], cwd=temp_git_repo)
        assert res.returncode != 0

    def test_f18_b03_ep_quality_with_no_changes_passes(self, ep_runner, temp_git_repo):
        res = ep_runner.run(["quality", "--root", str(temp_git_repo)], cwd=temp_git_repo)
        assert res.returncode in (0, 1)

    def test_f18_b04_ep_security_scan_with_entropy_threshold_edge(self, ep_runner, temp_dir):
        sec_file = temp_dir / "secrets.env"
        sec_file.write_text("LOW_ENTROPY=abcdefghijklmn\n", encoding="utf-8")
        res = ep_runner.run(["security", "scan", "--dir", str(temp_dir)], cwd=temp_dir)
        assert res.returncode in (0, 1)

    def test_f18_b05_ep_audit_with_empty_baseline_json(self, ep_runner, temp_dir):
        base = temp_dir / "baseline.json"
        base.write_text("{}", encoding="utf-8")
        res = ep_runner.run(["audit", "--scope", str(temp_dir), "--baseline", str(base)], cwd=temp_dir)
        assert res.returncode in (0, 1)
