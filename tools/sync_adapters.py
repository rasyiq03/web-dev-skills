# ============================================================
# File      : sync_adapters.py
# Proyek    : web-skills
# Deskripsi : Sinkronisasi skill ke .agents/skills/ untuk Codex. Claude Code
#             memuat skill lewat plugin, jadi .claude/skills/ tidak ditulis lagi.
# ============================================================

import argparse
import os
import shutil
import sys
from pathlib import Path

# Impor pustaka lib dari skills/web-build/scripts
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "skills" / "web-build" / "scripts"))

import yaml
from lib import paths, report
from lib.report import EXIT_INVALID, fail


def parse_frontmatter(skill_md_path):
    """
    Mengekstrak frontmatter YAML dari file SKILL.md.

    I.S. : skill_md_path file yang ada.
    F.S. : Dict frontmatter dikembalikan.
    """
    content = skill_md_path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return {}
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}
    return yaml.safe_load(parts[1]) or {}


def sync_adapters(copy_mode=False):
    """
    Memeriksa validitas SKILL.md dan membuat tautan/salinan skill di .agents/skills/ (Codex).

    I.S. : Folder skills/ ada di root repo.
    F.S. : .agents/skills/ tersinkronisasi. Peringatan dicetak bila CLAUDE.md ada, dan untuk
           setiap salinan lama di .claude/skills/ yang akan membuat skill muncul dua kali di
           samping plugin.
    """
    skills_dir = REPO_ROOT / "skills"
    if not skills_dir.is_dir():
        fail(EXIT_INVALID, "Folder skills/ tidak ditemukan di root repo.", "ensure skills directory exists")

    lines = []

    # Cek keberadaan CLAUDE.md
    claude_md = REPO_ROOT / "CLAUDE.md"
    if claude_md.is_file():
        lines.append("PERINGATAN: CLAUDE.md ditemukan! Claude Code akan mengabaikan AGENTS.md bila file ini ada.")

    agents_skills_dir = REPO_ROOT / ".agents" / "skills"

    agents_skills_dir.mkdir(parents=True, exist_ok=True)

    skill_folders = [d for d in skills_dir.iterdir() if d.is_dir()]

    for s_dir in skill_folders:
        s_name = s_dir.name
        skill_md = s_dir / "SKILL.md"
        if not skill_md.is_file():
            fail(EXIT_INVALID, f"Skill {s_name} tidak memiliki SKILL.md.", f"add SKILL.md in skills/{s_name}/")

        meta = parse_frontmatter(skill_md)
        meta_name = meta.get("name")
        meta_desc = meta.get("description", "")

        if meta_name != s_name:
            fail(
                EXIT_INVALID,
                f"Nama frontmatter SKILL.md ({meta_name!r}) tidak sama dengan folder ({s_name!r}).",
                f"set name: {s_name} in skills/{s_name}/SKILL.md",
            )

        if len(meta_desc) >= 1024:
            fail(
                EXIT_INVALID,
                f"Deskripsi skill {s_name} melebihi 1.024 karakter ({len(meta_desc)} karakter).",
                f"shorten description in skills/{s_name}/SKILL.md to under 1024 chars",
            )

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

    summary_lines = [
        "Sinkronisasi adapter selesai:",
        f"  - {len(skill_folders)} skill diverifikasi (frontmatter name dan deskripsi < 1024 karakter)",
    ] + lines

    return summary_lines, "adapters synced"


def main():
    """
    Titik masuk CLI: membaca opsi --copy dari argumen lalu menjalankan sync_adapters().

    I.S. : sys.argv berisi opsi baris perintah.
    F.S. : Hasil sync_adapters() dikembalikan.
    """
    parser = argparse.ArgumentParser(description="Sinkronisasi skill ke .agents/skills/ untuk Codex.")
    parser.add_argument("--copy", action="store_true", help="Salin folder sebagai ganti relative symlink")

    args = parser.parse_args()
    return sync_adapters(copy_mode=args.copy)


if __name__ == "__main__":
    report.run(main)
