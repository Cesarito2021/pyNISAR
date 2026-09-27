import io
import pytest
from pynisar.remote import RemoteFile


class Session:
    def __init__(self, data, status=206):
        self.data, self.status, self.calls = data, status, 0

    def get(self, url, *, headers, stream, timeout):
        self.calls += 1
        first, last = map(int, headers['Range'][6:].split('-'))
        data = self.data[first:last+1]
        response = type('Response', (), {'status_code': self.status,
            'headers': {'Content-Range': f'bytes {first}-{first+len(data)-1}/{len(self.data)}'},
            'raw': io.BytesIO(data), '__enter__': lambda self: self,
            '__exit__': lambda *args: None})()
        return response


def test_ranges_cache_budget_and_no_full_get():
    session = Session(bytes(range(100)))
    with RemoteFile('https://example.org/data.h5', session, max_bytes=32, block_size=16) as f:
        assert f.read(5) == bytes(range(5))
        f.seek(14)
        assert f.read(5) == bytes(range(14, 19))
        f.seek(0); assert f.read(3) == bytes(range(3))
        assert session.calls == 2 and f.bytes_read == 32
        f.seek(40)
        with pytest.raises(OSError, match='budget'):
            f.read(1)
    with pytest.raises(OSError, match='206'):
        RemoteFile('https://example.org/data.h5', Session(b'hello', 200), block_size=16)


def test_hdf5_random_access(tmp_path):
    import h5py
    import numpy as np
    path = tmp_path/'data.h5'
    with h5py.File(path, 'w') as h:
        h['samples'] = np.arange(200).reshape(20, 10)
    session = Session(path.read_bytes())
    with RemoteFile('https://example.org/data.h5', session, block_size=512) as f:
        with h5py.File(f, 'r') as h:
            np.testing.assert_array_equal(h['samples'][3:5, 2:4], [[32, 33], [42, 43]])
