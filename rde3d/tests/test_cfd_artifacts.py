"""Native CFD evidence extraction must preserve failures and reject corrupt archives."""
import base64
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from tools.cfd_artifacts import unpack

class NativeArtifactTests(unittest.TestCase):
    def record(self, root, name='case/solver.log'):
        buffer=io.BytesIO()
        with tarfile.open(fileobj=buffer,mode='w:gz') as archive:
            content=b'TIME LIMIT: incomplete run\n';info=tarfile.TarInfo(name);info.size=len(content)
            archive.addfile(info,io.BytesIO(content))
        raw=buffer.getvalue();value=dict(artifact_sha256=hashlib.sha256(raw).hexdigest(),artifact_tar_gz_base64=base64.b64encode(raw).decode())
        path=root/'result.json';path.write_text(json.dumps(value));return path,value

    def test_stream_preserves_failed_log_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp,contextlib.redirect_stdout(io.StringIO()):
            root=Path(tmp);source,_=self.record(root);out=root/'native';unpack(source,out)
            self.assertEqual((out/'case/solver.log').read_bytes(),b'TIME LIMIT: incomplete run\n')
            with self.assertRaises(FileExistsError):unpack(source,out)

    def test_checksum_rejected_before_output_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source,value=self.record(root);value['artifact_sha256']='0'*64;source.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError,'checksum'):unpack(source,root/'native')
            self.assertFalse((root/'native').exists())

    def test_stream_rejects_path_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source,_=self.record(root,'../escaped')
            with self.assertRaises(tarfile.FilterError):unpack(source,root/'native')
            self.assertFalse((root/'escaped').exists())
