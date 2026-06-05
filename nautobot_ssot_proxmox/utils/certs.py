"""Certificate handling and parsing"""

import tempfile

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12


def handle_p12_cert(cert_path: str, certificate_passphrase) -> str:
    """Convert a .p12 certificate to a PEM file.

    Returns the path to the PEM file (original or temporary).
    """
    if not cert_path.lower().endswith(".p12"):
        return cert_path

    try:
        with open(cert_path, "rb") as f:
            p12_data = f.read()

        password = certificate_passphrase.encode() if certificate_passphrase else None
        private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
            p12_data, password
        )

        pem_data = b""
        if private_key:
            pem_data += private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        if certificate:
            pem_data += certificate.public_bytes(serialization.Encoding.PEM)
        if additional_certificates:
            for cert in additional_certificates:
                pem_data += cert.public_bytes(serialization.Encoding.PEM)

        # Create a temporary file that will be cleaned up when the adapter is destroyed
        # or when the process ends.
        temp_pem = tempfile.NamedTemporaryFile(delete=False, suffix=".pem")
        temp_pem.write(pem_data)
        temp_pem.close()

        return temp_pem.name
    except Exception as err:
        raise RuntimeError(f"Failed to process .p12 certificate {cert_path}: {err}") from err
