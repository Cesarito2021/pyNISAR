"""Seekable, budget-limited HTTPS ranges for HDF5; never fall back to a full GET."""
from collections import OrderedDict
import io
import re


class RemoteFile(io.RawIOBase):
    """Read byte ranges through an authenticated requests-compatible session.

    max_bytes limits response-body bytes requested per instance, including cache
    misses. Network headers, redirects and TLS overhead are not included. A server
    that ignores Range is rejected before its response body is consumed.
    """
    def __init__(self, url, session, *, max_bytes=128*1024**2, block_size=1024**2):
        super().__init__()
        if not url.startswith('https://') or max_bytes < block_size or block_size < 1:
            raise ValueError('Use HTTPS and a positive byte budget >= block_size.')
        self.url, self.session = url, session
        self.max_bytes, self.block_size = max_bytes, block_size
        self.bytes_read, self.position, self.size = 0, 0, None
        self.cache = OrderedDict()
        self._block(0)

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        self._checkClosed()
        if whence not in (0, 1, 2):
            raise ValueError('Invalid seek origin.')
        position = offset + (0 if whence == 0 else self.position if whence == 1 else self.size)
        if position < 0:
            raise ValueError('Negative seek position.')
        self.position = position
        return position

    def _block(self, index):
        if index in self.cache:
            self.cache.move_to_end(index)
            return self.cache[index]
        start = index*self.block_size
        stop = min(start+self.block_size, self.size or start+self.block_size)-1
        count = stop-start+1
        if self.bytes_read+count > self.max_bytes:
            raise OSError('Remote byte budget reached; no full-file download attempted.')
        headers = {'Range': f'bytes={start}-{stop}', 'Accept-Encoding': 'identity'}
        with self.session.get(self.url, headers=headers, stream=True, timeout=45) as response:
            if response.status_code != 206:
                raise OSError(f'Expected HTTP 206 byte range; received {response.status_code}.')
            match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', response.headers.get('Content-Range', ''))
            if not match:
                raise OSError('Missing or invalid Content-Range.')
            first, last, total = map(int, match.groups())
            if first != start or last != min(stop, total-1) or (self.size is not None and self.size != total):
                raise OSError('Unexpected range or changing remote file size.')
            self.size = total
            data = response.raw.read(last-first+2)
            self.bytes_read += len(data)
            if len(data) != last-first+1:
                raise OSError('Truncated or oversized range response.')
        self.cache[index] = data
        while len(self.cache) > 128:
            self.cache.popitem(last=False)
        return data

    def read(self, size=-1):
        self._checkClosed()
        size = max(0, self.size-self.position) if size is None or size < 0 else size
        size = min(size, max(0, self.size-self.position))
        if size > self.max_bytes:
            raise OSError('Read request exceeds the remote byte budget.')
        chunks = []
        while size:
            index, offset = divmod(self.position, self.block_size)
            data = self._block(index)
            part = data[offset:offset+size]
            chunks.append(part)
            self.position += len(part)
            size -= len(part)
        return b''.join(chunks)

    def readinto(self, buffer):
        data = self.read(len(buffer))
        buffer[:len(data)] = data
        return len(data)

    def close(self):
        self.cache.clear()
        super().close()


def open_remote(url, *, session=None, max_mb=128):
    """Open a seekable NASA HTTPS file after Catalog.login(), with a body-byte cap."""
    if session is None:
        import earthaccess
        session = earthaccess.get_requests_https_session()
    return RemoteFile(url, session, max_bytes=int(max_mb*1024**2))
