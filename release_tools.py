"""Build clean, integrity-checked ORION releases for a trusted HTTPS host."""
import argparse
import json
import zipfile
from pathlib import Path

from update_installer import allowed_file, inspect_package, sha256
from updater import https_url, version_key


def build(root, output, version, url, notes):
    version_key(version)
    https_url(url)
    root, output = Path(root).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    package = output / ("ORION-" + version + ".zip")
    metadata = {"version": version}
    try:
        current = json.loads((root / "version.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        current = {}
    if isinstance(current, dict) and current.get("version") == version:
        name = current.get("name")
        if isinstance(name, str) and name.strip():
            metadata["name"] = name
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(root.rglob("*")):
            if not file.is_file() or file.is_symlink():
                continue
            name = file.relative_to(root).as_posix()
            if allowed_file(name) and name != "version.json":
                archive.write(file, "ORION/" + name)
        archive.writestr("ORION/version.json", json.dumps(metadata, ensure_ascii=False))
    inspect_package(package, version)
    manifest = {"version": version, "url": url, "sha256": sha256(package),
                "size": package.stat().st_size, "notes": notes[:20000]}
    (output / "latest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return package, output / "latest.json"


def main():
    parser = argparse.ArgumentParser(description="Create an ORION source release and HTTPS manifest")
    parser.add_argument("--version", required=True)
    parser.add_argument("--url", required=True, help="Final HTTPS URL of the release ZIP")
    parser.add_argument("--notes", type=Path, default=Path(__file__).with_name("RELEASE_NOTES_AZ.md"))
    parser.add_argument("--output", type=Path, default=Path("release"))
    args = parser.parse_args()
    for file in build(Path(__file__).parent, args.output, args.version, args.url, args.notes.read_text(encoding="utf-8")):
        print(file)


if __name__ == "__main__":
    main()
