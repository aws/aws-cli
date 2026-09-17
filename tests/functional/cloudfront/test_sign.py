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

from botocore.compat import parse_qs, urlparse
from botocore.signers import CloudFrontSigner
from botocore.utils import parse_to_aware_datetime

from awscrt.crypto import EC

from awscli.customizations.cloudfront import _pem_to_der
from awscli.testutils import BaseAWSCommandParamsTest, FileCreator, mock


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
        key = EC.new_key_from_der_data(_pem_to_der(self.private_key))
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
