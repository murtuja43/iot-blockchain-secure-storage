"""ECDSA key generation, signing, and verification.

ECDSA (Elliptic Curve Digital Signature Algorithm) is *asymmetric* cryptography:
each device owns a key PAIR.

  * The PRIVATE key is secret and never leaves the device. It is used to SIGN.
  * The PUBLIC key can be shared freely. Anyone holding it can VERIFY a
    signature, but cannot forge one.

This gives telemetry two guarantees:
  * Authenticity - a valid signature proves the data came from the device that
                   holds the matching private key (only it could have signed).
  * Integrity    - if even one byte of the signed data changes in transit,
                   verification fails.

We use the NIST P-256 curve (SECP256R1) with SHA-256 as the digest: fast,
compact, and widely supported - a good fit for resource-constrained IoT.

Interchange formats (so keys/signatures travel in files and JSON):
  * keys       -> PEM text strings
  * signatures -> hex strings
  * data       -> raw bytes (produce them with ``serialization.serialize``)
"""

from __future__ import annotations

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import ec

# The single curve and digest used for every key and signature in the project.
_CURVE = ec.SECP256R1()
_SIGNATURE_ALGORITHM = ec.ECDSA(hashes.SHA256())


def generate_key_pair() -> tuple[str, str]:
    """Generate a fresh ECDSA key pair.

    Returns ``(private_key_pem, public_key_pem)`` as PEM strings. The private
    PEM stays on the device; the public PEM is registered with the server so it
    can verify that device's signatures.
    """
    private_key = ec.generate_private_key(_CURVE)
    public_key = private_key.public_key()
    return serialize_private_key(private_key), serialize_public_key(public_key)


def serialize_private_key(private_key: ec.EllipticCurvePrivateKey) -> str:
    """Encode a private key object as an unencrypted PKCS#8 PEM string."""
    pem = private_key.private_bytes(
        encoding=crypto_serialization.Encoding.PEM,
        format=crypto_serialization.PrivateFormat.PKCS8,
        encryption_algorithm=crypto_serialization.NoEncryption(),
    )
    return pem.decode("utf-8")


def serialize_public_key(public_key: ec.EllipticCurvePublicKey) -> str:
    """Encode a public key object as a SubjectPublicKeyInfo PEM string."""
    pem = public_key.public_bytes(
        encoding=crypto_serialization.Encoding.PEM,
        format=crypto_serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return pem.decode("utf-8")


def load_private_key(private_key_pem: str) -> ec.EllipticCurvePrivateKey:
    """Load a private key object from a PEM string."""
    return crypto_serialization.load_pem_private_key(
        private_key_pem.encode("utf-8"), password=None
    )


def load_public_key(public_key_pem: str) -> ec.EllipticCurvePublicKey:
    """Load a public key object from a PEM string."""
    return crypto_serialization.load_pem_public_key(public_key_pem.encode("utf-8"))


def sign(private_key_pem: str, data: bytes) -> str:
    """Sign ``data`` with a private key (PEM) and return the signature as hex.

    The library hashes ``data`` with SHA-256 internally, then produces a DER-
    encoded ECDSA signature, which we hex-encode for easy storage/transmission.
    """
    private_key = load_private_key(private_key_pem)
    signature = private_key.sign(data, _SIGNATURE_ALGORITHM)
    return signature.hex()


def verify(public_key_pem: str, data: bytes, signature_hex: str) -> bool:
    """Verify a hex signature over ``data`` using a public key (PEM).

    Returns ``True`` only if the signature is valid for exactly this data and
    this key. Every failure mode - wrong key, altered data, malformed signature
    - is caught and reported as ``False`` rather than raising, so callers get a
    simple boolean to branch on.
    """
    try:
        public_key = load_public_key(public_key_pem)
        signature = bytes.fromhex(signature_hex)
        public_key.verify(signature, data, _SIGNATURE_ALGORITHM)
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False
