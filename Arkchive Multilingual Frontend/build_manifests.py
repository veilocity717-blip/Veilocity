#!/usr/bin/env python3
from pathlib import Path
import json
import re

ROOT = Path(".").resolve()

def natural_sort_key(text: str):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", text)]

def js_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)

def strip_trailing_version(text: str) -> str:
    return re.sub(r"\sv\d{3}$", "", text, flags=re.IGNORECASE).strip()

def guess_version(folder_name: str) -> str:
    m = re.search(r"\s(v\d{3})$", folder_name, flags=re.IGNORECASE)
    return m.group(1) if m else ""

def title_case_guess(text: str) -> str:
    text = re.sub(r"[_-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return " ".join(word[:1].upper() + word[1:] for word in text.split())

def guess_country_language(folder_name: str):
    name = re.sub(r"^Ark\s+", "", folder_name, flags=re.IGNORECASE)
    name = strip_trailing_version(name)
    pretty = title_case_guess(name)
    return pretty, pretty

def find_flag(files):
    for f in files:
      if f.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif"} and "flag" in f.name.lower():
          return f.name
    return ""

def looks_like_html(name: str) -> bool:
    return name.lower().endswith(".html")

def is_court_file(name: str) -> bool:
    return "court" in name.lower()

def write_archives_js(archive_dirs):
    lines = []
    lines.append("window.VEILOCITY_ARCHIVES = {")
    lines.append("  archives: [")
    for i, p in enumerate(archive_dirs):
        comma = "," if i < len(archive_dirs) - 1 else ""
        lines.append(f"    {js_string(p.name)}{comma}")
    lines.append("  ]")
    lines.append("};")
    output = "\n".join(lines) + "\n"
    (ROOT / "archives.js").write_text(output, encoding="utf-8")
    print(f"Wrote {ROOT / 'archives.js'}")

def write_manifest_js(ark_dir: Path):
    files = sorted([p for p in ark_dir.iterdir() if p.is_file()], key=lambda p: natural_sort_key(p.name))
    file_names = [p.name for p in files]

    html_files = [name for name in file_names if looks_like_html(name)]
    non_court_html = [name for name in html_files if not is_court_file(name)]

    country, language = guess_country_language(ark_dir.name)
    version = guess_version(ark_dir.name)
    flag = find_flag(files)
    primary_html = non_court_html[0] if non_court_html else (html_files[0] if html_files else "")

    manifest = {
        "country": country,
        "language": language,
        "version": version,
        "flag": flag,
        "primary_html": primary_html,
        "description": f"{language} portable archive",
        "files": file_names
    }

    content = []
    content.append("window.VEILOCITY_MANIFESTS = window.VEILOCITY_MANIFESTS || {};")
    content.append(f"window.VEILOCITY_MANIFESTS[{js_string(ark_dir.name)}] = {json.dumps(manifest, ensure_ascii=False, indent=2)};")
    content.append("")

    output_path = ark_dir / "manifest.js"
    output_path.write_text("\n".join(content), encoding="utf-8")
    print(f"Wrote {output_path}")

def build():
    archive_dirs = sorted(
        [p for p in ROOT.iterdir() if p.is_dir() and p.name.lower().startswith("ark ")],
        key=lambda p: natural_sort_key(p.name)
    )

    write_archives_js(archive_dirs)

    for ark_dir in archive_dirs:
        write_manifest_js(ark_dir)

if __name__ == "__main__":
    build()
