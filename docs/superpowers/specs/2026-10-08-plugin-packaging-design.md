# Plugin packaging — design

Date: 2026-10-08 · Status: approved in conversation, awaiting written-spec review

## Goal

Anyone with Python 3.11+ and Node.js installs this repository as a Claude Code plugin and
builds a site from any folder, without cloning the repository:

```
/plugin marketplace add rasyiq03/web-dev-skills
/plugin install web-skills@web-dev-skills
```

Then, in any folder, a prompt such as "buat company profile Kopi Senja, kedai kopi di
Bandung, target mahasiswa" produces `<folder>/kopi-senja/` with a site that `check.py`
passes with zero errors.

**Success criteria**

- A machine with only Python and Node.js (no clone, no `pip install`, no `npm install`)
  installs the plugin and builds a site end to end.
- Python packages and Node tools are installed automatically on first use, at the versions
  pinned in `requirements.txt` and `package-lock.json`.
- The existing development flow (working inside this repository) and the Codex adapter
  keep working.
- No failure is silent: a missing tool or a failed install stops with a message that says
  what to install.

**Decisions taken in the conversation**

| Topic | Decision |
| --- | --- |
| Distribution | Claude Code plugin; this repository is also its own marketplace |
| Dependency setup | Approach A: a launcher `run.py` installs dependencies on first use |
| Project location | One subfolder per site in the folder Claude Code was opened in |
| License | MIT |

## 1. Packaging and install

New files at the repository root:

- `.claude-plugin/plugin.json`: `name: web-skills`, `version: 0.1.0`, a one-line
  `description`, `author: { name: Rasyiq03 }`, `homepage` and `repository` set to
  `https://github.com/rasyiq03/web-dev-skills`, `license: MIT`, `keywords`. The version
  lives only here; users stay on it until it is raised, so every release raises it.
- `.claude-plugin/marketplace.json`: marketplace `name: web-dev-skills`, `owner:
  { name: Rasyiq03 }`, one plugin entry `{ name: web-skills, source: "./", description }`.
- `LICENSE`: MIT, `Copyright (c) 2026 Rasyiq03`.
- `README.md`: requirements (Python 3.11+ reachable as `python`, Node.js LTS), install
  commands, an example prompt, where results go, the one-time first-run install (needs
  internet, about a minute), the dependency cache location and how to delete it, and the
  development flow below.

Skills appear as `web-skills:web-build` and `web-skills:web-design`.

**Development flow.** The maintainer adds the working copy as a local marketplace
(`/plugin marketplace add D:\Project\dkills\web-skills\web-skills`) and installs from it.
A plugin from a local-path marketplace loads in place, so edits apply without copying.
`.claude/skills/` copies are no longer used for Claude Code; together with the plugin they
would list every skill twice.

**Related fix.** `package.json` `scripts.setup` becomes `npm ci`. Today it runs
`npm install -D prettier eslint …` without versions, which installs the latest releases
and overwrites the pinned versions.

## 2. `run.py` and dependencies

### Interface

`skills/web-build/scripts/run.py <command> [args…]`

- `<command>` is one of the nine scripts (`validate_brief`, `gaps`, `serve`,
  `pick_direction`, `compile_tokens`, `scaffold`, `context`, `check`, `handoff`) or the
  subcommand `path` (section 3). Anything else exits 1 and lists the valid names.
- Output contract unchanged: setup progress lines come first, the script's own output
  follows, and the `NEXT:` line stays last.
- The scripts can still be run directly (tests, development); `run.py` adds dependency
  setup and nothing else.

### Steps on every call

1. **Python version.** Below 3.11 → exit 1, message names the version found.
2. **Python packages.** If `yaml`, `jsonschema`, `bs4`, and `tinycss2` are importable
   (`importlib.util.find_spec`), use them. Otherwise use
   `<cache>/py-<major.minor>-<hash of requirements.txt>/`, installing it first if absent
   with `python -m pip install --target <tmp> -r requirements.txt`, and prepend it to
   `sys.path`.
3. **Node tools.** If the repository's `node_modules/` holds every package named in
   `package.json` (`dependencies` and `devDependencies`), use it. Otherwise use
   `<cache>/node-<hash of package-lock.json>/node_modules`, installing it first if absent:
   copy `package.json` and `package-lock.json` into `<tmp>` and run `npm ci` there. `npm`
   and `node` are located with `shutil.which` (on Windows `npm` is `npm.cmd`). The chosen
   folder is exported as `PD_NODE_MODULES`.
4. **Dispatch.** Set `sys.argv` and run the script with `runpy.run_path(…,
   run_name="__main__")` in the same process. `run.py` lives in `scripts/`, so
   `sys.path[0]` is already the scripts folder that `from lib import …` needs.

### Lint configs next to the Node tools

`config/eslint.config.js` imports its plugins, and `config/.stylelintrc.json` names
`stylelint-order`; both resolve from the config file's own location. In an installed
plugin, `config/` sits in the plugin folder and `node_modules` in the cache, so the
imports would fail. `node_tools.lint_config(name)` returns the config to pass to the
linter: `config/<name>` itself when the `node_modules` in use sits in one of its
ancestors (development), otherwise a fresh copy at `<node_modules>/../config/<name>`, from
where the plugins resolve. `check.py` uses it for ESLint and stylelint on every run, so a
plugin update that changes a config takes effect even when the lock file did not change.

Hashes are the first 12 hex characters of SHA-256. A plugin update that changes
`requirements.txt` or `package-lock.json`, or a different Python version, gets a fresh
cache folder automatically. Old folders are not removed automatically; the README says
how to delete the cache.

### Cache location

`PD_CACHE_DIR` if set; else `%LOCALAPPDATA%\web-skills` on Windows; else
`$XDG_CACHE_HOME/web-skills`, falling back to `~/.cache/web-skills`.

### Install safety

Each install goes into `<final>.tmp-<pid>` and is renamed to its final name only after
the installer exits 0. A final folder that exists is complete by construction. If the
rename fails because another process finished first, the temporary folder is deleted and
the existing one is used.

### Failures

No internet, `npm` or `node` missing, `pip` missing, or a non-zero installer exit →
exit 1 with the installer's last lines and a `NEXT:` line telling the agent which tool the
user must install before running the same command again.

### Units

- `lib/deps.py`: `cache_root()`, `ensure_python_packages(repo_root, cache)`,
  `ensure_node_tools(repo_root, cache)`. Each returns the folder in use or raises
  `ScriptExit`. They take explicit paths so tests can point them at a stand-in repository.
- `run.py`: argument check, calls into `deps`, dispatch, `path` subcommand.
- `run.py` and `lib/deps.py` run before the packages exist, so they import only the
  standard library, `lib.paths`, and `lib.report` (the two `lib` modules with no
  third-party imports). `deps.py` reads `package.json` with `json`, not `lib.io`.

### Changes in `lib/paths.py`

- `REPO_ROOT` = the first ancestor of `paths.py` that contains `audit/anti-slop.yaml` and
  `config/eslint.config.js`; none found → `RuntimeError` naming the start folder. Today it
  is "exactly four levels up", which points at `.agents/` for the Codex copy in
  `.agents/skills/web-build/`, so `config/` and `audit/` are not found there.
- `NODE_MODULES` (a constant read at import) becomes `node_modules_dir()`, which returns
  `PD_NODE_MODULES` when set, else `REPO_ROOT/node_modules`. A function is needed because
  `run.py` imports `lib` before it knows which folder to export. `node_tools.py` and
  `scaffold.py` call the function.

### Changes in `lib/node_tools.py` and `check.py`

- New `lint_config(name)` as described above; `check.py` `eslint_args()` and
  `stylelint_args()` pass its result to `--config`.

## 3. Project location and skill text

### `paths.projects_dir()`

In order:

1. `PD_PROJECTS_DIR` set → that folder (unchanged; the tests rely on it).
2. The current folder is `REPO_ROOT` (development) → `REPO_ROOT/projects`.
3. Otherwise → the current folder, so a site lives at `<folder>/<slug>/`.

### `run.py path <slug>`

Prints `PROJECT: <absolute folder>` and `NEXT: write the project files in that folder`.
Invalid slug → exit 1. Creates nothing. Step 1 of `web-build/SKILL.md` runs it before the
agent writes `brief.yaml`, so the agent never has to apply the rules above itself.

### `skills/web-build/SKILL.md`

- Every `python skills/web-build/scripts/X.py <args>` becomes
  `python "${CLAUDE_PLUGIN_ROOT}/skills/web-build/scripts/run.py" X <args>`, written out in
  full on each step. Claude Code substitutes the variable with the installed path when it
  loads the skill (on Windows with forward slashes).
- Every file reference (`references/…`, `schemas/…`, `site-types/…`, the web-design skill)
  is written as `${CLAUDE_PLUGIN_ROOT}/skills/…`.
- "Run commands from the repository root" becomes "run every command from the folder
  Claude Code was opened in". `projects/<slug>/…` becomes `<project>/…`, the folder printed
  by `run.py path`.
- One fallback sentence for agents that load the file without plugin substitution
  (Codex): if `${CLAUDE_PLUGIN_ROOT}/skills` appears literally, it means the folder that
  contains this skill's folder.

### `skills/web-design/SKILL.md`

The same path changes for `styles/`, `layouts/`, `directions.schema.json`, and
`<project>/brief.yaml`, `<project>/gaps.json`, `<project>/directions.yaml`.

### Other files

- `tools/sync_adapters.py`: Codex only (`.agents/skills/`). It no longer writes
  `.claude/skills/` and warns when that folder still holds a copy of a skill from
  `skills/`.
- `AGENTS.md`: adds the development flow and points to the README.
- `IMPLEMENTATION.md`: §0 (scripts run through `run.py`; the project folder rule), §1
  (layout adds `.claude-plugin/`, `LICENSE`, `README.md`, `docs/`, `run.py`,
  `lib/deps.py`), §2 (project folder rule), §3.10 (`sync_adapters.py` is Codex only).

## 4. Testing and verification

### New and changed pytest tests (written before the code)

- `run.py`: an unknown command exits 1 and lists the valid names;
  `run.py validate_brief kopi-senja` gives the same exit code and `NEXT:` line as the
  script run directly.
- `run.py path`: a current folder outside the repository gives `<folder>/<slug>`; the
  repository root gives `projects/<slug>`; `PD_PROJECTS_DIR` wins over both.
- `lib/deps.py` against a stand-in repository (a temporary folder holding `package.json`,
  `package-lock.json`, and `requirements.txt`, no `node_modules`):
  - `PATH` without `npm` and `node` → `ScriptExit` whose message names Node.js.
  - Marker `network` (not part of a plain `pytest` run, run once before every release):
    a real `npm ci` and `pip install --target` into a temporary `PD_CACHE_DIR`; a second
    call reuses the folder without installing.
- `paths.find_repo_root`: a copy of `skills/web-build/` under `<tmp>/.agents/skills/`
  inside a stand-in repository finds `<tmp>`.
- `node_tools.lint_config`: with the repository's `node_modules` it returns
  `config/<name>`; with `PD_NODE_MODULES` pointing elsewhere it returns an identical copy
  next to that folder.
- Marker `network`, end to end: copy only the files a plugin install contains (no
  `node_modules`, no `.venv`) to a temporary plugin folder, then run every step through that
  copy's `run.py` with `python -S` (no site-packages), a fresh `PD_CACHE_DIR`, and an empty
  working folder; `check.py` reports zero errors.
- Every `${CLAUDE_PLUGIN_ROOT}/<path>` written in either `SKILL.md` exists in the
  repository (placeholders such as `<site_type>` are matched against the folder listing).
- `tests/test_sync_adapters.py` updated: only `.agents/skills/` is written; a stale
  `.claude/skills/<name>` produces a warning.

### Verification before calling the work done

1. `pytest` all green, plus `pytest -m network` once.
2. `claude plugin validate .` passes.
3. New-user simulation: in an empty folder outside the repository, with a fresh
   `PD_CACHE_DIR` and a Python that cannot import the packages, run the whole pipeline
   through `run.py` on the kopi-senja fixtures; `check.py` reports zero errors and the
   result is in `<folder>/kopi-senja/`.

### Left to the maintainer

- Push the repository to GitHub; `/plugin marketplace add rasyiq03/web-dev-skills` reads
  it from there.
- Install from GitHub in a fresh Claude Code session and run one real prompt in an empty
  folder. An interactive session cannot be started from the implementing session.

## Out of scope

- A Codex plugin manifest (`.codex-plugin/plugin.json`): Codex is not installed here, so
  its plugin loading cannot be verified. Codex keeps using `sync_adapters.py`.
- Submission to Anthropic's plugin directory.
- Automatic removal of old dependency cache folders.
- The audit gaps found earlier (`low-contrast` and the others); they stay v0.2 work.

## Risks

- First use needs internet and about a minute; offline first use fails with a clear
  message.
- `pip install --target` needs wheels for the user's Python version; a very new Python
  may lack a wheel for a compiled dependency (`rpds-py`, pulled in by `jsonschema`).
- On Windows, `python` may resolve to the Microsoft Store alias rather than a real
  install; the README names this.
- `claude plugin validate` may not exist in Claude Code 2.1.270, the version installed
  here; if so, verification step 2 is reported as not run rather than passed.
