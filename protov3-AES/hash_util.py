import hashlib

def get_sha3_hash(data: bytes) -> str:
    return hashlib.sha3_256(data).hexdigest()

def verify_hash(data: bytes, hash_str: str) -> bool:
    return get_sha3_hash(data) == hash_str
