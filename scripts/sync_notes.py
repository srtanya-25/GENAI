"""
Mirror the Notes/ folder from v0idgy/LPU_GenAI into this repo's
Notes/ folder, converting any non-PDF source file to PDF along the way.

Run by .github/workflows/sync-notes.yml on a schedule.

Safe to re-run: files are only overwritten when their content actually changed.
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
    headers = {
        "Accept": "application/vnd.github+json"
    }

    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    return headers


def list_source_files():
    url = (
        f"https://api.github.com/repos/"
        f"{OWNER}/{REPO}/git/trees/{BRANCH}?recursive=1"
    )

    resp = requests.get(url, headers=api_headers(), timeout=30)
    resp.raise_for_status()

    files = []

    for entry in resp.json()["tree"]:
        if entry["type"] != "blob":
            continue

        path = entry["path"]

        if not (
            path == SRC_PREFIX or
            path.startswith(SRC_PREFIX + "/")
        ):
            continue

        name = pathlib.Path(path).name

        if name in SKIP_NAMES or name.startswith("."):
            continue

        files.append(path)

    return files


def download(path, dest):
    encoded = "/".join(quote(part) for part in path.split("/"))

    url = (
        f"https://raw.githubusercontent.com/"
        f"{OWNER}/{REPO}/{BRANCH}/{encoded}"
    )

    try:
        resp = requests.get(
            url,
            headers=api_headers(),
            timeout=60
        )
        resp.raise_for_status()

        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(resp.content)

    except requests.RequestException as e:
        print(f"Failed to download {path}: {e}", file=sys.stderr)
        raise


def convert_to_pdf(src_file: pathlib.Path,
                   dest_pdf: pathlib.Path) -> bool:

    dest_pdf.parent.mkdir(parents=True, exist_ok=True)

    ext = src_file.suffix.lower()

    # Image -> PDF
    if ext in IMAGE_EXTS:
        from PIL import Image

        try:
            Image.open(src_file).convert("RGB").save(
                dest_pdf,
                "PDF"
            )
            return True

        except Exception as e:
            print(
                f"Could not convert image "
                f"{src_file.name}: {e}",
                file=sys.stderr
            )
            return False

    # LibreOffice conversion
    with tempfile.TemporaryDirectory() as tmp:
        try:
            result = subprocess.run(
                [
                    "soffice",
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    tmp,
                    str(src_file)
                ],
                capture_output=True,
                text=True,
                timeout=180
            )

            produced = pathlib.Path(tmp) / (
                src_file.stem + ".pdf"
            )

            if produced.exists():
                shutil.move(str(produced), dest_pdf)
                return True

            print(
                f"WARN: could not convert "
                f"{src_file.name}: "
                f"{result.stderr.strip()}",
                file=sys.stderr
            )

        except Exception as e:
            print(
                f"Conversion failed for "
                f"{src_file.name}: {e}",
                file=sys.stderr
            )

    return False


def main():
    try:
        files = list_source_files()

    except Exception as e:
        print(
            f"Could not retrieve source files: {e}",
            file=sys.stderr
        )
        sys.exit(1)

    if not files:
        print(
            "Source Notes/ folder is empty "
            "or unreachable; nothing to do."
        )
        return

    changed = []

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_root = pathlib.Path(tmpdir)

        for path in files:
            print(f"Processing: {path}")

            rel = pathlib.Path(path).relative_to(SRC_PREFIX)
            tmp_file = tmp_root / rel

            try:
                download(path, tmp_file)

            except Exception:
                continue

            # Already PDF
            if tmp_file.suffix.lower() == ".pdf":

                dest = DEST_DIR / rel

                is_new = not dest.exists()

                if (
                    is_new or
                    dest.read_bytes() != tmp_file.read_bytes()
                ):
                    dest.parent.mkdir(
                        parents=True,
                        exist_ok=True
                    )

                    shutil.copy2(tmp_file, dest)
                    changed.append(str(dest))

            # Convert to PDF
            else:
                dest = DEST_DIR / rel.with_suffix(".pdf")

                before = (
                    dest.read_bytes()
                    if dest.exists()
                    else None
                )

                if convert_to_pdf(tmp_file, dest):

                    after = dest.read_bytes()

                    if before != after:
                        changed.append(str(dest))

    if changed:
        print(f"\nUpdated {len(changed)} file(s):")

        for file in changed:
            print(f"  - {file}")

    else:
        print("No changes detected.")


if __name__ == "__main__":
    main()
