from ecdsa import SigningKey, VerifyingKey, SECP256k1
import hashlib

def generate_keys():
    private_key = SigningKey.generate(curve=SECP256k1)
    public_key = private_key.get_verifying_key()
    return private_key, public_key

def ecc_encrypt(data_bytes: bytes, public_key: VerifyingKey) -> bytes:
    keystream = hashlib.sha3_256(public_key.to_string()).digest()
    return bytes([b ^ keystream[i % len(keystream)] for i, b in enumerate(data_bytes)])

def ecc_decrypt(data_bytes: bytes, private_key: SigningKey) -> bytes:
    public_key = private_key.get_verifying_key()
    keystream = hashlib.sha3_256(public_key.to_string()).digest()
    return bytes([b ^ keystream[i % len(keystream)] for i, b in enumerate(data_bytes)])
