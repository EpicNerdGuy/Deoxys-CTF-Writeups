from pwn import *
import re

HOST = "mysterious-sea.picoctf.net"
PORT = 65401

r = remote(HOST, PORT)

for i in range(20):
    
    r.recvuntil(b"Here's the next binary in bytes:\n")
    hex_blob = r.recvline().strip()

    binary = bytes.fromhex(hex_blob.decode())

    sig = b"\xc7\x45\xfc"

    idx = binary.find(sig)
    if idx == -1:
        log.failure("Signature not found")
        exit()

    secret_bytes = binary[idx+3:idx+7]
    secret = u32(secret_bytes)

    log.success(f"Secret {i+1}: {secret}")

    r.recvuntil(b"What's the secret?")
    r.sendline(str(secret).encode())

print(r.recvall().decode())