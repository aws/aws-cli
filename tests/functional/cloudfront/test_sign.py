# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import base64
import hashlib
import json
import re

from awscrt.crypto import EC, RSA, RSASignatureAlgorithm
from botocore.compat import parse_qs, urlparse
from botocore.signers import CloudFrontSigner
from botocore.utils import parse_to_aware_datetime

from awscli.testutils import BaseAWSCommandParamsTest, FileCreator, mock


def _pem_to_der(pem, label):
    # Decode the body of the PEM block with the given label.
    match = re.search(
        rf'-----BEGIN {label}-----(.*?)-----END {label}-----', pem, re.DOTALL
    )
    return base64.b64decode(''.join(match.group(1).split()))


def _url_b64decode(value):
    # Reverse the CloudFront-specific base64 substitutions applied by
    # CloudFrontSigner._url_b64encode.
    restored = value.replace('-', '+').replace('_', '=').replace('~', '/')
    return base64.b64decode(restored)


class TestSign(BaseAWSCommandParamsTest):
    # A private key only for testing purpose.
    private_key = (
        '-----BEGIN RSA PRIVATE KEY-----\n'
        'MIIEowIBAAKCAQEAu6o2+Jc8UINw2P/w2l7A1xXu3emQEZQ9diA3bmog8r9Dg+65\n'
        'fZgAqmuNWPqBivv7j3DGnLUdt8uCIr7PYUbK7wDa6n7U3ryOWtO2ZTc3StiJVcqT\n'
        'sokZ0qxGFtDRafjBuydXtcxh52vVTcHqH33nubyyZIzuhTwfmrIOnUXnLwbMrBBP\n'
        'bg/8mlgQooyo1XbrN1eO4XMs+UgQ9Mqc7KRJRinUJ+KYuCnM8f/nN4RjYdjTcghk\n'
        'xCPEHCeSt2luywWyYmfguWCBS2Mu1q0250wKyNazlgiiTJtAuuSeweb4NKPOJL9X\n'
        'hR6Ce6UuU4WYlli8gvQh3FAV3N3C1Rxo20k28QIDAQABAoIBAQCUEkP5dWrzpCJg\n'
        'NeHWizjg/L9SfT1dgXfVQqo6BqckoeElsjDNdifgT6hhcpbQEO52SWeMsiNWp85w\n'
        'l9mNSYxJdIVGzPgtHt27sJyT1DNebOg/tu0+y4qCfcd3rR/u24YQo4RDP5ZoQN82\n'
        '0TBn1LIIDWk8iS6SFdRh/OgnE8bLhNbK9IfZQFEEJrFkArrn/le/ro2mfJkC/imo\n'
        'QvqKmM0dGBXt5SCDSbUQAzKtEcR/4gf/qSjFe2YAwAvSA05WXMH6szdtx6/H/VbK\n'
        'Uck/WwTHvGObQDFEWmICxPK9AWT0qaFNjlUsi3bjQRdIlYYrXe+6nVMB/Jp1awq7\n'
        'tGBqIcWBAoGBAPtXCNuoQhKXqkjJgteQpB+wFav12XRZgpOciYdeviJrgWydpOOu\n'
        'O9wkiRUctUijRJbUuWCJF7SgYGoT2xTTp/COiOReqs7qXLMuuXCZcPKkMRJj5wmo\n'
        'Uc2AwUV/o3+PNz1NFK+2RgciXplac7qugIyuxIvBKuVFTBlCg0+if/0pAoGBAL8k\n'
        '845wKqOeiawwle/o9lKLGPy1T11GrE6l1A5jRuE1WTVM77jRrb0Hmo0mdfHaf5A0\n'
        'EjXGIX/fjcmQzBrEd78eCUsvI2Bgn6xXwhd4TTyWHGZfoQjFqAGkixuLN1oo2h1g\n'
        'bRreFKfAubFP8MC93z23vnH6tdY2VIA4h5ehUFyJAoGAJqxJrKLDJ+E2TmTTQR/8\n'
        'YPPTIdZ+UyzCrrvTXYTydJFeJLxM9suEYmcswJbePgMBNsQckgIGJ8DVlPzhJN88\n'
        'ZANKhPkcByKAiQGTfwPdITiqZE4C6rV/gMNi+bKeEa6TrVcC69Z8B/T94VLNo9fd\n'
        '58esbmSWmRiEkQ5u7f3u+6ECgYA8+6ANCLJB43nPCu07TpsP+LrvHTWF799XdEa0\n'
        'lG3vuiKNA8/TqmoAziU79VJZ6Dkcm9BXga/8aSmGboD/5UDDI+UZLJ/fxtQKmzEc\n'
        'ZdBWjRnge5AYCV+xrnqHPiJZzIDSMIp+sO3sG2vjKzsHc0x/F1lWagOLpWfORLrV\n'
        '4KyP6QKBgAafeSrfK3LM7idiCBuxckLCgFoHa7uXLUNJRS5iIU+bbZLPj2ozu/tk\n'
        'U0jp7sNk1CyMWI36lR3sujkSyH3lPIXVgrXMuGY3PJRGntN8WlWEsw4VUMGRj3h4\n'
        '5rB+y/UOS+nlEwQ6eOS09GByJDEXOXpcwjFcTr/f7V8mi0jH+gY/\n'
        '-----END RSA PRIVATE KEY-----\n'
    )
    prefix = 'cloudfront sign --key-pair-id my_id --url http://example.com/hi '

    def setUp(self):
        files = FileCreator()
        self.private_key_file = files.create_file('foo.pem', self.private_key)
        self.addCleanup(files.remove_all)
        super().setUp()

    def assertDesiredUrl(self, url, base, params):
        self.assertEqual(len(url.splitlines()), 1, "Expects only 1 line")
        self.assertTrue(url.startswith(base), "URL mismatch")
        url = url.strip()  # Otherwise the last param contains a trailing CRLF
        self.assertEqual(parse_qs(urlparse(url).query), params)

    def test_canned_policy(self):
        cmdline = (
            self.prefix
            + '--private-key file://'
            + self.private_key_file
            + ' --date-less-than 2016-1-1'
        )
        expected_signature = (
            "UiEmtMsInU-gXoa1O7-bTRJmZ~ocphB0ONMxyEHs2r8Y9dwzeB~DkbgzPMX3jbdb"
            "wIwVX3f4VcY4HBLdPSkbF~D6KbUlxPw1ju8mlXeu2C436XxZdrJrrJaiEDaTpKsl"
            "Xpn9ngaCzVfCVPfkC3a0NBWBySi5ezCG2yzb0c-djNgI1wkogwtmtZuOxAoKF1sR"
            "TyFX9ZitUiUIl~65nkJ94s~GGwxzTf1kMi7Wdm~9rFrJpx0O7nJEBy5O578s2UHr"
            "ejtwyedUR5BqXTkgu~A51NcjAN9LErATV7SVBYicoZ76AOfB-TKay7g6-MWCK6-T"
            "-4Q5x6XH4yzII3JpbCmVwA__"
        )
        expected_params = {
            'Key-Pair-Id': ['my_id'],
            'Expires': ['1451606400'],
            'Signature': [expected_signature],
        }
        self.assertDesiredUrl(
            self.run_cmd(cmdline)[0], 'http://example.com/hi', expected_params
        )

    def test_custom_policy(self):
        cmdline = (
            self.prefix
            + '--private-key file://'
            + self.private_key_file
            + ' --date-less-than 2016-1-1 --ip-address 12.34.56.78'
        )
        expected_signature = (
            "Vw-WG18WJJXim7YSGWS-zW~XmFB9MjCDOvgC~2Gz-1wiMQzCrXzYYbSE7-aF6JGO"
            "Ob5ewArpMqmu2g5mohnqgieZX1NY6IOteDoXYgqaNj1DafHWQD6UJ3IKVfkxISU9"
            "OmFPoG7H~VSPWEzOxdjOqdIPvAU2pW2mJ5oWu2aL62s0VVtLGCAm-DahiSQisl0J"
            "bzpPyG1pofvPbT75qc71r9uiqSAbPjUF5nmLCZazVnFjDkj3zIgMRYa5aV54VDa6"
            "-wEizzmjQ3-m6UMoYgcGHQXEjoFIWTfpZvbZBYkmK9lk3d16cgvaHafTJ-CPegn1"
            "bKxfgNEjSAoPWS0OvBkRmg__"
        )
        expected_params = {
            'Key-Pair-Id': ['my_id'],
            'Policy': [mock.ANY],
            'Signature': [expected_signature],
        }
        self.assertDesiredUrl(
            self.run_cmd(cmdline)[0], 'http://example.com/hi', expected_params
        )


class BaseECDSASignTest(BaseAWSCommandParamsTest):
    # Abstract base; concrete subclasses supply an EC private key. Prevents
    # pytest from collecting this base class directly.
    __test__ = False
    # Overridden by subclasses with an EC private key in a specific PEM format.
    private_key = None
    pem_label = None
    url = 'http://example.com/hi'
    prefix = 'cloudfront sign --key-pair-id my_id --url http://example.com/hi '

    def setUp(self):
        files = FileCreator()
        self.private_key_file = files.create_file('foo.pem', self.private_key)
        self.addCleanup(files.remove_all)
        super().setUp()

    def _run_and_parse(self, cmdline):
        url = self.run_cmd(cmdline)[0].strip()
        self.assertEqual(len(url.splitlines()), 1, "Expects only 1 line")
        self.assertTrue(url.startswith(self.url), "URL mismatch")
        return parse_qs(urlparse(url).query)

    def _assert_signature_verifies(self, params, policy):
        # ECDSA signatures are non-deterministic (a random nonce is used), so
        # rather than comparing against a fixed value we verify the signature
        # cryptographically against the policy that was signed.
        self.assertEqual(params['Key-Pair-Id'], ['my_id'])
        # ECDSA signatures are SHA-256; the URL must carry Hash-Algorithm=SHA256
        # so CloudFront's edge verifies with SHA-256 instead of its SHA-1
        # default (otherwise verification fails with AccessDenied).
        self.assertEqual(params['Hash-Algorithm'], ['SHA256'])
        key = EC.new_key_from_der_data(
            _pem_to_der(self.private_key, self.pem_label)
        )
        signature = _url_b64decode(params['Signature'][0])
        digest = hashlib.sha256(policy.encode('utf8')).digest()
        self.assertTrue(
            key.verify(digest, signature),
            "ECDSA signature failed to verify",
        )

    def test_canned_policy(self):
        cmdline = (
            self.prefix
            + '--private-key file://'
            + self.private_key_file
            + ' --date-less-than 2016-1-1'
        )
        params = self._run_and_parse(cmdline)
        self.assertEqual(params['Expires'], ['1451606400'])
        self.assertNotIn('Policy', params)
        # For a canned policy the signed payload is the canned policy that
        # CloudFrontSigner builds internally from the expiration date.
        policy = CloudFrontSigner('my_id', None).build_policy(
            self.url, parse_to_aware_datetime('2016-1-1')
        )
        self._assert_signature_verifies(params, policy)

    def test_custom_policy(self):
        cmdline = (
            self.prefix
            + '--private-key file://'
            + self.private_key_file
            + ' --date-less-than 2016-1-1 --ip-address 12.34.56.78'
        )
        params = self._run_and_parse(cmdline)
        self.assertNotIn('Expires', params)
        # The custom policy is emitted (base64url encoded) in the URL, so the
        # exact signed payload can be recovered and verified against.
        policy = _url_b64decode(params['Policy'][0]).decode('utf8')
        self._assert_signature_verifies(params, policy)


class TestSignECDSASEC1(BaseECDSASignTest):
    __test__ = True
    pem_label = 'EC PRIVATE KEY'
    # An EC (P-256) private key in SEC1 format, only for testing purpose.
    private_key = (
        '-----BEGIN EC PRIVATE KEY-----\n'
        'MHcCAQEEIEJv7Bciy04Q7+wqRyaA2xSCsaHtqPmDIQ5msTzcH1xNoAoGCCqGSM49\n'
        'AwEHoUQDQgAEdPNT3OyY+yjo4dOMWcnmKSeIUzrfH2WHkcfKFm32D9B0/DNP9Coj\n'
        'qIXILIjVsmvtp0ULy/ICJEeZbKxUv1/OjA==\n'
        '-----END EC PRIVATE KEY-----\n'
    )


class TestSignECDSAPKCS8(BaseECDSASignTest):
    __test__ = True
    pem_label = 'PRIVATE KEY'
    # The same EC (P-256) key in PKCS#8 format, only for testing purpose.
    private_key = (
        '-----BEGIN PRIVATE KEY-----\n'
        'MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgQm/sFyLLThDv7CpH\n'
        'JoDbFIKxoe2o+YMhDmaxPNwfXE2hRANCAAR081Pc7Jj7KOjh04xZyeYpJ4hTOt8f\n'
        'ZYeRx8oWbfYP0HT8M0/0KiOohcgsiNWya+2nRQvL8gIkR5lsrFS/X86M\n'
        '-----END PRIVATE KEY-----\n'
    )


class TestSignECDSAUnsupportedCurve(BaseAWSCommandParamsTest):
    # An EC private key on the P-384 curve, which CloudFront does not support.
    private_key = (
        '-----BEGIN EC PRIVATE KEY-----\n'
        'MIGkAgEBBDCIoGBIXHIpvlHWVTT+jka5Jpj1YR5rWIncoxf6VUxxhlHjEI7hqDto\n'
        'FajvDTKH5jSgBwYFK4EEACKhZANiAAT1i0QFJOMXeKxMx4VpZHw6OoKhEOB4nOXk\n'
        'h+Z9dhiQ4H6O2D84WS6ql+iyNIH2qux8jBUju3fc8NdbVwIqyfQZWRRo/Lg5ekDp\n'
        'M7re404ay7JYpiJXlCZP+RBCBn23NZU=\n'
        '-----END EC PRIVATE KEY-----\n'
    )
    prefix = 'cloudfront sign --key-pair-id my_id --url http://example.com/hi '

    def setUp(self):
        files = FileCreator()
        self.private_key_file = files.create_file('foo.pem', self.private_key)
        self.addCleanup(files.remove_all)
        super().setUp()

    def test_non_p256_curve_raises_error(self):
        cmdline = (
            self.prefix
            + '--private-key file://'
            + self.private_key_file
            + ' --date-less-than 2016-1-1'
        )
        _, stderr, _ = self.run_cmd(cmdline, expected_rc=255)
        self.assertIn('Only P-256 EC keys are supported', stderr)


class TestSignUnsupportedKeyType(BaseAWSCommandParamsTest):
    # A key whose PEM header is neither RSA, EC, nor PKCS#8 "PRIVATE KEY".
    private_key = (
        '-----BEGIN OPENSSH PRIVATE KEY-----\n'
        'b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtz\n'
        '-----END OPENSSH PRIVATE KEY-----\n'
    )
    prefix = 'cloudfront sign --key-pair-id my_id --url http://example.com/hi '

    def setUp(self):
        files = FileCreator()
        self.private_key_file = files.create_file('foo.pem', self.private_key)
        self.addCleanup(files.remove_all)
        super().setUp()

    def test_unsupported_key_type_raises_error(self):
        cmdline = (
            self.prefix
            + '--private-key file://'
            + self.private_key_file
            + ' --date-less-than 2016-1-1'
        )
        _, stderr, _ = self.run_cmd(cmdline, expected_rc=255)
        self.assertIn('Unsupported key type', stderr)


class TestSignPKCS8(BaseAWSCommandParamsTest):
    # A private key only for testing purpose.
    private_key = (
        '-----BEGIN PRIVATE KEY-----\n'
        'MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDiVR5JIogE3iKq\n'
        'buYalyKO3vmRnOxf7OU6/8WPma8wpWltb4d67HRBxeUvNugGq0uwinoPDfwF74zG\n'
        'hOKeGrDPLVAbekPzYv1SnB/ppy+nvojDew72xgW56ii9X+Jk83f0TGNTmC7sBvcc\n'
        'kqz3T/aX23NU0faCW5bl6fiW+HVUHZe/aE4nHqhorHiDXlvTV6wpjEWS6Xyf7ll+\n'
        'Jvf4eXg7GqTGTGKsB0jE/xPKdVbnQD67fkJOdaAKTQKanY1UF2SS5Nx6NcBxbcCR\n'
        'Va4myn1JOeQDyHcIXb4NmBx3m21eJSotrJYmD9LTs16mB4wi21lvimALwKxZHjvV\n'
        'p58xKyyJAgMBAAECggEAFtKPdb96KMd/hmEdaeQAk5iPYOwKd9fK+6qL8OGF5Wlg\n'
        'mqzq4+3RAUrjw+GM/xMp1Dj6euclmTGhJ+mBcoDtgE6o68Rl8rZyJfDhVO3LY+ZW\n'
        'IyQXC7JHJIqkpgfzq8tTNrq3L1hCrwE6zNJLh7qz+nciB5UOfvGeYzu3Gf4e0qbi\n'
        'rlStPa7Gi4Oc0EO/51YRjU3IpXjFRvcsqBtV95XA96hPo2ice0KMcrWPF9Kai8bQ\n'
        '0sE+wv+YbgIsbwmnHntdd7Sfxx2jPjXeEgh/ncoXCMYfQueSAHQ/EQBWkofhUeB5\n'
        'oEuQlS5b3D1t3aSKr2o7vrMtu1UWhabu0u+Db/r6gQKBgQD7DKJk0Ow2JBaoM7vV\n'
        'UucuLWLaY4MG4a1YDlHPl6zmD1OioKrQw2h/m2SalYfxM8BjPbR9eesyDv55HQnR\n'
        'ptC1SBNxH7dCwWqCeD1jNVoJP8VkBDPRiNaLz68wYkrtfiXCa0DYbewbdrEFDaIk\n'
        'IErrRzxSWTSNE8Y1YA3ka6MiaQKBgQDmy7TdLa0tyYwY30DmLmS4WUZglJZKrT/0\n'
        'd9UTz7KJek7P9BNZAe8yotVrxO2di+8W85GAVQBexeISrEW6ZK6GHGz949fJmbvq\n'
        'QOU/6TgE01AL0nUZF2QKbdAleonlR/WB9IpZTQf/ZI1HmUV0QL3nCrs9OoFbzx4E\n'
        'GfjbCmQ1IQKBgFOlZgZJRirT42ivtAnj0XslTCaPuXx1fRg1zTRpyQXuXWN2PPPJ\n'
        '5+t8jwyifeTz5UorqROVp7PKIyefcUIVXrzIAxJSCvGHGEHYZjvD7vfd85rbe5h5\n'
        'C2MSE8D/Pw/aVCJvMe/q0Bxmc5zHahq3V78EwSh+6G+JAyWNl5Nf+b7hAoGBAM1Z\n'
        'PGB7DpYpuLw8j9r+NmGMFUFDk4F4KupSYMTSzPDjYRJIAZr1TKWKGkhcHGtMIXwT\n'
        'VUeQ2dZ5TM/+dcAFav8qdZNk0Q+v+HHSMeeuk0g/1/3c0JF1rW5WDJf8MotNflSV\n'
        'hy8zicUj60xkRFbOb+kNNFGjJ4vPec5+aVxDH6vhAoGBAI3RsJZXYUL9PhakrsVp\n'
        '71N+JbNxvw8L9b2VL6ecLNMtPcG5ddFaMhc+kQZap6vAZXauft1fzvAO3fMKNJXm\n'
        'yvtM2CEYzVd8lFqA8xETa/FgelkFjB5gkiq4EDIuX6mFStkskKUfRHHrb0ATKHSl\n'
        'YvT60qFc4be2Mfyzt+CuGhYi\n'
        '-----END PRIVATE KEY-----\n'
    )
    prefix = 'cloudfront sign --key-pair-id my_id --url http://example.com/hi '

    def setUp(self):
        files = FileCreator()
        self.private_key_file = files.create_file('foo.pem', self.private_key)
        self.addCleanup(files.remove_all)
        super().setUp()

    def assertDesiredUrl(self, url, base, params):
        self.assertEqual(len(url.splitlines()), 1, "Expects only 1 line")
        self.assertTrue(url.startswith(base), "URL mismatch")
        url = url.strip()  # Otherwise the last param contains a trailing CRLF
        self.assertEqual(parse_qs(urlparse(url).query), params)

    def test_canned_policy(self):
        cmdline = (
            self.prefix
            + '--private-key file://'
            + self.private_key_file
            + ' --date-less-than 2016-1-1'
        )
        expected_signature = (
            "cIOcUXezjLknta66EiRX7rk3viXv20F01OwZa1X2QWxhnWnBVno~mg0Gcyfzvfgo"
            "-oXCvZC3bdsfTJXiBcnC1XyxCxBa03bouAae4A0ajP4ey~TKKwPHikOmu2Rc1NEu"
            "-c6wr8DbMZrm~1WIWG4kFG1jhSRoEk2W82NkGEh4xEPq3gaNjQPfF7zIAwcZUUkg"
            "GkIbT-cQ5UZ6rTqTiFGdXD2z8kjulgmtu8Quo6hplch~9ltmKTOt9blswd6hMfCM"
            "NJ~tUj77j8fz968adb9w43jBtl~~5seb8ys01cg5IGWV44LKMWaLmEgzWQAjg-Jg"
            "9wx-HYwuqH4Klds03WZzRQ__"
        )
        expected_params = {
            'Key-Pair-Id': ['my_id'],
            'Expires': ['1451606400'],
            'Signature': [expected_signature],
        }
        self.assertDesiredUrl(
            self.run_cmd(cmdline)[0], 'http://example.com/hi', expected_params
        )

    def test_custom_policy(self):
        cmdline = (
            self.prefix
            + '--private-key file://'
            + self.private_key_file
            + ' --date-less-than 2016-1-1 --ip-address 12.34.56.78'
        )
        expected_signature = (
            "beEwE8ZmSX71e79a5dxupiE0zHxahe1IFzuTExKxV0InQnKFlT0wj0tardAlGKFL"
            "LdX9HMGiVjIjvMBdUZQJ-9mMXBtFsQ5nLDEoRH29H8AATzaf4Nx4n29XtVp-jPVF"
            "GFtmdaGJedjJRMV-IzBQcJ19VPl3R8t3Fp~8eP9-P8KpvkJXH2UvJ2H8nMBt2Ogv"
            "brCT2hl~91UtEOgmxeA6twWNpziH0uEdpDOHgnYer5ScdFoo02rPjRXIqPuQcjwP"
            "T2wu~A5T~zomcghjMcIdLeJeS9nscTkjON69xBB-t4lclK3mfzsXTumcx-FzLgOB"
            "bP2Z1d~ZU6X0rkeL~w1BlQ__"
        )
        expected_params = {
            'Key-Pair-Id': ['my_id'],
            'Policy': [mock.ANY],
            'Signature': [expected_signature],
        }
        self.assertDesiredUrl(
            self.run_cmd(cmdline)[0], 'http://example.com/hi', expected_params
        )


class TestSignECDSAWithECParameters(BaseECDSASignTest):
    __test__ = True
    pem_label = 'EC PRIVATE KEY'
    # An EC (P-256) key as written by ``openssl ecparam -genkey``, which
    # prepends an EC PARAMETERS block. Only for testing purpose.
    private_key = (
        '-----BEGIN EC PARAMETERS-----\n'
        'BggqhkjOPQMBBw==\n'
        '-----END EC PARAMETERS-----\n'
        '-----BEGIN EC PRIVATE KEY-----\n'
        'MHcCAQEEIIn+jH+ABbyXBxAaGba29zfgklJlso8Uy/hTX87clMxYoAoGCCqGSM49\n'
        'AwEHoUQDQgAEcfEKhYahmRNFgp2LiNJf1Uy9TmWPgyuoAxKxXuS1Gtcxxs+39col\n'
        'Ty9YFvZvhsAcv6B3LwBJW/ah/AUD1BGTIg==\n'
        '-----END EC PRIVATE KEY-----\n'
    )


class BaseSigningCommandTest(BaseAWSCommandParamsTest):
    private_key = TestSign.private_key

    def setUp(self):
        self.files = FileCreator()
        self.private_key_file = self.files.create_file(
            'foo.pem', self.private_key
        )
        self.private_key_arg = 'file://' + self.private_key_file
        self.addCleanup(self.files.remove_all)
        super().setUp()

    def use_private_key(self, contents, scheme='file://'):
        mode = 'wb' if isinstance(contents, bytes) else 'w'
        path = self.files.create_file('key.pem', contents, mode=mode)
        self.private_key_arg = scheme + path

    def sign(self, *args, expected_rc=0):
        cmdline = [
            'cloudfront',
            'sign',
            '--key-pair-id',
            'myid',
            '--private-key',
            self.private_key_arg,
            '--date-less-than',
            '2016-1-1',
        ] + list(args)
        return self.run_cmd(cmdline, expected_rc=expected_rc)

    def sign_url(self, *args):
        url = self.sign(*args)[0].strip()
        return url, parse_qs(urlparse(url).query)

    def sign_cookies(self, *args, expected_rc=0):
        cmdline = [
            'cloudfront',
            'sign-cookies',
            '--key-pair-id',
            'myid',
            '--private-key',
            self.private_key_arg,
            '--date-less-than',
            '2016-1-1',
        ] + list(args)
        return self.run_cmd(cmdline, expected_rc=expected_rc)

    def assert_sign_error(self, message, *args, expected_rc=252):
        _, stderr, _ = self.sign(*args, expected_rc=expected_rc)
        self.assertIn(message, stderr)

    def assert_sign_cookies_error(self, message, *args):
        _, stderr, _ = self.sign_cookies(*args, expected_rc=252)
        self.assertIn(message, stderr)

    def assert_key_error(self, message):
        # Invalid keys have always been reported as an error with rc 255.
        self.assert_sign_error(
            message, '--url', 'http://example.com/hi', expected_rc=255
        )


class TestSignPolicySelection(BaseSigningCommandTest):
    def test_wildcard_url_keeps_canned_policy(self):
        # For backward compatibility --url is always signed as it always
        # was. Wildcard resources are signed with --policy-resource.
        _, params = self.sign_url('--url', 'http://example.com/*')
        self.assertEqual(params['Expires'], ['1451606400'])
        self.assertNotIn('Policy', params)

    def test_policy_resource_is_signed_and_applied_to_url(self):
        url, params = self.sign_url(
            '--url',
            'http://example.com/videos/intro.mp4',
            '--policy-resource',
            'http://example.com/videos/*',
        )
        self.assertTrue(url.startswith('http://example.com/videos/intro.mp4?'))
        self.assertNotIn('Expires', params)
        policy = json.loads(_url_b64decode(params['Policy'][0]))
        self.assertEqual(
            policy['Statement'][0]['Resource'], 'http://example.com/videos/*'
        )

    def test_policy_resource_different_from_url_uses_custom_policy(self):
        # A canned policy is verified against the requested URL, so it can
        # not be used for a resource other than the URL.
        _, params = self.sign_url(
            '--url',
            'http://example.com/hi',
            '--policy-resource',
            'http://example.com/h?',
        )
        self.assertNotIn('Expires', params)
        policy = json.loads(_url_b64decode(params['Policy'][0]))
        self.assertEqual(
            policy['Statement'][0]['Resource'], 'http://example.com/h?'
        )

    def test_rejects_policy_resource_not_matching_url(self):
        for resource in [
            'http://example.com/other',
            'http://example.com/videos/*',
            'http://example.com/h??',
        ]:
            with self.subTest(resource=resource):
                self.assert_sign_error(
                    'does not match --policy-resource',
                    '--url',
                    'http://example.com/hi',
                    '--policy-resource',
                    resource,
                )

    def test_policy_resource_same_as_url_uses_canned_policy(self):
        _, params = self.sign_url(
            '--url',
            'http://example.com/hi',
            '--policy-resource',
            'http://example.com/hi',
        )
        self.assertEqual(params['Expires'], ['1451606400'])
        self.assertNotIn('Policy', params)

    def test_custom_policy_condition_order(self):
        # The order is kept stable so signed URLs are unchanged.
        _, params = self.sign_url(
            '--url',
            'http://example.com/hi',
            '--date-greater-than',
            '2015-12-1',
            '--ip-address',
            '12.34.56.78',
        )
        self.assertEqual(
            _url_b64decode(params['Policy'][0]).decode('utf8'),
            '{"Statement":[{"Resource":"http://example.com/hi","Condition":{'
            '"DateLessThan":{"AWS:EpochTime":1451606400},'
            '"IpAddress":{"AWS:SourceIp":"12.34.56.78/32"},'
            '"DateGreaterThan":{"AWS:EpochTime":1448928000}}}]}',
        )


class TestSignHashAlgorithm(BaseSigningCommandTest):
    def test_rsa_defaults_to_sha1_without_hash_algorithm_param(self):
        _, params = self.sign_url('--url', 'http://example.com/hi')
        self.assertNotIn('Hash-Algorithm', params)
        self.assert_rsa_signature(params, 'SHA1')

    def test_rsa_explicit_sha1_matches_default(self):
        default_url, _ = self.sign_url('--url', 'http://example.com/hi')
        sha1_url, _ = self.sign_url(
            '--url', 'http://example.com/hi', '--hash-algorithm', 'SHA1'
        )
        self.assertEqual(sha1_url, default_url)

    def test_rsa_sha256(self):
        _, params = self.sign_url(
            '--url', 'http://example.com/hi', '--hash-algorithm', 'SHA256'
        )
        self.assertEqual(params['Hash-Algorithm'], ['SHA256'])
        self.assert_rsa_signature(params, 'SHA256')

    def test_unsupported_hash_algorithm(self):
        _, stderr, _ = self.sign(
            '--url',
            'http://example.com/hi',
            '--hash-algorithm',
            'MD5',
            expected_rc=252,
        )
        self.assertIn('--hash-algorithm', stderr)

    def assert_rsa_signature(self, params, hash_algorithm):
        policy = CloudFrontSigner('myid', None).build_policy(
            'http://example.com/hi', parse_to_aware_datetime('2016-1-1')
        )
        signature_algorithm, hash_function = {
            'SHA1': (RSASignatureAlgorithm.PKCS1_5_SHA1, hashlib.sha1),
            'SHA256': (RSASignatureAlgorithm.PKCS1_5_SHA256, hashlib.sha256),
        }[hash_algorithm]
        key = RSA.new_private_key_from_pem_data(self.private_key.encode())
        self.assertTrue(
            key.verify(
                signature_algorithm,
                hash_function(policy.encode('utf8')).digest(),
                _url_b64decode(params['Signature'][0]),
            )
        )


class TestSignECDSAHashAlgorithm(BaseSigningCommandTest):
    private_key = TestSignECDSASEC1.private_key

    def test_ecdsa_sha256(self):
        _, params = self.sign_url(
            '--url', 'http://example.com/hi', '--hash-algorithm', 'SHA256'
        )
        self.assertEqual(params['Hash-Algorithm'], ['SHA256'])

    def test_ecdsa_rejects_sha1(self):
        self.assert_sign_error(
            'cannot be used with ECDSA keys',
            '--url',
            'http://example.com/hi',
            '--hash-algorithm',
            'SHA1',
        )


class TestSignBackwardCompatibility(BaseSigningCommandTest):
    # ``sign`` keeps accepting, and signing in the same way, every value of
    # its original arguments that it accepted before they were validated.
    def assert_signs_canned(self, url, *args):
        signed_url, _ = self.sign_url('--url', url, *args)
        # The signing parameters are appended to the URL as given.
        self.assertTrue(signed_url.startswith(url + '?Expires=1451606400&'))

    def assert_signs_custom(self, url, *args):
        signed_url, params = self.sign_url('--url', url, *args)
        self.assertTrue(signed_url.startswith(url))
        return json.loads(_url_b64decode(params['Policy'][0]))

    def test_urls_are_not_validated(self):
        for url in [
            'rtmp://example.com/video.mp4',
            'video.mp4',
            'http://example.com/caf\u00e9.jpg',
            'http://example.com/a"b',
            'http://example.com/a#b',
        ]:
            with self.subTest(url=url):
                self.assert_signs_canned(url)

    def test_key_pair_id_is_not_validated(self):
        url, _ = self.sign_url(
            '--url', 'http://example.com/hi', '--key-pair-id', 'my_id'
        )
        self.assertIn('Key-Pair-Id=my_id', url)

    def test_ip_address_is_not_validated(self):
        policy = self.assert_signs_custom(
            'http://example.com/hi', '--ip-address', '2001:db8::/32'
        )
        self.assertEqual(
            policy['Statement'][0]['Condition']['IpAddress'],
            {'AWS:SourceIp': '2001:db8::/32'},
        )

    def test_date_range_is_not_validated(self):
        policy = self.assert_signs_custom(
            'http://example.com/hi', '--date-greater-than', '2016-2-1'
        )
        self.assertIn('DateGreaterThan', policy['Statement'][0]['Condition'])

    def test_invalid_date_error(self):
        self.assert_sign_error(
            'Invalid timestamp',
            '--url',
            'http://example.com/hi',
            '--date-less-than',
            'not-a-date',
            expected_rc=255,
        )


class TestSignPolicyResourceValidation(BaseSigningCommandTest):
    def sign_policy_resource(self, url, resource):
        return self.sign(
            '--url', url, '--policy-resource', resource, expected_rc=252
        )[1]

    def test_rejects_unsafe_policy_resource(self):
        for resource in ['http://example.com/\\*', 'http://example.com/"*']:
            with self.subTest(resource=resource):
                self.assertIn(
                    'Invalid value for --policy-resource',
                    self.sign_policy_resource(
                        'http://example.com/hi', resource
                    ),
                )

    def test_rejects_invalid_non_wildcard_policy_resource(self):
        self.assertIn(
            'Invalid value for --policy-resource',
            self.sign_policy_resource('http://example.com/hi', 'not-a-url'),
        )

    def test_rejects_policy_resource_fragment(self):
        self.assertIn(
            'URL fragment',
            self.sign_policy_resource(
                'http://example.com/hi', 'http://example.com/*#frag'
            ),
        )

    def test_validates_url_with_policy_resource(self):
        for url in ['example.com/hi', 'http://example.com/h#i']:
            with self.subTest(url=url):
                self.assertIn(
                    'Invalid value for --url',
                    self.sign_policy_resource(url, '*'),
                )

    def test_rejects_already_signed_url_with_policy_resource(self):
        self.assertIn(
            'already contains the CloudFront signing parameters',
            self.sign_policy_resource(
                'http://example.com/hi?Expires=1&Signature=a&Key-Pair-Id=K',
                'http://example.com/*',
            ),
        )

    def test_allows_wildcard_scheme_in_policy_resource(self):
        _, params = self.sign_url(
            '--url',
            'https://example.com/hi',
            '--policy-resource',
            'http*://example.com/*',
        )
        self.assertIn('Policy', params)


class TestSignCookiesInputValidation(BaseSigningCommandTest):
    def assert_error(self, message, *args):
        self.assert_sign_cookies_error(message, *args)

    def test_rejects_unsafe_characters(self):
        for resource in [
            'http://example.com/hi"',
            'http://example.com/\\*',
            'http://example.com/h\ni',
        ]:
            with self.subTest(resource=resource):
                self.assert_error(
                    'must not contain double quotes', '--resource', resource
                )

    def test_rejects_url_fragment(self):
        for resource in [
            'http://example.com/hi#frag',
            'http://example.com/hi#',
            'http://example.com/*#frag',
        ]:
            with self.subTest(resource=resource):
                self.assert_error('URL fragment', '--resource', resource)

    def test_rejects_malformed_urls(self):
        for resource in [
            'example.com/hi',
            'ftp://example.com/hi',
            'https://[zz/a',
            'https://:80/a',
            'https://example.com:abc/a',
            'https://example.com:99999/a',
        ]:
            with self.subTest(resource=resource):
                self.assert_error('is not a valid URL', '--resource', resource)

    def test_rejects_non_ascii_and_spaces(self):
        for resource in [
            'https://example.com/caf\u00e9.jpg',
            'https://b\u00fccher.example/a.jpg',
            'https://example.com/a b.jpg',
        ]:
            with self.subTest(resource=resource):
                self.assert_error('ASCII characters', '--resource', resource)

    def test_accepts_url_with_port_and_percent_encoding(self):
        stdout, _, _ = self.sign_cookies(
            '--resource',
            'https://example.com:8443/caf%C3%A9.jpg',
            '--output',
            'json',
        )
        self.assertEqual(
            json.loads(stdout)['CloudFront-Expires'], '1451606400'
        )

    def test_rejects_invalid_dates(self):
        for arg, value in [
            ('--date-less-than', 'not-a-date'),
            ('--date-greater-than', 'not-a-date'),
            # A millisecond epoch, e.g. from JavaScript's Date.now().
            ('--date-less-than', '1893456000000'),
        ]:
            with self.subTest(arg=arg, value=value):
                self.assert_error(
                    f'Invalid value for {arg}',
                    '--resource',
                    'http://example.com/hi',
                    arg,
                    value,
                )

    def test_rejects_active_date_not_before_expiration(self):
        for date_greater_than in ['2016-2-1', '2016-1-1']:
            with self.subTest(date_greater_than=date_greater_than):
                self.assert_error(
                    'must be before --date-less-than',
                    '--resource',
                    'http://example.com/hi',
                    '--date-greater-than',
                    date_greater_than,
                )

    def test_rejects_ipv6_address(self):
        self.assert_error(
            'CloudFront only supports IPv4',
            '--resource',
            'http://example.com/hi',
            '--ip-address',
            '2001:db8::/32',
        )

    def test_rejects_invalid_ip_address(self):
        for ip_address in [
            '1.2.3',
            '256.1.1.1',
            '1.2.3.4/33',
            '1.2.3.4/a',
            '1.2.3.0/255.255.255.0',
            '01.2.3.4',
        ]:
            with self.subTest(ip_address=ip_address):
                self.assert_error(
                    'not a valid IPv4 address or CIDR range',
                    '--resource',
                    'http://example.com/hi',
                    '--ip-address',
                    ip_address,
                )

    def test_accepts_ip_address_range(self):
        stdout, _, _ = self.sign_cookies(
            '--resource',
            'http://example.com/hi',
            '--ip-address',
            '192.168.0.0/24',
            '--output',
            'json',
        )
        policy = json.loads(
            _url_b64decode(json.loads(stdout)['CloudFront-Policy'])
        )
        self.assertEqual(
            policy['Statement'][0]['Condition']['IpAddress'],
            {'AWS:SourceIp': '192.168.0.0/24'},
        )

    def test_rejects_invalid_key_pair_ids(self):
        for key_pair_id in ['', 'K&Policy=x', 'K 1', 'K#1', 'K;1', 'my_id']:
            with self.subTest(key_pair_id=key_pair_id):
                self.assert_error(
                    'Invalid value for --key-pair-id',
                    '--resource',
                    'http://example.com/hi',
                    '--key-pair-id',
                    key_pair_id,
                )


class TestSignKeyErrors(BaseSigningCommandTest):
    def test_encrypted_pkcs8_private_key(self):
        self.use_private_key(
            '-----BEGIN ENCRYPTED PRIVATE KEY-----\n'
            'MIIC5TBfBgkqhkiG9w0BBQ0wUjAxBgkqhkiG9w0BBQwwJAQQ4VOg5sq9YVA9jnxg\n'
            '-----END ENCRYPTED PRIVATE KEY-----\n'
        )
        self.assert_key_error('Encrypted private keys are not supported')

    def test_encrypted_pkcs1_private_key(self):
        self.use_private_key(
            '-----BEGIN RSA PRIVATE KEY-----\n'
            'Proc-Type: 4,ENCRYPTED\n'
            'DEK-Info: AES-128-CBC,00000000000000000000000000000000\n'
            '\n'
            'AAAA\n'
            '-----END RSA PRIVATE KEY-----\n'
        )
        self.assert_key_error('Encrypted private keys are not supported')

    def test_malformed_key_bodies(self):
        for label in ['RSA PRIVATE KEY', 'EC PRIVATE KEY', 'PRIVATE KEY']:
            for body in ['MIIC5TBfBgkqhkiG9w0BBQ0w', 'not base64 !!']:
                with self.subTest(label=label, body=body):
                    self.use_private_key(
                        f'-----BEGIN {label}-----\n{body}\n'
                        f'-----END {label}-----\n'
                    )
                    self.assert_key_error(
                        'Unsupported key type or invalid private key'
                    )

    def test_error_does_not_expose_key_material(self):
        body = 'MIIC5TBfBgkqhkiG9w0BBQ0wUjAxBgkqhkiG9w0BBQwwJAQQ4VOg5sq9YVA9'
        for scheme in ['file://', 'fileb://']:
            with self.subTest(scheme=scheme):
                self.use_private_key(
                    f'-----BEGIN PRIVATE KEY-----\n{body}\n'
                    '-----END PRIVATE KEY-----\n',
                    scheme=scheme,
                )
                _, stderr, _ = self.sign(
                    '--url', 'http://example.com/hi', expected_rc=255
                )
                self.assertNotIn(body[:24], stderr)

    def test_non_utf8_private_key(self):
        self.use_private_key(b'\xff\xfe\x00', scheme='fileb://')
        self.assert_key_error('Unsupported private key')

    def test_ec_private_key_without_public_key(self):
        # A P-256 key exported with ``openssl ec -no_public``.
        self.use_private_key(
            '-----BEGIN PRIVATE KEY-----\n'
            'MEECAQAwEwYHKoZIzj0CAQYIKoZIzj0DAQcEJzAlAgEBBCCtiWoCbDTjaVJiKBL+\n'
            'EfVrw1qbBKZkc6ch+SgM8yMdsg==\n'
            '-----END PRIVATE KEY-----\n'
        )
        self.assert_key_error('does not include its public key')


class TestSignPrivateKeyInputs(BaseSigningCommandTest):
    def assert_signs_like_file_key(self):
        expected_url = self.sign_url_with('file://' + self.private_key_file)
        self.assertEqual(
            self.sign_url_with(self.private_key_arg), expected_url
        )

    def sign_url_with(self, private_key_arg):
        self.private_key_arg, previous = private_key_arg, self.private_key_arg
        try:
            return self.sign('--url', 'http://example.com/hi')[0]
        finally:
            self.private_key_arg = previous

    def test_fileb_private_key(self):
        self.use_private_key(self.private_key.encode('ascii'), 'fileb://')
        self.assert_signs_like_file_key()

    def test_private_key_with_byte_order_mark(self):
        self.use_private_key(
            b'\xef\xbb\xbf' + self.private_key.encode('ascii'), 'fileb://'
        )
        self.assert_signs_like_file_key()

    def test_private_key_with_crlf_line_endings(self):
        self.use_private_key(self.private_key.replace('\n', '\r\n'))
        self.assert_signs_like_file_key()

    def test_private_key_after_certificate(self):
        self.use_private_key(
            '-----BEGIN CERTIFICATE-----\n'
            'MIIB9DCCAV2gAwIBAgIUVURURxQltJ3nilDhiDP37i2FhcAwDQYJKoZIhvcNAQEL\n'
            '-----END CERTIFICATE-----\n' + self.private_key
        )
        self.assert_signs_like_file_key()


class TestSignSigningFailures(BaseSigningCommandTest):
    signing_error = RuntimeError(
        '7179 (AWS_ERROR_CAL_CRYPTO_OPERATION_FAILED): Unknown error when '
        'calling underlying Crypto library.'
    )

    def assert_signing_failure(self, key_class):
        with mock.patch.object(
            key_class, 'sign', side_effect=self.signing_error
        ):
            self.assert_key_error('Failed to sign the CloudFront policy')

    def test_rsa_signing_failure(self):
        self.assert_signing_failure(RSA)

    def test_ecdsa_signing_failure(self):
        self.use_private_key(TestSignECDSASEC1.private_key)
        self.assert_signing_failure(EC)

    def test_sign_cookies_signing_failure(self):
        with mock.patch.object(RSA, 'sign', side_effect=self.signing_error):
            _, stderr, _ = self.sign_cookies(
                '--resource', 'http://example.com/hi', expected_rc=255
            )
        self.assertIn('Failed to sign the CloudFront policy', stderr)


class TestSignECDSAUnsupportedCurvePKCS8(BaseSigningCommandTest):
    # An EC private key on the P-384 curve in PKCS#8 format.
    private_key = (
        '-----BEGIN PRIVATE KEY-----\n'
        'MIG2AgEAMBAGByqGSM49AgEGBSuBBAAiBIGeMIGbAgEBBDBMuzkcdg39rdzENI+E\n'
        'T7PxexdQ6bSROnnxQAn+KTrCfDDfWjfhm/AxexdwTBnkffmhZANiAASbiECnsS42\n'
        'Bz5vDZrKGz5t6qtWa6KJdgSHyP75BEwY1Fq5mrrV/mzWRzisPvALUzx6OJyQ/inY\n'
        'mKeb0H9tA7BMjxTpT7GfYE9ySp1bsKqXwa725O6Kcl3pPz6JsiXNVs8=\n'
        '-----END PRIVATE KEY-----\n'
    )

    def test_non_p256_curve_raises_error(self):
        self.assert_key_error('Only P-256 EC keys are supported')


class TestSignCookies(BaseSigningCommandTest):
    def test_canned_policy(self):
        stdout, _, _ = self.sign_cookies(
            '--resource', 'http://example.com/hi', '--output', 'json'
        )
        cookies = json.loads(stdout)
        self.assertEqual(
            set(cookies),
            {
                'CloudFront-Expires',
                'CloudFront-Signature',
                'CloudFront-Key-Pair-Id',
            },
        )
        self.assertEqual(cookies['CloudFront-Expires'], '1451606400')
        self.assertEqual(cookies['CloudFront-Key-Pair-Id'], 'myid')

    def test_cookie_signature_matches_signed_url(self):
        stdout, _, _ = self.sign_cookies(
            '--resource', 'http://example.com/hi', '--output', 'json'
        )
        _, params = self.sign_url('--url', 'http://example.com/hi')
        self.assertEqual(
            json.loads(stdout)['CloudFront-Signature'], params['Signature'][0]
        )

    def test_wildcard_resource_uses_custom_policy(self):
        stdout, _, _ = self.sign_cookies(
            '--resource', 'http://example.com/*', '--output', 'json'
        )
        cookies = json.loads(stdout)
        self.assertNotIn('CloudFront-Expires', cookies)
        policy = json.loads(_url_b64decode(cookies['CloudFront-Policy']))
        self.assertEqual(
            policy['Statement'][0]['Resource'], 'http://example.com/*'
        )

    def test_hash_algorithm_cookie(self):
        stdout, _, _ = self.sign_cookies(
            '--resource',
            'http://example.com/hi',
            '--hash-algorithm',
            'SHA256',
            '--output',
            'json',
        )
        self.assertEqual(
            json.loads(stdout)['CloudFront-Hash-Algorithm'], 'SHA256'
        )

    def test_query(self):
        stdout, _, _ = self.sign_cookies(
            '--resource',
            'http://example.com/hi',
            '--query',
            '"CloudFront-Expires"',
            '--output',
            'text',
        )
        self.assertEqual(stdout.strip(), '1451606400')

    def test_question_mark_does_not_select_custom_policy(self):
        # ``?`` is ambiguous with the query string delimiter, so it is never
        # treated as a wildcard when choosing the policy type.
        for resource in [
            'http://example.com/image.jpg?size=large',
            'http://example.com/image?.jpg',
        ]:
            with self.subTest(resource=resource):
                stdout, _, _ = self.sign_cookies(
                    '--resource', resource, '--output', 'json'
                )
                cookies = json.loads(stdout)
                self.assertEqual(cookies['CloudFront-Expires'], '1451606400')
                self.assertNotIn('CloudFront-Policy', cookies)

    def test_rejects_unsafe_resource(self):
        _, stderr, _ = self.sign_cookies(
            '--resource', 'http://example.com/"*', expected_rc=252
        )
        self.assertIn('Invalid value for --resource', stderr)

    def test_rejects_invalid_non_wildcard_resource(self):
        _, stderr, _ = self.sign_cookies(
            '--resource', 'example.com/hi', expected_rc=252
        )
        self.assertIn('is not a valid URL', stderr)
