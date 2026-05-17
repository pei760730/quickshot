#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JWT / RSA 認證（手作，不依賴外部套件）。
"""

import json
import time
import base64
import hashlib
import ssl
import urllib.request
import urllib.parse

from .config import CREDENTIALS_PATH


def b64url_encode(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def load_credentials():
    with open(CREDENTIALS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_pem_key(pem_text):
    lines = pem_text.strip().split("\n")
    der_lines = [line for line in lines if not line.startswith("-----")]
    return base64.b64decode("".join(der_lines))


def bytes_to_int(b):
    return int.from_bytes(b, byteorder="big")


def int_to_bytes(n, length):
    return n.to_bytes(length, byteorder="big")


def parse_asn1(data, offset=0):
    offset += 1  # tag
    length = data[offset]
    offset += 1
    if length & 0x80:
        nb = length & 0x7F
        length = bytes_to_int(data[offset:offset + nb])
        offset += nb
    return data[offset:offset + length], offset + length


def extract_rsa_d(der):
    # PKCS#8: SEQUENCE { version, algorithmIdentifier, privateKey(OCTET STRING) }
    seq_content, _ = parse_asn1(der, 0)
    pos = 0
    _, pos = parse_asn1(seq_content, pos)   # version
    _, pos = parse_asn1(seq_content, pos)   # algorithmIdentifier
    pk_content, _ = parse_asn1(seq_content, pos)  # privateKey OCTET STRING
    # pk_content is RSA PKCS#1: SEQUENCE { version, n, e, d, p, q, dp, dq, qinv }
    rsa_seq, _ = parse_asn1(pk_content, 0)
    pos = 0
    comps = []
    for _ in range(9):
        c, pos = parse_asn1(rsa_seq, pos)
        comps.append(bytes_to_int(c))
    return comps[1], comps[3]  # n, d


def rsa_sign_sha256(msg_bytes, pem_key):
    der = parse_pem_key(pem_key)
    n, d = extract_rsa_d(der)
    k = (n.bit_length() + 7) // 8
    digest = hashlib.sha256(msg_bytes).digest()
    prefix = bytes([0x30,0x31,0x30,0x0d,0x06,0x09,0x60,0x86,
                    0x48,0x01,0x65,0x03,0x04,0x02,0x01,0x05,0x00,0x04,0x20])
    T = prefix + digest
    ps = b"\xff" * (k - len(T) - 3)
    em = b"\x00\x01" + ps + b"\x00" + T
    s = pow(bytes_to_int(em), d, n)
    return int_to_bytes(s, k)


def get_access_token(creds):
    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    claim = {
        "iss":   creds["client_email"],
        "scope": "https://www.googleapis.com/auth/spreadsheets",
        "aud":   "https://oauth2.googleapis.com/token",
        "iat":   now, "exp": now + 3600,
    }
    seg = b64url_encode(json.dumps(header)) + "." + b64url_encode(json.dumps(claim))
    sig = rsa_sign_sha256(seg.encode("ascii"), creds["private_key"])
    jwt = seg + "." + b64url_encode(sig)
    data = urllib.parse.urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": jwt,
    }).encode("ascii")
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token", data=data, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, context=ctx) as r:
        return json.loads(r.read().decode())["access_token"]
