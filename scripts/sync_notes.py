"""Mirror the Notes/ folder from v0idgy/LPU_GenAI into this repo's Notes/ folder,
converting any non-PDF source file to PDF along the way.

Run by .github/workflows/sync-notes.yml on a schedule. Safe to re-run: files are
only overwritten when their content actually changed.
"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import quote

import requests

OWNER = "v0idgy"
REPO = "LPU_GenAI"
BRANCH = "main"
SRC_PREFIX = "Notes"
DEST_DIR = pathlib.Path("Notes")

SKIP_NAMES = {".DS_Store", "Thumbs.db", ".gitkeep"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff"}


def api_headers():
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def list_source_files():
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/git/trees/{BRANCH}?recursive=1"
    resp = requests.get(url, headers=api_headers(), timeout=30)
    resp.raise_for_status()
    files = []
    for entry in resp.json()["tree"]:
        if entry["type"] != "blob":
            continue
        path = entry["path"]
        if not (path == SRC_PREFIX or path.startswith(SRC_PREFIX + "/")):
            continue
        name = pathlib.Path(path).name
        if name in SKIP_NAMES or name.startswith("."):
            continue
        files.append(path)
    return files


def download(path, dest):
    encoded = "/".join(quote(part) for part in path.split("/"))
    url = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/{BRANCH}/{encoded}"
    resp = requests.get(url, headers=api_headers(), timeout=60)
    resp.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(resp.content)


def convert_to_pdf(src_file: pathlib.Path, dest_pdf: pathlib.Path) -> bool:
    dest_pdf.parent.mkdir(parents=True, exist_ok=True)
    ext = src_file.suffix.lower()

    if ext in IMAGE_EXTS:
        from PIL import Image

        Image.open(src_file).convert("RGB").save(dest_pdf, "PDF")
        return True

    # LibreOffice handles docx/pptx/xlsx/odt/txt/rtf/csv/md (best-effort) generically.
    with tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run(
            ["soffice", "--headless", "--convert-to", "pdf", "--outdir", tmp, str(src_file)],
            capture_output=True,
            text=True,
            timeout=180,
        )
        produced = pathlib.Path(tmp) / (src_file.stem + ".pdf")
        if produced.exists():
            shutil.move(str(produced), dest_pdf)
            return True
        print(f"  WARN: could not convert {src_file.name}: {result.stderr.strip()}", file=sys.stderr)
        return False


def main():
    files = list_source_files()
    if not files:
        print("Source Notes/ folder is empty or unreachable; nothing to do.")
        return

    changed = []
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_root = pathlib.Path(tmpdir)
        for path in files:
            rel = pathlib.Path(path).relative_to(SRC_PREFIX)
            tmp_file = tmp_root / rel
            download(path, tmp_file)

            if tmp_file.suffix.lower() == ".pdf":
                dest = DEST_DIR / rel
                is_new = not dest.exists()
                if is_new or dest.read_bytes() != tmp_file.read_bytes():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy(tmp_file, dest)
                    changed.append(str(dest))
            else:
                dest = DEST_DIR / rel.with_suffix(".pdf")
                before = dest.read_bytes() if dest.exists() else None
                if convert_to_pdf(tmp_file, dest) and dest.read_bytes() != before:
                    changed.append(str(dest))

    if changed:
        print(f"Updated {len(changed)} file(s):")
        for c in changed:
            print(f"  - {c}")
    else:
        print("No changes detected.")


if __name__ == "__main__":
    main()
