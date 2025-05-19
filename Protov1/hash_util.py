import hashlib

def get_sha3_hash(data: bytes) -> str:
    """Menghasilkan SHA-3 hash string dari data."""
    sha3 = hashlib.sha3_256()
    sha3.update(data)
    return sha3.hexdigest()

def verify_hash(data: bytes, expected_hash: str) -> bool:
    """Memverifikasi apakah hash data sesuai dengan expected hash."""
    actual_hash = get_sha3_hash(data)
    return actual_hash == expected_hash
