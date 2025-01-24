# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

import _awscrt
from awscrt import NativeResource
from typing import Union
from enum import IntEnum


class Hash:

    def __init__(self, native_handle):
        """
        don't call me, I'm private
        """
        self._hash = native_handle

    @staticmethod
    def sha1_new():
        """
        Creates a new instance of Hash, using the sha1 algorithm
        """
        return Hash(native_handle=_awscrt.sha1_new())

    @staticmethod
    def sha256_new():
        """
        Creates a new instance of Hash, using the sha256 algorithm
        """
        return Hash(native_handle=_awscrt.sha256_new())

    @staticmethod
    def md5_new():
        """
        Creates a new instance of Hash, using the md5 algorithm.
        """
        return Hash(native_handle=_awscrt.md5_new())

    def update(self, to_hash):
        _awscrt.hash_update(self._hash, to_hash)

    def digest(self, truncate_to=0):
        return _awscrt.hash_digest(self._hash, truncate_to)


class HMAC:
    def __init__(self, native_handle):
        """
        don't call me, I'm private
        """
        self._hmac = native_handle

    @staticmethod
    def sha256_hmac_new(secret_key):
        """
        Creates a new instance of HMAC, using SHA256 HMAC as the algorithm and secret_key as the secret
        """
        return HMAC(native_handle=_awscrt.sha256_hmac_new(secret_key))

    def update(self, to_hmac):
        _awscrt.hmac_update(self._hmac, to_hmac)

    def digest(self, truncate_to=0):
        return _awscrt.hmac_digest(self._hmac, truncate_to)


class RSAEncryptionAlgorithm(IntEnum):
    """RSA Encryption Algorithm"""

    PKCS1_5 = 0
    """
    PKCSv1.5 padding
    """

    OAEP_SHA256 = 1
    """
    OAEP padding with sha256 hash function
    """

    OAEP_SHA512 = 2
    """
    OAEP padding with sha512 hash function
    """


class RSASignatureAlgorithm(IntEnum):
    """RSA Encryption Algorithm"""

    PKCS1_5_SHA256 = 0
    """
    PKCSv1.5 padding with sha256 hash function
    """

    PKCS1_5_SHA1 = 1
    """
    PKCSv1.5 padding with sha1 hash function
    """

    PSS_SHA256 = 2
    """
    PSS padding with sha256 hash function
    """


class RSA(NativeResource):
    def __init__(self, binding):
        super().__init__()
        self._binding = binding

    @staticmethod
    def new_private_key_from_pem_data(pem_data: Union[str, bytes, bytearray, memoryview]) -> 'RSA':
        """
        Creates a new instance of private RSA key pair from pem data.
        Raises ValueError if pem does not have private key object.
        """
        return RSA(binding=_awscrt.rsa_private_key_from_pem_data(pem_data))

    @staticmethod
    def new_public_key_from_pem_data(pem_data: Union[str, bytes, bytearray, memoryview]) -> 'RSA':
        """
        Creates a new instance of public RSA key pair from pem data.
        Raises ValueError if pem does not have public key object.
        """
        return RSA(binding=_awscrt.rsa_public_key_from_pem_data(pem_data))

    @staticmethod
    def new_private_key_from_der_data(der_data: Union[bytes, bytearray, memoryview]) -> 'RSA':
        """
        Creates a new instance of private RSA key pair from der data.
        Expects key in PKCS1 format.
        Raises ValueError if pem does not have private key object.
        """
        return RSA(binding=_awscrt.rsa_private_key_from_der_data(der_data))

    @staticmethod
    def new_public_key_from_der_data(der_data: Union[bytes, bytearray, memoryview]) -> 'RSA':
        """
        Creates a new instance of public RSA key pair from der data.
        Expects key in PKCS1 format.
        Raises ValueError if pem does not have public key object.
        """
        return RSA(binding=_awscrt.rsa_public_key_from_der_data(der_data))

    def encrypt(self, encryption_algorithm: RSAEncryptionAlgorithm,
                plaintext: Union[bytes, bytearray, memoryview]) -> bytes:
        """
        Encrypts data using a given algorithm.
        """
        return _awscrt.rsa_encrypt(self._binding, encryption_algorithm, plaintext)

    def decrypt(self, encryption_algorithm: RSAEncryptionAlgorithm,
                ciphertext: Union[bytes, bytearray, memoryview]) -> bytes:
        """
        Decrypts data using a given algorithm.
        """
        return _awscrt.rsa_decrypt(self._binding, encryption_algorithm, ciphertext)

    def sign(self, signature_algorithm: RSASignatureAlgorithm,
             digest: Union[bytes, bytearray, memoryview]) -> bytes:
        """
        Signs data using a given algorithm.
        Note: function expects digest of the message, ex sha256
        """
        return _awscrt.rsa_sign(self._binding, signature_algorithm, digest)

    def verify(self, signature_algorithm: RSASignatureAlgorithm,
               digest: Union[bytes, bytearray, memoryview],
               signature: Union[bytes, bytearray, memoryview]) -> bool:
        """
        Verifies signature against digest.
        Returns True if signature matches and False if not.
        """
        return _awscrt.rsa_verify(self._binding, signature_algorithm, digest, signature)
