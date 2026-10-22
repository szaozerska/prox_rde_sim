"""Verify and preserve a small native-run artifact returned by Modal."""
import argparse
import base64
import hashlib
import io
import json
import tarfile
from pathlib import Path


def collect(source: Path, destination: Path) -> dict:
    record = json.loads(source.read_text())
    raw = base64.b64decode(record.pop('artifact_tar_gz_base64'), validate=True)
    if hashlib.sha256(raw).hexdigest() != record['artifact_sha256']:
        raise ValueError('Native artifact checksum mismatch')
    destination.mkdir(parents=True, exist_ok=False)
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
        archive.extractall(destination, filter='data')
    (destination/'transport_manifest.json').write_text(json.dumps(record, indent=2)+'\n')
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    print(json.dumps(collect(args.source, args.destination), indent=2))
