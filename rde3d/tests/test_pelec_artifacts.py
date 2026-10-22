"""A remote success flag must not bypass native artifact integrity checks."""
import base64
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

from tools.pelec.collect_result import collect


class PeleCArtifactTests(unittest.TestCase):
    def record(self, root, name='run/result.json'):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
            content=b'{"status":"installation_smoke_failed"}'
            info=tarfile.TarInfo(name)
            info.size=len(content)
            archive.addfile(info,io.BytesIO(content))
        raw=buffer.getvalue()
        record={'status':'installation_smoke_failed',
                'artifact_sha256':hashlib.sha256(raw).hexdigest(),
                'artifact_tar_gz_base64':base64.b64encode(raw).decode()}
        source=root/'response.json'
        source.write_text(json.dumps(record))
        return source,record

    def test_preserves_failed_run_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            source,_=self.record(root)
            output=root/'evidence'
            result=collect(source,output)
            self.assertEqual(result['status'],'installation_smoke_failed')
            self.assertTrue((output/'run/result.json').is_file())
            with self.assertRaises(FileExistsError):
                collect(source,output)

    def test_checksum_failure_creates_no_evidence_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            source,record=self.record(root)
            record['artifact_sha256']='0'*64
            source.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError,'checksum'):
                collect(source,root/'evidence')
            self.assertFalse((root/'evidence').exists())

    def test_path_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            source,_=self.record(root,'../escaped')
            with self.assertRaises(tarfile.FilterError):
                collect(source,root/'evidence')
            self.assertFalse((root/'escaped').exists())
