# Plugin Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make this repository installable as the Claude Code plugin `web-skills`, so anyone with Python 3.11+ and Node.js can build a site from any folder.

**Architecture:** The repository root becomes the plugin root and its own marketplace. A launcher `run.py` installs the Python packages and Node tools into a per-user cache on first use and then runs the requested script in-process. `lib/paths.py` finds the repository root by walking up, resolves `node_modules` and the project folder at call time, and the two `SKILL.md` files call every script through `${CLAUDE_PLUGIN_ROOT}/…/run.py`.

**Tech Stack:** Python 3.11+ standard library (`runpy`, `importlib`, `subprocess`, `hashlib`), pytest, Node.js/npm (`npm ci`), Claude Code plugin manifests, `claude plugin validate`.

**Spec:** `docs/superpowers/specs/2026-10-08-plugin-packaging-design.md`

## Global Constraints

- Python 3.11 or newer; Python dependencies only from `requirements.txt` (pyyaml, jsonschema, beautifulsoup4, tinycss2).
- `run.py` and `lib/deps.py` import only the standard library, `lib.paths`, and `lib.report`.
- House code style: file header and section banners in comments, a docstring with `I.S.` and `F.S.` on every function (nested ones too), comments in Indonesian, names in English, LF line endings.
- Every script ends its output with exactly one `NEXT:` line; exit codes `0` ok · `1` invalid input or missing tool · `2` check failed · `3` ask the user · `4` timeout.
- Plugin `name: web-skills`, `version: 0.1.0`, `license: MIT`, author `Rasyiq03`; marketplace `name: web-dev-skills`; repository `https://github.com/rasyiq03/web-dev-skills`.
- Project folder rule, in order: `PD_PROJECTS_DIR` → `REPO_ROOT/projects` when the current folder is `REPO_ROOT` → the current folder.
- Dependency cache: `PD_CACHE_DIR` → `%LOCALAPPDATA%\web-skills` on Windows → `$XDG_CACHE_HOME/web-skills` → `~/.cache/web-skills`; subfolders `py-<major.minor>-<hash12 of requirements.txt>` and `node-<hash12 of package-lock.json>`.
- Files in `config/` and `audit/` are not edited.
- Run tests with the repo venv: `.venv/Scripts/python.exe -m pytest` (Windows) from the repository root.

## Review Focus

- A first run on a machine without internet: `run.py` must stop with exit 1 and name the failed installer, and leave no half-filled cache folder (next run retries). Covered by `install_into` writing to a temporary folder; add the failing-installer test in Task 4.
- Linting from an installed plugin, where `node_modules` lives in the cache: ESLint and stylelint must still load their plugins. Covered by `lint_config` (Task 3) and the end-to-end test (Task 8).
- A user who opens Claude Code inside the plugin's own repository versus anywhere else: projects must land in `projects/` versus `<folder>/<slug>/`. Covered in Tasks 2 and 5.
- A second run after a successful install must not touch the network: covered by the "install once" tests in Task 4 (second call with `node`/`npm` removed from `PATH`).
- A script's own exit code (for example 1 from `validate_brief` on a missing project) must pass through `run.py` unchanged. Covered in Task 5.

---

## File Structure

| File | Responsibility |
| --- | --- |
| `.claude-plugin/plugin.json` (new) | Plugin manifest |
| `.claude-plugin/marketplace.json` (new) | This repo as a one-plugin marketplace |
| `LICENSE` (new) | MIT text |
| `README.md` (new) | Install and use instructions for other people |
| `package.json` | `setup` script becomes `npm ci` |
| `pytest.ini`, `tests/conftest.py` | `network` marker skipped unless `--network`; `run_script(..., cwd=)` |
| `skills/web-build/scripts/lib/paths.py` | `find_repo_root`, `node_modules_dir()`, new `projects_dir()` rule |
| `skills/web-build/scripts/lib/project.py` | Missing-project message names the absolute `brief.yaml` path |
| `skills/web-build/scripts/lib/node_tools.py` | Uses `node_modules_dir()`; new `lint_config(name)` |
| `skills/web-build/scripts/check.py` | ESLint/stylelint configs via `lint_config` |
| `skills/web-build/scripts/scaffold.py` | Chart.js from `node_modules_dir()` |
| `skills/web-build/scripts/lib/deps.py` (new) | Cache location, Python and Node dependency setup |
| `skills/web-build/scripts/run.py` (new) | Launcher: dependency setup, dispatch, `path` subcommand |
| `skills/web-build/SKILL.md`, `skills/web-design/SKILL.md` | Plugin paths, `<project>` folder |
| `tools/sync_adapters.py` | Codex only; warns about stale `.claude/skills/` copies |
| `AGENTS.md`, `IMPLEMENTATION.md` | Development flow and the new rules |
| `tests/test_plugin_manifest.py`, `test_paths.py`, `test_node_tools.py`, `test_deps.py`, `test_run.py`, `test_skill_text.py`, `test_plugin_e2e.py` (new) | Tests per task |
| `tests/test_sync_adapters.py` | Rewritten against a stand-in repo |

---

### Task 1: Plugin manifests, license, pinned setup script

**Files:**
- Create: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `LICENSE`
- Modify: `package.json` (`scripts.setup`)
- Test: `tests/test_plugin_manifest.py`

**Interfaces:**
- Produces: install command `/plugin install web-skills@web-dev-skills` (plugin name `web-skills`, marketplace name `web-dev-skills`), used by the README in Task 9.

- [ ] **Step 1: Write the failing tests**

`tests/test_plugin_manifest.py`:

```python
# ============================================================
# File      : test_plugin_manifest.py
# Deskripsi : Pengujian manifest plugin Claude Code dan marketplace:
#             lolos claude plugin validate --strict dan saling cocok.
# ============================================================

import json
import shutil
import subprocess

import pytest
from conftest import REPO

CLAUDE = shutil.which("claude")
MANIFEST_DIR = REPO / ".claude-plugin"

needs_claude = pytest.mark.skipif(CLAUDE is None, reason="Claude Code CLI tidak terpasang")


def validate(manifest):
    """
    Menjalankan claude plugin validate --strict --json pada satu manifest.

    I.S. : CLAUDE menunjuk CLI Claude Code.
    F.S. : (kode keluar, stdout) dikembalikan.
    """
    result = subprocess.run(
        [CLAUDE, "plugin", "validate", "--strict", "--json", str(manifest)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )

    return result.returncode, result.stdout


@needs_claude
def test_plugin_manifest_passes_strict_validation():
    code, out = validate(MANIFEST_DIR / "plugin.json")

    assert code == 0, out
    assert json.loads(out)["manifest"]["type"] == "plugin"


@needs_claude
def test_marketplace_manifest_passes_strict_validation():
    code, out = validate(MANIFEST_DIR / "marketplace.json")

    assert code == 0, out
    assert json.loads(out)["manifest"]["type"] == "marketplace"


def test_marketplace_installs_this_repository_as_the_plugin():
    plugin = json.loads((MANIFEST_DIR / "plugin.json").read_text(encoding="utf-8"))
    market = json.loads((MANIFEST_DIR / "marketplace.json").read_text(encoding="utf-8"))

    entries = [entry for entry in market["plugins"] if entry["name"] == plugin["name"]]

    assert market["name"] == "web-dev-skills"
    assert plugin["name"] == "web-skills"
    assert len(entries) == 1
    assert entries[0]["source"] == "./"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_plugin_manifest.py -v`
Expected: 3 FAIL (validator exit code non-zero for a missing file; `FileNotFoundError` for `plugin.json`).

- [ ] **Step 3: Create the manifests and the license**

`.claude-plugin/plugin.json`:

```json
{
  "name": "web-skills",
  "version": "0.1.0",
  "description": "Build a complete website from a short prompt (company profile, landing page, portfolio, small-business catalog, or dashboard), with every design decision recorded and every page checked.",
  "author": {
    "name": "Rasyiq03",
    "url": "https://github.com/rasyiq03"
  },
  "homepage": "https://github.com/rasyiq03/web-dev-skills",
  "repository": "https://github.com/rasyiq03/web-dev-skills",
  "license": "MIT",
  "keywords": ["website", "web-design", "landing-page", "dashboard", "indonesian"]
}
```

`.claude-plugin/marketplace.json`:

```json
{
  "name": "web-dev-skills",
  "description": "Marketplace for web-skills: prompt-to-website skills for Claude Code.",
  "owner": {
    "name": "Rasyiq03"
  },
  "plugins": [
    {
      "name": "web-skills",
      "source": "./",
      "description": "Build a complete website from a short prompt, with recorded design decisions and checked pages."
    }
  ]
}
```

`LICENSE`:

```text
MIT License

Copyright (c) 2026 Rasyiq03

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

In `package.json`, replace the `setup` value:

```json
		"setup": "npm ci"
```

(It previously ran `npm install -D prettier eslint …` without versions, which installs the latest releases over the pinned ones. This is a configuration line; it has no test.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_plugin_manifest.py -v`
Expected: 3 PASS. If `--strict` reports an unknown field (for example `author.url` on an older CLI), remove that field and rerun.

- [ ] **Step 5: Commit**

```bash
git add .claude-plugin LICENSE package.json tests/test_plugin_manifest.py
git commit -m "feat(plugin): add Claude Code plugin and marketplace manifests, MIT license"
```

---

### Task 2: Repository root, `node_modules`, and project folder in `lib/paths.py`

**Files:**
- Modify: `skills/web-build/scripts/lib/paths.py`, `skills/web-build/scripts/lib/project.py:30-32`, `skills/web-build/scripts/lib/node_tools.py:31,59`, `skills/web-build/scripts/scaffold.py:319`
- Test: `tests/test_paths.py`

**Interfaces:**
- Produces: `paths.find_repo_root(start: Path) -> Path` (raises `RuntimeError`), `paths.REPO_ROOT: Path`, `paths.node_modules_dir() -> Path` (replaces the removed constant `paths.NODE_MODULES`), `paths.projects_dir() -> Path`, `paths.project_dir(slug) -> Path`.

- [ ] **Step 1: Write the failing tests**

`tests/test_paths.py`:

```python
# ============================================================
# File      : test_paths.py
# Deskripsi : Pengujian lib/paths.py: pencarian akar repo, folder
#             node_modules, dan aturan folder proyek.
# ============================================================

import pytest
from conftest import REPO, next_line, run_script
from lib import paths


def make_repo_markers(root):
    """
    Membuat penanda akar repo (audit/ dan config/) di folder tiruan.

    I.S. : root adalah folder kosong.
    F.S. : root/audit/anti-slop.yaml dan root/config/eslint.config.js ada.
    """
    (root / "audit").mkdir(parents=True)
    (root / "audit" / "anti-slop.yaml").write_text("rules: []\n", encoding="utf-8")
    (root / "config").mkdir()
    (root / "config" / "eslint.config.js").write_text("export default [];\n", encoding="utf-8")


def test_find_repo_root_from_codex_copy(tmp_path):
    make_repo_markers(tmp_path)
    lib_dir = tmp_path / ".agents" / "skills" / "web-build" / "scripts" / "lib"
    lib_dir.mkdir(parents=True)

    assert paths.find_repo_root(lib_dir) == tmp_path.resolve()


def test_find_repo_root_without_markers_raises(tmp_path):
    with pytest.raises(RuntimeError):
        paths.find_repo_root(tmp_path)


def test_node_modules_dir_follows_env(monkeypatch, tmp_path):
    monkeypatch.setenv("PD_NODE_MODULES", str(tmp_path))

    assert paths.node_modules_dir() == tmp_path


def test_node_modules_dir_defaults_to_repo(monkeypatch):
    monkeypatch.delenv("PD_NODE_MODULES", raising=False)

    assert paths.node_modules_dir() == REPO / "node_modules"


def test_project_dir_is_in_working_folder_outside_repo(monkeypatch, tmp_path):
    monkeypatch.delenv("PD_PROJECTS_DIR", raising=False)
    monkeypatch.chdir(tmp_path)

    assert paths.project_dir("kopi-senja") == tmp_path.resolve() / "kopi-senja"


def test_project_dir_is_under_projects_in_repo(monkeypatch):
    # Sudah lolos sebelum perubahan; menjaga aturan mode pengembangan
    monkeypatch.delenv("PD_PROJECTS_DIR", raising=False)
    monkeypatch.chdir(REPO)

    assert paths.project_dir("kopi-senja") == REPO / "projects" / "kopi-senja"


def test_project_dir_env_wins_over_working_folder(monkeypatch, tmp_path):
    monkeypatch.setenv("PD_PROJECTS_DIR", str(tmp_path))
    monkeypatch.chdir(REPO)

    assert paths.project_dir("kopi-senja") == tmp_path / "kopi-senja"


def test_missing_project_names_absolute_brief_path(projects_dir):
    result = run_script("validate_brief", "belum-ada")

    assert result.returncode == 1
    assert next_line(result) == f"NEXT: write {projects_dir / 'belum-ada' / 'brief.yaml'} first"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_paths.py -v`
Expected: FAIL for `find_repo_root` (AttributeError), `node_modules_dir` (AttributeError), the working-folder test (returns `REPO/projects/...`), and the brief-path test (`NEXT: write projects/belum-ada/brief.yaml first`). `test_project_dir_is_under_projects_in_repo` and `test_project_dir_env_wins_over_working_folder` already pass.

- [ ] **Step 3: Implement**

In `lib/paths.py`, replace lines 20-34 (the `REPO_ROOT … NODE_MODULES` block) with:

```python
# ============================================================
# ========================= AKAR REPO ========================
# ============================================================


def find_repo_root(start):
    """
    Mencari akar repo atau plugin dengan naik dari folder start.

    I.S. : start adalah folder di dalam repo, folder plugin terpasang, atau salinan skill
           (misalnya .agents/skills/web-build/scripts/lib untuk Codex).
    F.S. : Folder induk pertama yang berisi audit/anti-slop.yaml dan config/eslint.config.js
           dikembalikan; RuntimeError bila tidak ada.
    """
    start = Path(start).resolve()

    for folder in (start, *start.parents):
        if (folder / "audit" / "anti-slop.yaml").is_file() and (folder / "config" / "eslint.config.js").is_file():
            return folder

    raise RuntimeError(f"Akar web-skills (audit/ dan config/) tidak ditemukan di atas {start}")


REPO_ROOT = find_repo_root(Path(__file__).parent)
SKILLS_DIR = REPO_ROOT / "skills"
BUILD_DIR = SKILLS_DIR / "web-build"
SCRIPTS_DIR = BUILD_DIR / "scripts"
DESIGN_DIR = SKILLS_DIR / "web-design"
SCHEMAS_DIR = BUILD_DIR / "schemas"
SITE_TYPES_DIR = BUILD_DIR / "site-types"
TEMPLATES_DIR = BUILD_DIR / "templates"
REFERENCES_DIR = BUILD_DIR / "references"
STYLES_DIR = DESIGN_DIR / "styles"
PATTERNS_FILE = DESIGN_DIR / "layouts" / "patterns.yaml"
AUDIT_DIR = REPO_ROOT / "audit"
CONFIG_DIR = REPO_ROOT / "config"
```

After `scripts_dir()`, add:

```python
def node_modules_dir():
    """
    Menentukan folder node_modules yang dipakai alat Node.

    I.S. : PD_NODE_MODULES boleh diatur (run.py mengisinya dengan folder cache).
    F.S. : Path PD_NODE_MODULES dikembalikan bila diatur, selain itu node_modules di akar repo.
           Dibaca setiap dipanggil karena run.py mengaturnya setelah modul ini diimpor.
    """
    override = os.environ.get("PD_NODE_MODULES")

    return Path(override) if override else REPO_ROOT / "node_modules"
```

Replace `projects_dir()` and the `F.S.` line of `project_dir()`:

```python
def projects_dir():
    """
    Menentukan folder induk semua proyek.

    I.S. : PD_PROJECTS_DIR boleh diatur; folder kerja saat ini menentukan sisanya.
    F.S. : Urutan: PD_PROJECTS_DIR; projects/ di akar repo bila folder kerja adalah akar repo
           (mode pengembangan); selain itu folder kerja itu sendiri, sehingga proyek ada di
           <folder>/<slug>/. Path belum tentu sudah ada.
    """
    override = os.environ.get("PD_PROJECTS_DIR")

    if override:
        return Path(override)

    cwd = Path.cwd().resolve()

    if cwd == REPO_ROOT:
        return REPO_ROOT / "projects"

    return cwd
```

```python
    F.S. : Path <folder induk proyek>/<slug>/ dikembalikan (lihat projects_dir).
```

In `lib/project.py` `open_project`, replace the missing-folder `fail` call:

```python
    if not project.is_dir():
        fail(EXIT_INVALID, f"Folder proyek tidak ada: {project}",
             f"write {project / 'brief.yaml'} first")
```

In `lib/node_tools.py`, replace both uses of `paths.NODE_MODULES` with `paths.node_modules_dir()`:

```python
    pkg_dir = paths.node_modules_dir() / package
```

```python
        reason = f"Paket {package} tidak ditemukan di {paths.node_modules_dir()}."
```

In `scaffold.py` line 319:

```python
        chart_vendor_src = paths.node_modules_dir() / "chart.js" / "dist" / "chart.umd.js"
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_paths.py -v` → all PASS.
Run: `.venv/Scripts/python.exe -m pytest -q` → all PASS (no other test reads `paths.NODE_MODULES`; `grep -rn NODE_MODULES skills tests tools` must print nothing).

- [ ] **Step 5: Commit**

```bash
git add skills/web-build/scripts/lib/paths.py skills/web-build/scripts/lib/project.py skills/web-build/scripts/lib/node_tools.py skills/web-build/scripts/scaffold.py tests/test_paths.py
git commit -m "feat(paths): find repo root by walking up, project folder follows the working folder"
```

---

### Task 3: Lint configs next to the `node_modules` in use

**Files:**
- Modify: `skills/web-build/scripts/lib/node_tools.py`, `skills/web-build/scripts/check.py` (`eslint_args`, `stylelint_args`)
- Test: `tests/test_node_tools.py`

**Interfaces:**
- Consumes: `paths.node_modules_dir()`, `paths.CONFIG_DIR` (Task 2).
- Produces: `node_tools.lint_config(name: str) -> Path`.

- [ ] **Step 1: Write the failing tests**

`tests/test_node_tools.py`:

```python
# ============================================================
# File      : test_node_tools.py
# Deskripsi : Pengujian lib/node_tools.lint_config: config linter selalu
#             berada di atas node_modules yang dipakai.
# ============================================================

from conftest import REPO
from lib import node_tools


def test_lint_config_uses_repo_config_with_repo_node_modules(monkeypatch):
    monkeypatch.delenv("PD_NODE_MODULES", raising=False)

    assert node_tools.lint_config("eslint.config.js") == REPO / "config" / "eslint.config.js"


def test_lint_config_copies_next_to_other_node_modules(monkeypatch, tmp_path):
    modules = tmp_path / "node-abc" / "node_modules"
    modules.mkdir(parents=True)
    monkeypatch.setenv("PD_NODE_MODULES", str(modules))

    config = node_tools.lint_config(".stylelintrc.json")

    assert config == tmp_path.resolve() / "node-abc" / "config" / ".stylelintrc.json"
    assert config.read_bytes() == (REPO / "config" / ".stylelintrc.json").read_bytes()
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_node_tools.py -v`
Expected: 2 FAIL with `AttributeError: module 'lib.node_tools' has no attribute 'lint_config'`.

- [ ] **Step 3: Implement**

In `lib/node_tools.py` add `import shutil` to the imports and this function after `run_tool`:

```python
def lint_config(name):
    """
    Menentukan file config linter yang impor plugin-nya bisa ditemukan.

    I.S. : name adalah nama file di config/, misalnya eslint.config.js.
    F.S. : config/<name> dikembalikan bila node_modules yang dipakai berada di salah satu
           induknya (mode pengembangan). Selain itu config disalin ke
           <node_modules>/../config/<name> dan path salinan itu dikembalikan, karena ESLint dan
           stylelint mencari plugin dari lokasi file config.
    """
    source = paths.CONFIG_DIR / name
    modules = paths.node_modules_dir().resolve()

    if modules.parent in source.resolve().parents:
        return source

    target = modules.parent / "config" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)

    return target
```

In `check.py`, replace the bodies (and the config sentence of the docstrings) of `eslint_args` and `stylelint_args`:

```python
def eslint_args():
    """
    Menyusun argumen ESLint bersama untuk mode perbaikan dan mode laporan.

    I.S. : -
    F.S. : List argumen dikembalikan. Config diambil lewat node_tools.lint_config agar impor
           plugin di eslint.config.js selalu ditemukan; salinan di proyek tetap dijaga oleh
           pemeriksaan integritas konfigurasi.
    """
    return [
        JS_TARGET,
        "--ignore-pattern",
        "site/js/vendor/**",
        "--config",
        str(node_tools.lint_config("eslint.config.js")),
    ]


def stylelint_args():
    """
    Menyusun argumen stylelint bersama untuk mode perbaikan dan mode laporan.

    I.S. : -
    F.S. : List argumen dikembalikan. Config diambil lewat node_tools.lint_config dengan
           alasan yang sama seperti ESLint (plugin stylelint-order dicari dari lokasi config).
    """
    return ["--config", str(node_tools.lint_config(".stylelintrc.json")), CSS_TARGET]
```

- [ ] **Step 4: Run to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_node_tools.py tests/test_check.py -v` → all PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/web-build/scripts/lib/node_tools.py skills/web-build/scripts/check.py tests/test_node_tools.py
git commit -m "feat(check): place lint configs where their plugins resolve"
```

---

### Task 4: Dependency setup in `lib/deps.py`

**Files:**
- Create: `skills/web-build/scripts/lib/deps.py`
- Modify: `pytest.ini` (marker), `tests/conftest.py` (`--network` option)
- Test: `tests/test_deps.py`

**Interfaces:**
- Consumes: `lib.report.fail`, `EXIT_INVALID`, `ScriptExit`.
- Produces: `deps.cache_root() -> Path`, `deps.ensure_python_packages(repo_root: Path, cache: Path) -> Path | None` (None = interpreter already has the packages; otherwise the folder prepended to `sys.path`), `deps.ensure_node_tools(repo_root: Path, cache: Path) -> Path` (the `node_modules` folder to use).

- [ ] **Step 1: Add the `network` marker**

`pytest.ini`, under `markers =` add the line:

```ini
    network: test memasang dependensi dari internet (lambat); jalankan dengan --network
```

`tests/conftest.py`, after the imports, add:

```python
# ============================================================
# ======================== OPSI PYTEST =======================
# ============================================================


def pytest_addoption(parser):
    """
    Menambah opsi --network untuk tes yang memasang dependensi dari internet.

    I.S. : parser adalah parser opsi pytest.
    F.S. : Opsi --network tersedia.
    """
    parser.addoption("--network", action="store_true", help="jalankan tes bertanda network")


def pytest_collection_modifyitems(config, items):
    """
    Melewati tes bertanda network kecuali pytest dijalankan dengan --network.

    I.S. : items adalah tes yang terkumpul.
    F.S. : Tes network diberi tanda skip bila --network tidak diberikan.
    """
    if config.getoption("--network"):
        return

    skip = pytest.mark.skip(reason="butuh internet; jalankan dengan --network")

    for item in items:
        if "network" in item.keywords:
            item.add_marker(skip)
```

- [ ] **Step 2: Write the failing tests**

`tests/test_deps.py`:

```python
# ============================================================
# File      : test_deps.py
# Deskripsi : Pengujian lib/deps.py: lokasi cache, pemakaian dependensi
#             yang sudah ada, kegagalan yang jelas, dan pemasangan sekali
#             ke cache (bertanda network).
# ============================================================

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import REPO, SCRIPTS
from lib import deps
from lib.report import ScriptExit


@pytest.fixture
def stand_in_repo(tmp_path):
    """
    Menyiapkan repo tiruan yang hanya berisi file dependensi, tanpa node_modules.

    I.S. : tmp_path kosong.
    F.S. : tmp_path/plugin berisi package.json, package-lock.json, requirements.txt.
    """
    root = tmp_path / "plugin"
    root.mkdir()

    for name in ("package.json", "package-lock.json", "requirements.txt"):
        shutil.copyfile(REPO / name, root / name)

    return root


def python_only_path():
    """
    Menyusun PATH yang hanya berisi folder Python, tanpa node dan npm.

    I.S. : -
    F.S. : String PATH dikembalikan.
    """
    return str(Path(sys.executable).parent)


def test_cache_root_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("PD_CACHE_DIR", str(tmp_path))

    assert deps.cache_root() == tmp_path


@pytest.mark.skipif(os.name != "nt", reason="aturan Windows")
def test_cache_root_windows_default(monkeypatch, tmp_path):
    monkeypatch.delenv("PD_CACHE_DIR", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    assert deps.cache_root() == tmp_path / "web-skills"


@pytest.mark.skipif(os.name == "nt", reason="aturan POSIX")
def test_cache_root_posix_default(monkeypatch, tmp_path):
    monkeypatch.delenv("PD_CACHE_DIR", raising=False)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))

    assert deps.cache_root() == tmp_path / "web-skills"


def test_python_packages_already_importable_need_no_cache(tmp_path):
    assert deps.ensure_python_packages(REPO, tmp_path) is None
    assert list(tmp_path.iterdir()) == []


def test_node_tools_use_complete_repo_node_modules(tmp_path):
    assert deps.ensure_node_tools(REPO, tmp_path) == REPO / "node_modules"
    assert list(tmp_path.iterdir()) == []


def test_node_tools_without_node_fail_with_message(stand_in_repo, tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    monkeypatch.setenv("PATH", python_only_path())

    with pytest.raises(ScriptExit) as stop:
        deps.ensure_node_tools(stand_in_repo, cache)

    assert stop.value.code == 1
    assert "Node.js" in "\n".join(stop.value.lines)
    assert not cache.exists()


def test_failed_install_leaves_no_cache_folder(tmp_path):
    final = tmp_path / "cache" / "py-x"
    failing = [sys.executable, "-c", "import sys; sys.exit(3)"]

    with pytest.raises(ScriptExit) as stop:
        deps.install_into(final, "contoh", lambda tmp: subprocess.run(failing, capture_output=True, text=True))

    assert stop.value.code == 1
    assert list((tmp_path / "cache").iterdir()) == []


@pytest.mark.network
def test_node_tools_install_into_cache_once(stand_in_repo, tmp_path, monkeypatch):
    cache = tmp_path / "cache"

    modules = deps.ensure_node_tools(stand_in_repo, cache)

    assert (modules / "eslint" / "package.json").is_file()
    assert modules.parent.parent == cache

    # Panggilan kedua tanpa node/npm di PATH harus memakai cache tanpa memasang ulang
    monkeypatch.setenv("PATH", python_only_path())
    assert deps.ensure_node_tools(stand_in_repo, cache) == modules


@pytest.mark.network
def test_python_packages_install_into_cache_once(stand_in_repo, tmp_path):
    cache = tmp_path / "cache"
    probe = (
        "import sys; sys.path.insert(0, sys.argv[1]);"
        "from pathlib import Path; from lib import deps;"
        "target = deps.ensure_python_packages(Path(sys.argv[2]), Path(sys.argv[3]));"
        "import yaml, jsonschema, bs4, tinycss2; print(target)"
    )

    def run_probe():
        """
        Menjalankan probe di Python tanpa site-packages (-S).

        I.S. : -
        F.S. : CompletedProcess dikembalikan.
        """
        return subprocess.run(
            [sys.executable, "-S", "-c", probe, str(SCRIPTS), str(stand_in_repo), str(cache)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=600,
        )

    first = run_probe()
    assert first.returncode == 0, first.stdout + first.stderr
    target = Path(first.stdout.strip().splitlines()[-1])
    assert target.parent == cache
    (target / "sentinel").write_text("x", encoding="utf-8")

    second = run_probe()
    assert second.returncode == 0, second.stdout + second.stderr
    assert Path(second.stdout.strip().splitlines()[-1]) == target
    assert (target / "sentinel").is_file()
```

- [ ] **Step 3: Run to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_deps.py -v`
Expected: collection error `ImportError: cannot import name 'deps' from 'lib'`.

- [ ] **Step 4: Implement `lib/deps.py`**

```python
# ============================================================
# File      : deps.py
# Deskripsi : Memastikan paket Python dan alat Node tersedia sebelum skrip
#             berjalan: pakai yang sudah ada, atau pasang sekali ke folder
#             cache pengguna. Hanya memakai pustaka standar dan lib.report,
#             karena modul ini berjalan sebelum paket pihak ketiga terpasang.
# ============================================================

import functools
import hashlib
import importlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from lib.report import EXIT_INVALID, fail

# ============================================================
# ========================= KONSTANTA ========================
# ============================================================

# Nama modul yang diimpor skrip (bukan nama paket pip)
PYTHON_MODULES = ("yaml", "jsonschema", "bs4", "tinycss2")

NODE_MANIFESTS = ("package.json", "package-lock.json")


# ============================================================
# =========================== CACHE ==========================
# ============================================================


def cache_root():
    """
    Menentukan folder cache dependensi milik pengguna.

    I.S. : PD_CACHE_DIR, LOCALAPPDATA, atau XDG_CACHE_HOME boleh diatur.
    F.S. : Urutan: PD_CACHE_DIR; %LOCALAPPDATA%/web-skills di Windows;
           $XDG_CACHE_HOME/web-skills; ~/.cache/web-skills. Path belum tentu ada.
    """
    override = os.environ.get("PD_CACHE_DIR")

    if override:
        return Path(override)

    local_app_data = os.environ.get("LOCALAPPDATA")

    if os.name == "nt" and local_app_data:
        return Path(local_app_data) / "web-skills"

    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else Path.home() / ".cache"

    return base / "web-skills"


def file_hash(path):
    """
    Menghitung sidik pendek isi file untuk nama folder cache.

    I.S. : path adalah file yang ada.
    F.S. : 12 karakter heksadesimal pertama SHA-256 isi file dikembalikan.
    """
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:12]


def output_tail(result):
    """
    Meringkas keluaran installer yang gagal.

    I.S. : result adalah CompletedProcess installer.
    F.S. : Paling banyak 8 baris terakhir stderr (atau stdout), masing-masing diindentasi.
    """
    text = (result.stderr or result.stdout or "").strip()

    return ["  " + line for line in text.splitlines()[-8:]]


def install_into(final, label, install):
    """
    Memasang dependensi ke folder sementara lalu me-rename-nya menjadi folder akhir.

    I.S. : final belum ada; install(tmp) menjalankan installer ke folder tmp dan
           mengembalikan CompletedProcess.
    F.S. : final berisi hasil instalasi lengkap. Bila installer gagal, folder sementara
           dihapus dan ScriptExit kode 1 dilempar, jadi folder akhir yang ada selalu lengkap.
    """
    tmp = final.with_name(f"{final.name}.tmp-{os.getpid()}")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    print(f"Menyiapkan {label} sekali saja di {final} ...", flush=True)

    result = install(tmp)

    if result.returncode != 0:
        shutil.rmtree(tmp, ignore_errors=True)
        fail(
            EXIT_INVALID,
            [f"Pemasangan {label} gagal (kode keluar {result.returncode}):"] + output_tail(result),
            f"tell the user that installing {label} failed (see the lines above; usually no "
            "internet connection), then run the same command again",
        )

    try:
        tmp.rename(final)
    except OSError:
        # Proses lain selesai lebih dulu; hasilnya dipakai
        shutil.rmtree(tmp, ignore_errors=True)

        if not final.is_dir():
            raise


# ============================================================
# ======================= PAKET PYTHON =======================
# ============================================================


def python_packages_importable():
    """
    Memeriksa apakah interpreter ini sudah bisa mengimpor semua paket.

    I.S. : -
    F.S. : True bila setiap modul di PYTHON_MODULES ditemukan.
    """
    return all(importlib.util.find_spec(name) is not None for name in PYTHON_MODULES)


def pip_install(requirements, tmp):
    """
    Memasang requirements.txt ke folder tmp dengan pip --target.

    I.S. : requirements adalah path requirements.txt; tmp folder kosong.
    F.S. : CompletedProcess pip dikembalikan.
    """
    command = [
        sys.executable, "-m", "pip", "install",
        "--disable-pip-version-check", "--no-input", "--quiet",
        "--target", str(tmp), "-r", str(requirements),
    ]

    return subprocess.run(command, capture_output=True, text=True, encoding="utf-8")


def ensure_python_packages(repo_root, cache):
    """
    Memastikan paket Python di requirements.txt bisa diimpor.

    I.S. : repo_root berisi requirements.txt; cache adalah folder cache pengguna.
    F.S. : None bila interpreter sudah punya paketnya. Selain itu folder
           <cache>/py-<versi>-<hash> (dipasang dulu bila belum ada) ditambahkan ke awal
           sys.path dan dikembalikan. ScriptExit kode 1 bila pip gagal.
    """
    if python_packages_importable():
        return None

    requirements = Path(repo_root) / "requirements.txt"
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    target = Path(cache) / f"py-{version}-{file_hash(requirements)}"

    if not target.is_dir():
        install_into(target, "paket Python (pip)", functools.partial(pip_install, requirements))

    sys.path.insert(0, str(target))
    importlib.invalidate_caches()

    return target


# ============================================================
# ========================= ALAT NODE ========================
# ============================================================


def node_packages(repo_root):
    """
    Membaca nama paket Node yang dibutuhkan dari package.json.

    I.S. : repo_root berisi package.json.
    F.S. : List nama paket di dependencies dan devDependencies, terurut.
    """
    manifest = json.loads((Path(repo_root) / "package.json").read_text(encoding="utf-8"))
    names = {**manifest.get("dependencies", {}), **manifest.get("devDependencies", {})}

    return sorted(names)


def node_modules_complete(folder, packages):
    """
    Memeriksa apakah sebuah node_modules memuat semua paket.

    I.S. : folder boleh belum ada.
    F.S. : True bila setiap paket punya package.json di folder itu.
    """
    return all((folder / name / "package.json").is_file() for name in packages)


def npm_ci(repo_root, npm, tmp):
    """
    Memasang alat Node persis sesuai package-lock.json ke folder tmp.

    I.S. : npm adalah path perintah npm; tmp folder kosong.
    F.S. : package.json dan package-lock.json tersalin ke tmp; CompletedProcess npm ci
           dikembalikan.
    """
    for name in NODE_MANIFESTS:
        shutil.copyfile(Path(repo_root) / name, tmp / name)

    command = [npm, "ci", "--no-audit", "--no-fund", "--loglevel=error"]

    return subprocess.run(command, cwd=tmp, capture_output=True, text=True, encoding="utf-8")


def ensure_node_tools(repo_root, cache):
    """
    Memastikan alat Node di package.json tersedia.

    I.S. : repo_root berisi package.json dan package-lock.json; cache adalah folder cache.
    F.S. : node_modules repo dikembalikan bila lengkap. Selain itu
           <cache>/node-<hash>/node_modules (dipasang dulu dengan npm ci bila belum ada)
           dikembalikan. ScriptExit kode 1 bila node/npm tidak ada atau npm ci gagal.
    """
    repo_root = Path(repo_root)
    packages = node_packages(repo_root)
    local = repo_root / "node_modules"

    if node_modules_complete(local, packages):
        return local

    final = Path(cache) / f"node-{file_hash(repo_root / 'package-lock.json')}"

    if not final.is_dir():
        npm = shutil.which("npm")

        if npm is None or shutil.which("node") is None:
            fail(
                EXIT_INVALID,
                [
                    "Node.js (perintah node dan npm) tidak ditemukan di PATH.",
                    "Pasang Node.js versi LTS dari https://nodejs.org, lalu buka terminal baru.",
                ],
                "tell the user to install Node.js LTS from https://nodejs.org and open a new "
                "terminal, then run the same command again",
            )

        install_into(final, "alat Node (npm ci)", functools.partial(npm_ci, repo_root, npm))

    return final / "node_modules"
```

- [ ] **Step 5: Run to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_deps.py -v` → offline tests PASS, network tests SKIPPED.
Run: `.venv/Scripts/python.exe -m pytest tests/test_deps.py -v --network` → all PASS (needs internet, 1-3 minutes).

- [ ] **Step 6: Commit**

```bash
git add skills/web-build/scripts/lib/deps.py tests/test_deps.py tests/conftest.py pytest.ini
git commit -m "feat(deps): install Python packages and Node tools into a user cache on first use"
```

---

### Task 5: Launcher `run.py`

**Files:**
- Create: `skills/web-build/scripts/run.py`
- Modify: `tests/conftest.py` (`run_script` gains `cwd=REPO`)
- Test: `tests/test_run.py`

**Interfaces:**
- Consumes: `deps.cache_root`, `deps.ensure_python_packages`, `deps.ensure_node_tools` (Task 4); `paths.REPO_ROOT`, `paths.is_valid_slug`, `paths.project_dir` (Task 2).
- Produces: CLI `python run.py <command> [args…]`; module constant `run.SCRIPTS` (tuple of the nine script names) used by Task 6's test; `path <slug>` prints `PROJECT: <absolute folder>` and `NEXT: write the project files in that folder`.

- [ ] **Step 1: Let `run_script` take a working folder**

In `tests/conftest.py` change the signature and the `cwd` argument of `run_script`:

```python
def run_script(name, *args, script_dir=SCRIPTS, cwd=REPO):
    """
    Menjalankan satu skrip sebagai proses terpisah, seperti agen memanggilnya.

    I.S. : Variabel lingkungan tes sudah diatur oleh fixture; cwd adalah folder kerja
           (bawaan: root repo).
    F.S. : CompletedProcess dikembalikan; stdout dan stderr berupa teks UTF-8.
    """
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    command = [sys.executable, str(script_dir / f"{name}.py"), *map(str, args)]

    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=600,
    )
```

- [ ] **Step 2: Write the failing tests**

`tests/test_run.py`:

```python
# ============================================================
# File      : test_run.py
# Deskripsi : Pengujian run.py: penolakan perintah tak dikenal, penerusan
#             ke skrip, kode keluar skrip, dan subperintah path.
# ============================================================

from pathlib import Path

from conftest import REPO, next_line, run_script


def printed_project(result):
    """
    Mengambil folder dari baris PROJECT: keluaran run.py path.

    I.S. : result adalah CompletedProcess run.py path.
    F.S. : Path dikembalikan, atau None bila tidak ada baris PROJECT:.
    """
    lines = [line for line in result.stdout.splitlines() if line.startswith("PROJECT: ")]

    return Path(lines[-1].removeprefix("PROJECT: ")) if lines else None


def test_run_unknown_command_lists_valid_names():
    result = run_script("run", "deploy", "kopi-senja")

    assert result.returncode == 1
    assert "validate_brief" in result.stdout
    assert "path" in result.stdout
    assert next_line(result) == "NEXT: use one of the listed commands"


def test_run_without_command_fails():
    result = run_script("run")

    assert result.returncode == 1


def test_run_dispatches_to_script(kopi):
    direct = run_script("validate_brief", "kopi-senja")
    via_run = run_script("run", "validate_brief", "kopi-senja")

    assert direct.returncode == 0
    assert via_run.returncode == 0
    assert next_line(via_run) == next_line(direct) == "NEXT: run gaps.py"


def test_run_passes_script_exit_code_through(projects_dir):
    result = run_script("run", "validate_brief", "belum-ada")

    assert result.returncode == 1
    assert next_line(result).startswith("NEXT: write ")


def test_run_path_outside_repo(monkeypatch, tmp_path):
    monkeypatch.delenv("PD_PROJECTS_DIR", raising=False)

    result = run_script("run", "path", "kopi-senja", cwd=tmp_path)

    assert result.returncode == 0, result.stdout
    assert printed_project(result) == tmp_path.resolve() / "kopi-senja"
    assert next_line(result) == "NEXT: write the project files in that folder"
    assert not (tmp_path / "kopi-senja").exists()


def test_run_path_in_repo(monkeypatch):
    monkeypatch.delenv("PD_PROJECTS_DIR", raising=False)

    result = run_script("run", "path", "kopi-senja", cwd=REPO)

    assert printed_project(result) == REPO / "projects" / "kopi-senja"


def test_run_path_env_wins(monkeypatch, tmp_path):
    monkeypatch.setenv("PD_PROJECTS_DIR", str(tmp_path))

    result = run_script("run", "path", "kopi-senja", cwd=REPO)

    assert printed_project(result) == tmp_path.resolve() / "kopi-senja"


def test_run_path_rejects_invalid_slug():
    result = run_script("run", "path", "Kopi Senja")

    assert result.returncode == 1
```

- [ ] **Step 3: Run to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_run.py -v`
Expected: all FAIL (`run.py` does not exist: returncode 2 from Python, `can't open file`).

- [ ] **Step 4: Implement `run.py`**

```python
# ============================================================
# File      : run.py
# Proyek    : web-skills
# Deskripsi : Satu pintu untuk semua skrip web-build. Memastikan paket Python
#             dan alat Node tersedia (memasangnya sekali ke cache bila perlu),
#             lalu menjalankan skrip yang diminta di proses yang sama.
#             Subperintah 'path' mencetak folder proyek.
# ============================================================

import os
import platform
import runpy
import sys
from pathlib import Path

# Memungkinkan impor modul lib saat dijalankan langsung
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import deps, paths, report
from lib.report import EXIT_INVALID, fail

# ============================================================
# ========================= KONSTANTA ========================
# ============================================================

SCRIPTS = (
    "validate_brief",
    "gaps",
    "serve",
    "pick_direction",
    "compile_tokens",
    "scaffold",
    "context",
    "check",
    "handoff",
)

MIN_PYTHON = (3, 11)


# ============================================================
# ======================== SUBPERINTAH =======================
# ============================================================


def project_path(args):
    """
    Mencetak folder proyek untuk satu slug tanpa membuat apa pun.

    I.S. : args berisi tepat satu slug.
    F.S. : Baris 'PROJECT: <folder absolut>' dan langkah berikutnya dikembalikan;
           ScriptExit kode 1 bila slug tidak sah.
    """
    if len(args) != 1 or not paths.is_valid_slug(args[0]):
        fail(EXIT_INVALID, "Penggunaan: run.py path <slug> (slug kebab-case huruf kecil).",
             "choose a kebab-case slug and run path again")

    folder = paths.project_dir(args[0]).resolve()

    return [f"PROJECT: {folder}"], "write the project files in that folder"


def prepare_dependencies():
    """
    Memastikan paket Python dan alat Node siap sebelum skrip dijalankan.

    I.S. : paths.REPO_ROOT berisi requirements.txt, package.json, package-lock.json.
    F.S. : Paket Python bisa diimpor; PD_NODE_MODULES menunjuk node_modules yang dipakai.
    """
    cache = deps.cache_root()
    deps.ensure_python_packages(paths.REPO_ROOT, cache)
    node_modules = deps.ensure_node_tools(paths.REPO_ROOT, cache)
    os.environ["PD_NODE_MODULES"] = str(node_modules)


# ============================================================
# ======================== LOGIKA UTAMA ======================
# ============================================================


def main():
    """
    Titik masuk CLI: memeriksa Python dan perintah, lalu menjalankan path atau satu skrip.

    I.S. : sys.argv berisi perintah dan argumennya.
    F.S. : Untuk path: hasil project_path dikembalikan. Untuk skrip: dependensi disiapkan
           dan skrip dijalankan; skrip itu sendiri mencetak NEXT: dan mengakhiri proses
           dengan kode keluarnya. ScriptExit kode 1 untuk Python lama atau perintah salah.
    """
    if sys.version_info < MIN_PYTHON:
        fail(EXIT_INVALID, f"Python {platform.python_version()} terlalu lama; web-skills butuh Python 3.11 atau lebih baru.",
             "tell the user to install Python 3.11 or newer, then run the same command again")

    commands = ("path", *SCRIPTS)

    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        given = sys.argv[1] if len(sys.argv) > 1 else "(kosong)"
        fail(EXIT_INVALID, [f"Perintah tidak dikenal: {given}", f"Perintah yang sah: {', '.join(commands)}"],
             "use one of the listed commands")

    command, args = sys.argv[1], sys.argv[2:]

    if command == "path":
        return project_path(args)

    prepare_dependencies()

    script = Path(__file__).resolve().parent / f"{command}.py"
    sys.argv = [str(script), *args]
    runpy.run_path(str(script), run_name="__main__")

    # Setiap skrip mengakhiri proses sendiri; baris ini hanya tercapai bila skrip berubah
    fail(EXIT_INVALID, f"{command}.py selesai tanpa kode keluar.", "report this to the maintainer")


if __name__ == "__main__":
    report.run(main)
```

- [ ] **Step 5: Run to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_run.py -v` → all PASS.
Run: `.venv/Scripts/python.exe -m pytest -q` → all PASS.

- [ ] **Step 6: Commit**

```bash
git add skills/web-build/scripts/run.py tests/test_run.py tests/conftest.py
git commit -m "feat(run): launcher that prepares dependencies and runs one script"
```

---

### Task 6: Skill text uses plugin paths

**Files:**
- Modify: `skills/web-build/SKILL.md`, `skills/web-design/SKILL.md`
- Test: `tests/test_skill_text.py`

**Interfaces:**
- Consumes: `run.SCRIPTS` (Task 5); `run.py path` output contract (Task 5).

- [ ] **Step 1: Write the failing tests**

`tests/test_skill_text.py`:

```python
# ============================================================
# File      : test_skill_text.py
# Deskripsi : Pengujian rujukan di SKILL.md: setiap path plugin ada, dan
#             setiap perintah python lewat run.py dengan perintah yang sah.
# ============================================================

import re

import run
from conftest import REPO

SKILL_FILES = [REPO / "skills" / "web-build" / "SKILL.md", REPO / "skills" / "web-design" / "SKILL.md"]
ROOT_REF = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\s`\"')]+)")
COMMAND = re.compile(r"`python ([^`]+)`")
RUN = '"${CLAUDE_PLUGIN_ROOT}/skills/web-build/scripts/run.py"'


def test_every_plugin_root_path_exists():
    for skill in SKILL_FILES:
        for ref in ROOT_REF.findall(skill.read_text(encoding="utf-8")):
            ref = ref.rstrip(".,;:")
            pattern = re.sub(r"<[^>]+>", "*", ref)

            assert list(REPO.glob(pattern)), f"{skill.parent.name}/SKILL.md: {ref} tidak ada"


def test_every_python_command_goes_through_run_py():
    valid = {"path", *run.SCRIPTS}
    commands = []

    for skill in SKILL_FILES:
        commands += COMMAND.findall(skill.read_text(encoding="utf-8"))

    assert commands, "SKILL.md tidak memuat perintah python"

    for command in commands:
        assert command.startswith(RUN + " "), command
        assert command[len(RUN) + 1:].split()[0] in valid, command
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_skill_text.py -v`
Expected: `test_every_python_command_goes_through_run_py` FAIL on `skills/web-build/scripts/validate_brief.py <slug>`; the path test passes trivially (no references yet).

- [ ] **Step 3: Rewrite `skills/web-build/SKILL.md`**

Keep the frontmatter unchanged. Replace everything after it with (each command stays on one line):

```markdown
# web-build

Turn one prompt into a finished site in its own project folder. Decisions come first, code
second, checks last. Scripts do every deterministic step; you do only steps 1, 3, 5, 6
and the fixes in step 7.

## Ground rules

- Work through the steps in order. Write site files only after step 4 succeeds.
- Use only facts the user gave. Every other fact (address, phone, prices, hours,
  testimonials, client logos, statistics) becomes a placeholder `[[ISI: <what>]]`.
- Run every command from the folder Claude Code was opened in, exactly as written here.
  Every script prints what it wrote and exits non-zero on failure; read its output before
  moving on. On a new machine the first command installs the Python packages and Node
  tools once (about a minute, needs internet); let it finish.
- `<project>` below is the folder printed in step 1. Write every project file there.
- Work without stopping to ask the user, unless they asked for interactive mode or a
  script tells you to ask.
- If `${CLAUDE_PLUGIN_ROOT}/skills` appears literally in this file (the skill was loaded
  without plugin support), it means the folder that contains this skill's folder.

## Steps

1. **Brief.** Choose a short kebab-case slug, then run
   `python "${CLAUDE_PLUGIN_ROOT}/skills/web-build/scripts/run.py" path <slug>`.
   It prints `PROJECT: <folder>`; that folder is `<project>`. Write `<project>/brief.yaml`
   following `${CLAUDE_PLUGIN_ROOT}/skills/web-build/schemas/brief.schema.json`. Set every
   field the prompt does not state to `unknown`; mark stated fields with `source: stated`.
   Then run `python "${CLAUDE_PLUGIN_ROOT}/skills/web-build/scripts/run.py" validate_brief <slug>`
   and fix until it passes.

2. **Gaps.** Run `python "${CLAUDE_PLUGIN_ROOT}/skills/web-build/scripts/run.py" gaps <slug>`.
   It turns missing facts into placeholders and lists the open design decisions in
   `<project>/gaps.json`. Interactive mode only: run
   `python "${CLAUDE_PLUGIN_ROOT}/skills/web-build/scripts/run.py" serve <slug>` in the
   background, give the user the printed URL, and wait until the script reports the answers.

3. **Direction.** Read `${CLAUDE_PLUGIN_ROOT}/skills/web-design/SKILL.md` and follow it to
   write `<project>/directions.yaml`. Then run
   `python "${CLAUDE_PLUGIN_ROOT}/skills/web-build/scripts/run.py" pick_direction <slug>`.
   It writes `decisions.yaml`.

4. **Tokens and scaffold.** Run
   `python "${CLAUDE_PLUGIN_ROOT}/skills/web-build/scripts/run.py" compile_tokens <slug>`,
   then `python "${CLAUDE_PLUGIN_ROOT}/skills/web-build/scripts/run.py" scaffold <slug>`.
   The scaffold creates `<project>/site/`: the folder structure, `css/tokens.css`,
   `css/base.css`, and one skeleton HTML file per page whose sections are empty shells in
   the right order.

5. **Copy.** Read `${CLAUDE_PLUGIN_ROOT}/skills/web-build/references/copy-<lang>.md` for
   each language in the brief and
   `${CLAUDE_PLUGIN_ROOT}/skills/web-build/site-types/<site_type>.yaml`. Write
   `<project>/content/<lang>.yaml`: one entry per section listed in the site type, with
   headings, body text, and button labels. Collections the brief does not give (catalog
   products, portfolio projects) and every dashboard figure are data, not copy: add one
   endpoint per collection to `<project>/site/js/api/endpoints.js` and its response to
   `<project>/site/data/mock/<name>.mock.json`, following "Data and the mock API" in
   `${CLAUDE_PLUGIN_ROOT}/skills/web-build/references/conventions.md`. Collections the brief
   does give are content and go straight into the page; a stated API source means
   `API_MODE = 'live'` with that API's paths.

6. **Build.** Read `${CLAUDE_PLUGIN_ROOT}/skills/web-build/references/conventions.md`.
   Then, one page at a time, run
   `python "${CLAUDE_PLUGIN_ROOT}/skills/web-build/scripts/run.py" context <slug> <page>`;
   it prints exactly what that page needs (decisions, section patterns, token names,
   component recipes, placeholders). Fill each section shell of the page from
   `<project>/content/<lang>.yaml`, keeping its `class`, `id`, and `data-pd-pattern`, and
   write the CSS and JS in the files the scaffold made, using only the variables in
   `css/tokens.css`.

7. **Check and fix.** Run
   `python "${CLAUDE_PLUGIN_ROOT}/skills/web-build/scripts/run.py" check <slug>`. It formats
   the code, runs the linters and the audit, and writes `<project>/report.json` with each
   finding and a suggested replacement. Fix every `error`, then every `warning`, then run it
   again. The script counts rounds, keeps a copy of each round, and tells you when to stop.
   If you can start a subagent, give it
   `${CLAUDE_PLUGIN_ROOT}/skills/web-build/references/a11y-judge.md` and the built HTML, and
   apply its findings as one extra round. If you cannot, note "semantic review skipped".

8. **Handoff.** Run
   `python "${CLAUDE_PLUGIN_ROOT}/skills/web-build/scripts/run.py" handoff <slug>` and show
   its summary to the user exactly as printed: assumptions taken, placeholders to fill, and
   check scores.
```

- [ ] **Step 4: Rewrite the path lines of `skills/web-design/SKILL.md`**

Replace the `## Inputs` list:

```markdown
## Inputs

- `<project>/brief.yaml` and `<project>/gaps.json` (it lists requirement ids such as
  `req-audience` that your rationale must cite). `<project>` is the folder printed by
  `python "${CLAUDE_PLUGIN_ROOT}/skills/web-build/scripts/run.py" path <slug>`; web-build
  step 1 has already run it.
- `${CLAUDE_PLUGIN_ROOT}/skills/web-design/styles/index.yaml`: one line per style. Read only
  this catalog first, then open the full file of each style you actually use.
- `${CLAUDE_PLUGIN_ROOT}/skills/web-design/layouts/patterns.yaml`: the layout patterns
  available for each section kind.

If `${CLAUDE_PLUGIN_ROOT}/skills` appears literally in this file (the skill was loaded
without plugin support), it means the folder that contains this skill's folder.
```

Replace the heading `## Write \`projects/<slug>/directions.yaml\`` with:

```markdown
## Write `<project>/directions.yaml`
```

Replace the sentence about the schema:

```markdown
`based_on` lists requirement ids exactly as `gaps.json` prints them. The file must pass
`${CLAUDE_PLUGIN_ROOT}/skills/web-build/schemas/directions.schema.json`; `pick_direction`
reports any mismatch.
```

- [ ] **Step 5: Run to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_skill_text.py -v` → 2 PASS.

- [ ] **Step 6: Commit**

```bash
git add skills/web-build/SKILL.md skills/web-design/SKILL.md tests/test_skill_text.py
git commit -m "feat(skills): call scripts through run.py with plugin paths"
```

---

### Task 7: `sync_adapters.py` for Codex only

**Files:**
- Modify: `tools/sync_adapters.py`
- Test: `tests/test_sync_adapters.py` (rewrite)

**Interfaces:**
- Consumes: `paths.find_repo_root` (Task 2) through the copied `lib/` in the stand-in repo.

- [ ] **Step 1: Rewrite the tests against a stand-in repository**

`tests/test_sync_adapters.py`:

```python
# ============================================================
# File      : test_sync_adapters.py
# Deskripsi : Pengujian tools/sync_adapters.py pada salinan kecil repo,
#             agar .agents/ dan .claude/ milik repo asli tidak tersentuh.
# ============================================================

import os
import shutil
import subprocess
import sys

import pytest
from conftest import REPO, next_line


@pytest.fixture
def fake_repo(tmp_path):
    """
    Menyalin bagian repo yang dibutuhkan sync_adapters ke folder sementara.

    I.S. : tmp_path kosong.
    F.S. : tmp_path berisi skills/, tools/, audit/, config/.
    """
    for name in ("skills", "tools", "audit", "config"):
        shutil.copytree(REPO / name, tmp_path / name, ignore=shutil.ignore_patterns("__pycache__"))

    return tmp_path


def run_sync(root):
    """
    Menjalankan salinan sync_adapters.py --copy di root.

    I.S. : root adalah repo tiruan dari fake_repo.
    F.S. : CompletedProcess dikembalikan.
    """
    return subprocess.run(
        [sys.executable, str(root / "tools" / "sync_adapters.py"), "--copy"],
        cwd=root,
        env=dict(os.environ, PYTHONIOENCODING="utf-8"),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )


def test_sync_adapters_writes_codex_copies_only(fake_repo):
    res = run_sync(fake_repo)

    assert res.returncode == 0, res.stdout + res.stderr
    assert next_line(res) == "NEXT: adapters synced"
    assert (fake_repo / ".agents" / "skills" / "web-build" / "SKILL.md").is_file()
    assert (fake_repo / ".agents" / "skills" / "web-design" / "SKILL.md").is_file()
    assert not (fake_repo / ".claude").exists()


def test_sync_adapters_warns_on_stale_claude_copy(fake_repo):
    (fake_repo / ".claude" / "skills" / "web-build").mkdir(parents=True)

    res = run_sync(fake_repo)

    assert res.returncode == 0
    assert ".claude/skills/web-build" in res.stdout


def test_sync_adapters_warns_on_claude_md(fake_repo):
    (fake_repo / "CLAUDE.md").write_text("# Test\n", encoding="utf-8")

    res = run_sync(fake_repo)

    assert res.returncode == 0
    assert "PERINGATAN: CLAUDE.md ditemukan" in res.stdout
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_sync_adapters.py -v`
Expected: `test_sync_adapters_writes_codex_copies_only` FAIL (`.claude` exists) and `test_sync_adapters_warns_on_stale_claude_copy` FAIL (no warning); the CLAUDE.md test passes.

- [ ] **Step 3: Implement**

In `tools/sync_adapters.py`, change the header description:

```python
# Deskripsi : Sinkronisasi skill ke .agents/skills/ untuk Codex. Claude Code
#             memuat skill lewat plugin, jadi .claude/skills/ tidak ditulis lagi.
```

Replace the docstring of `sync_adapters`:

```python
    """
    Memeriksa validitas SKILL.md dan membuat tautan/salinan skill di .agents/skills/ (Codex).

    I.S. : Folder skills/ ada di root repo.
    F.S. : .agents/skills/ tersinkronisasi. Peringatan dicetak bila CLAUDE.md ada, dan untuk
           setiap salinan lama di .claude/skills/ yang akan membuat skill muncul dua kali di
           samping plugin.
    """
```

Remove the lines that define and create `claude_skills_dir`:

```python
    claude_skills_dir = REPO_ROOT / ".claude" / "skills"
```

```python
    claude_skills_dir.mkdir(parents=True, exist_ok=True)
```

Replace the block from `# Buat adapter di .claude dan .agents` to the end of the loop with:

```python
        # Salinan lama untuk Claude Code bentrok dengan skill dari plugin
        stale = REPO_ROOT / ".claude" / "skills" / s_name
        if stale.exists() or stale.is_symlink():
            lines.append(
                f"PERINGATAN: .claude/skills/{s_name} masih ada; hapus folder itu, karena Claude "
                "Code kini memuat skill lewat plugin dan skill akan muncul dua kali."
            )

        # Buat adapter untuk Codex
        adapter_label = "Codex (.agents/skills)"
        target_link = agents_skills_dir / s_name
        if target_link.is_symlink() or target_link.is_file():
            target_link.unlink()
        elif target_link.is_dir():
            shutil.rmtree(target_link)

        if copy_mode:
            shutil.copytree(s_dir, target_link)
            lines.append(f"  - [{s_name}] Disalin ke {adapter_label}")
        else:
            try:
                # Buat relative symlink: ../../skills/<s_name>
                rel_src = os.path.relpath(s_dir, agents_skills_dir)
                target_link.symlink_to(rel_src, target_is_directory=True)
                lines.append(f"  - [{s_name}] Symlink dibuat untuk {adapter_label}")
            except OSError:
                # Fallback ke copy jika izin symlink Windows tidak tersedia
                shutil.copytree(s_dir, target_link)
                lines.append(f"  - [{s_name}] Disalin (fallback tanpa hak symlink) ke {adapter_label}")
```

In `main()`, change the argparse description to `"Sinkronisasi skill ke .agents/skills/ untuk Codex."`.

- [ ] **Step 4: Run to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_sync_adapters.py -v` → 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/sync_adapters.py tests/test_sync_adapters.py
git commit -m "feat(tools): sync_adapters writes Codex adapters only and flags stale Claude copies"
```

---

### Task 8: End-to-end test of a fresh plugin install

**Files:**
- Test: `tests/test_plugin_e2e.py`

**Interfaces:**
- Consumes: everything above; expected `NEXT:` lines of each script (listed in the test).

- [ ] **Step 1: Write the test**

`tests/test_plugin_e2e.py`:

```python
# ============================================================
# File      : test_plugin_e2e.py
# Deskripsi : Simulasi pengguna baru: hanya isi plugin (tanpa node_modules
#             dan .venv), Python tanpa site-packages, cache kosong, folder
#             kerja kosong; seluruh pipeline lewat run.py harus lolos.
# ============================================================

import json
import os
import shutil
import subprocess
import sys

import pytest
from conftest import REPO, next_line

PLUGIN_DIRS = ("skills", "audit", "config", ".claude-plugin")
PLUGIN_FILES = ("package.json", "package-lock.json", "requirements.txt", "LICENSE")

STEPS = [
    (("path", "kopi-senja"), "NEXT: write the project files in that folder"),
    (("validate_brief", "kopi-senja"), "NEXT: run gaps.py"),
    (("gaps", "kopi-senja"), "NEXT: write directions.yaml (web-design skill)"),
    (("pick_direction", "kopi-senja", "--pick", "dir-2"), "NEXT: run compile_tokens.py"),
    (("compile_tokens", "kopi-senja"), "NEXT: run scaffold.py"),
    (("scaffold", "kopi-senja"), "NEXT: write content/id.yaml (web-build skill step 5)"),
    (("check", "kopi-senja"), "NEXT: run handoff.py"),
    (("handoff", "kopi-senja"), "NEXT: handoff complete"),
]


@pytest.mark.network
def test_fresh_plugin_install_builds_site(tmp_path):
    plugin = tmp_path / "plugin"
    for name in PLUGIN_DIRS:
        shutil.copytree(REPO / name, plugin / name, ignore=shutil.ignore_patterns("__pycache__"))
    for name in PLUGIN_FILES:
        shutil.copyfile(REPO / name, plugin / name)

    work = tmp_path / "work"
    (work / "kopi-senja").mkdir(parents=True)
    for name in ("brief.yaml", "directions.yaml"):
        shutil.copyfile(REPO / "examples" / "kopi-senja" / name, work / "kopi-senja" / name)

    env = {k: v for k, v in os.environ.items() if k not in ("PD_PROJECTS_DIR", "PD_NODE_MODULES")}
    env.update(PD_CACHE_DIR=str(tmp_path / "cache"), PD_DATE="2026-10-08", PYTHONIOENCODING="utf-8")
    run_py = plugin / "skills" / "web-build" / "scripts" / "run.py"

    for args, expected in STEPS:
        result = subprocess.run(
            [sys.executable, "-S", str(run_py), *args],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=900,
        )

        assert result.returncode == 0, f"{args}:\n{result.stdout}\n{result.stderr}"
        assert next_line(result) == expected, f"{args}:\n{result.stdout}"

    report = json.loads((work / "kopi-senja" / "report.json").read_text(encoding="utf-8"))
    assert report["summary"]["errors"] == 0
    assert not [f for f in report["findings"] if f["rule"] == "tool-failed"]
    assert (work / "kopi-senja" / "site" / "index.html").is_file()
    assert {p.name.split("-")[0] for p in (tmp_path / "cache").iterdir()} == {"py", "node"}
```

- [ ] **Step 2: Run it**

Run: `.venv/Scripts/python.exe -m pytest tests/test_plugin_e2e.py -v --network`
Expected: PASS (2-4 minutes). If a step fails, the assertion message shows that step's full output: fix the cause in the owning task's file, add a focused offline test there that reproduces it, and rerun.

- [ ] **Step 3: Commit**

```bash
git add tests/test_plugin_e2e.py
git commit -m "test(plugin): end-to-end build from a fresh plugin install"
```

---

### Task 9: Documentation and final verification

**Files:**
- Create: `README.md`
- Modify: `AGENTS.md`, `IMPLEMENTATION.md`

- [ ] **Step 1: Write `README.md`**

````markdown
# web-skills

A Claude Code plugin that turns a short prompt into a finished website: company profile,
landing page, portfolio, small-business catalog, or dashboard, in Indonesian, English, or
both. Every design decision is recorded and every page is formatted, linted, and audited
before handoff.

## Requirements

- [Claude Code](https://claude.com/claude-code)
- Python 3.11 or newer, reachable as `python`. On Windows, install it from python.org; the
  Microsoft Store shortcut named `python` is not a real install.
- Node.js LTS (includes `npm`).

## Install

In Claude Code:

```
/plugin marketplace add rasyiq03/web-dev-skills
/plugin install web-skills@web-dev-skills
```

## Use

Open Claude Code in the folder where the site should go and describe it, for example:

```
buat company profile Kopi Senja, kedai kopi di Bandung, target mahasiswa
```

The site is built in `<folder>/<slug>/`, for example `kopi-senja/`:

- `site/`: the website. Preview it with `python -m http.server` inside `site/`, then open
  http://localhost:8000 (pages use ES modules, which do not load from `file://`).
- `HANDOFF.md`: the chosen design direction, assumptions, and every placeholder
  `[[ISI: …]]` still to fill.
- `brief.yaml`, `decisions.yaml`, `content/`: the recorded decisions, kept for later
  changes.

Add "pakai mode interaktif" to the prompt to answer a short questionnaire in the browser
first.

## First run and the dependency cache

The first build on a machine installs the Python packages and Node tools the checks need
(about a minute, needs internet). They go to a cache that later builds reuse:

- Windows: `%LOCALAPPDATA%\web-skills`
- macOS and Linux: `~/.cache/web-skills`

Set `PD_CACHE_DIR` to use another folder. Uninstalling the plugin does not remove the
cache; delete the folder by hand.

## Update

```
/plugin marketplace update web-dev-skills
```

## Development

```
git clone https://github.com/rasyiq03/web-dev-skills.git
cd web-dev-skills
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
npm run setup
python -m pytest
```

Load the working copy as the plugin, so edits apply without reinstalling: in Claude Code,
`/plugin marketplace add <path to the clone>` and `/plugin install web-skills@web-dev-skills`.
Sites built while Claude Code is open in the clone go to `projects/<slug>/`.
`python -m pytest --network` also runs the slow tests that install dependencies from the
internet. For Codex, `python tools/sync_adapters.py` links the skills into `.agents/skills/`.

`IMPLEMENTATION.md` specifies every script.

## License

MIT
````

- [ ] **Step 2: Update `AGENTS.md`**

Replace the whole file with:

```markdown
# Website builder

This repository turns a short prompt into a finished website, with every design
decision recorded and every page checked before handoff. It is also the Claude Code
plugin `web-skills`; `README.md` explains installing it.

- To build or redesign a site, follow `skills/web-build/SKILL.md`.
- Projects live in `projects/<slug>/` while you work in this repository, in
  `<folder>/<slug>/` when the plugin runs elsewhere, and in `$PD_PROJECTS_DIR/<slug>/`
  when that variable is set. `python skills/web-build/scripts/run.py path <slug>` prints
  the folder. Each run writes only inside its own project folder.
- Scripts run from the repository root with
  `python skills/web-build/scripts/run.py <name> <slug>`.
- Files in `config/` and `audit/` are fixed; change them only when the user asks.

Development setup (once): `pip install -r requirements.txt -r requirements-dev.txt`,
`npm run setup`, then load this folder as the plugin (see "Development" in `README.md`).
```

- [ ] **Step 3: Update `IMPLEMENTATION.md`**

§0, replace the bullet that starts with "Every script:":

```markdown
- Every script: `python skills/web-build/scripts/<name>.py <slug> [options]`, or through
  the launcher `python skills/web-build/scripts/run.py <name> <slug> [options]`, which
  installs the dependencies on first use (see
  `docs/superpowers/specs/2026-10-08-plugin-packaging-design.md`). A script reads and
  writes only inside its project folder (§2), plus reading `skills/`, `audit/`, `config/`.
```

§1, in the layout block, add after the first line:

```text
.claude-plugin/  plugin.json marketplace.json (Claude Code plugin and marketplace)
LICENSE  README.md  docs/superpowers/ (specs and plans)
```

and change the `scripts/` line to:

```text
		scripts/     run.py validate_brief.py gaps.py serve.py pick_direction.py compile_tokens.py
		             scaffold.py context.py check.py handoff.py lib/ (deps.py node_tools.py …)
```

and the `projects/<slug>/` line to:

```text
<project>/             created at run time (see section 2)
```

§2, after the heading `## 2. Files inside \`projects/<slug>/\``, insert:

```markdown
The project folder is `$PD_PROJECTS_DIR/<slug>/` when that variable is set,
`projects/<slug>/` when the scripts run from the repository root, and otherwise
`<current folder>/<slug>/`. `run.py path <slug>` prints it.
```

§3.10, replace the section body with:

```markdown
- For each `skills/<name>/`, checks that `SKILL.md` frontmatter `name` equals `<name>` and
  the description is under 1,024 characters.
- Creates relative symlinks `.agents/skills/<name>` (Codex) pointing to `skills/<name>`.
  `--copy` copies instead (Windows without symlink rights). Claude Code loads the skills
  through the plugin, so `.claude/skills/` is not written; a leftover copy there produces a
  warning, because the skill would be listed twice. Warns when a `CLAUDE.md` exists.
```

- [ ] **Step 4: Full verification**

Run each and read the output:

1. `.venv/Scripts/python.exe -m pytest -q` → all pass, network tests skipped.
2. `.venv/Scripts/python.exe -m pytest -q --network -m network` → all pass.
3. `claude plugin validate --strict .claude-plugin/plugin.json` and `claude plugin validate --strict .claude-plugin/marketplace.json` → both `Validation passed`.
4. Docstring convention: every function in `skills/web-build/scripts/**/*.py` and `tools/*.py` has `I.S.` and `F.S.` (same AST scan as commit e950c02).
5. `python tools/sync_adapters.py --copy` in the real repo → prints the stale `.claude/skills` warnings (the maintainer deletes those copies after installing the plugin from the local marketplace).

- [ ] **Step 5: Commit**

```bash
git add README.md AGENTS.md IMPLEMENTATION.md
git commit -m "docs: README for plugin users, development flow, updated implementation brief"
```
