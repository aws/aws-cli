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
from awscli.botocore.compat import parse_qs, urlparse
from awscli.testutils import BaseAWSCommandParamsTest, FileCreator, mock


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
