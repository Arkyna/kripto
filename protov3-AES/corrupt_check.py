# corruption_check.py
with open("debug/encrypted_payload.bin", "rb") as f1, open("debug/extracted_payload.bin", "rb") as f2:
    enc = f1.read()
    ext = f2.read()

min_len = min(len(enc), len(ext))
diffs = [(i, enc[i], ext[i]) for i in range(min_len) if enc[i] != ext[i]]

print(f"Encrypted length: {len(enc)}")
print(f"Extracted length: {len(ext)}")
print(f"Corrupted bytes: {len(diffs)}")
print("First 10 mismatches:")
for i, b1, b2 in diffs[:10]:
    print(f"  Offset {i}: encrypted=0x{b1:02x}, extracted=0x{b2:02x}")
