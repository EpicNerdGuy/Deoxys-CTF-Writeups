#!/usr/bin/env python3
"""
Automated solver for the GLaDOS Aperture Lights Out CTF.
Connects via raw socket, solves each chamber, submits, loops through all 20.
"""
import socket
import re
import sys
import time

HOST = "162.243.98.234"
PORT = 9000


def solve_lights_out(grid, n):
    size = n * n
    A, b = [], []
    for r in range(n):
        for c in range(n):
            mask = 1 << (r * n + c)
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < n and 0 <= nc < n:
                    mask |= 1 << (nr * n + nc)
            A.append(mask)
            b.append(grid[r][c])

    pivot_row_for_col = {}
    cur = 0
    for col in range(size):
        pivot = next((r for r in range(cur, size) if (A[r] >> col) & 1), None)
        if pivot is None:
            continue
        A[cur], A[pivot] = A[pivot], A[cur]
        b[cur], b[pivot] = b[pivot], b[cur]
        for r in range(size):
            if r != cur and (A[r] >> col) & 1:
                A[r] ^= A[cur]
                b[r] ^= b[cur]
        pivot_row_for_col[col] = cur
        cur += 1
        if cur == size:
            break

    for r in range(cur, size):
        if A[r] == 0 and b[r] == 1:
            raise ValueError("Unsolvable grid, check parsing")

    x = [0] * size
    for col, row in pivot_row_for_col.items():
        x[col] = b[row]

    return [(i // n, i % n) for i in range(size) if x[i]]


def recv_until(sock, buf, markers, timeout=10):
    """Read until any marker string appears in the accumulated buffer, or timeout."""
    sock.settimeout(timeout)
    start = time.time()
    while True:
        if any(m in buf for m in markers):
            return buf
        try:
            chunk = sock.recv(65536)
            if not chunk:
                return buf
            buf += chunk.decode(errors="replace")
        except socket.timeout:
            return buf
        if time.time() - start > timeout:
            return buf


def parse_grid(text):
    m = re.search(r"GRID\s+(\d+)\s*\n((?:[01](?:\s+[01])*\s*\n)+)", text)
    if not m:
        return None, None
    n = int(m.group(1))
    rows_text = m.group(2).strip().splitlines()
    rows_text = rows_text[-n:]
    grid = [[int(x) for x in row.split()] for row in rows_text]
    return grid, n


def main():
    sock = socket.create_connection((HOST, PORT), timeout=15)
    full_buf = ""

    chamber = 0
    while chamber < 20:
        full_buf = recv_until(sock, full_buf, ["AWAITING SOLUTION", "FLAG", "flag{"], timeout=10)
        print(full_buf[len(full_buf) - full_buf[::-1].find("\n--\n"[::-1]) if False else 0:], end="")

        if "flag{" in full_buf.lower() or "FLAG" in full_buf:
            print("\n[+] FLAG FOUND")
            break

        grid, n = parse_grid(full_buf)
        if grid is None:
            print("[-] Could not parse grid, stopping")
            break

        chamber += 1
        presses = solve_lights_out(grid, n)
        print(f"\n[+] Solved chamber {chamber}: {n}x{n} grid, {len(presses)} presses")

        out_lines = [f"PRESSES {len(presses)}"]
        out_lines.extend(f"{r} {c}" for r, c in presses)
        payload = ("\n".join(out_lines) + "\n").encode()
        sock.sendall(payload)

        full_buf = ""  # reset buffer, next recv_until will catch the response to this submission

    # drain whatever's left (flag usually shows right after final OK)
    final = recv_until(sock, "", ["FLAG", "flag{"], timeout=5)
    if final.strip():
        print(final)

    sock.close()


if __name__ == "__main__":
    main()