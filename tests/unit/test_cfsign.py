# Should go into botocore/tests/unit
import unittest

from awscli.customizations.cfsign import cloudfront_b64encode, sign


def test_cloudfront_b64encode():
    assert b'aGVsbG8gd29ybGQ_'==cloudfront_b64encode(b'hello world')


class CloudFrontSignTest(unittest.TestCase):

    # The private key, its id, and the domain name used in this class,
    # are all based on a real CloudFront distribution as test environment.
    # That distribution and the key will probably not last for long,
    # but the test case(s) will remain valid.

    key_id = "APKAJW2UAWQ7F2BI3OHA"
    private_key = """
        -----BEGIN RSA PRIVATE KEY-----
        MIIEowIBAAKCAQEAu6o2+Jc8UINw2P/w2l7A1xXu3emQEZQ9diA3bmog8r9Dg+65
        fZgAqmuNWPqBivv7j3DGnLUdt8uCIr7PYUbK7wDa6n7U3ryOWtO2ZTc3StiJVcqT
        sokZ0qxGFtDRafjBuydXtcxh52vVTcHqH33nubyyZIzuhTwfmrIOnUXnLwbMrBBP
        bg/8mlgQooyo1XbrN1eO4XMs+UgQ9Mqc7KRJRinUJ+KYuCnM8f/nN4RjYdjTcghk
        xCPEHCeSt2luywWyYmfguWCBS2Mu1q0250wKyNazlgiiTJtAuuSeweb4NKPOJL9X
        hR6Ce6UuU4WYlli8gvQh3FAV3N3C1Rxo20k28QIDAQABAoIBAQCUEkP5dWrzpCJg
        NeHWizjg/L9SfT1dgXfVQqo6BqckoeElsjDNdifgT6hhcpbQEO52SWeMsiNWp85w
        l9mNSYxJdIVGzPgtHt27sJyT1DNebOg/tu0+y4qCfcd3rR/u24YQo4RDP5ZoQN82
        0TBn1LIIDWk8iS6SFdRh/OgnE8bLhNbK9IfZQFEEJrFkArrn/le/ro2mfJkC/imo
        QvqKmM0dGBXt5SCDSbUQAzKtEcR/4gf/qSjFe2YAwAvSA05WXMH6szdtx6/H/VbK
        Uck/WwTHvGObQDFEWmICxPK9AWT0qaFNjlUsi3bjQRdIlYYrXe+6nVMB/Jp1awq7
        tGBqIcWBAoGBAPtXCNuoQhKXqkjJgteQpB+wFav12XRZgpOciYdeviJrgWydpOOu
        O9wkiRUctUijRJbUuWCJF7SgYGoT2xTTp/COiOReqs7qXLMuuXCZcPKkMRJj5wmo
        Uc2AwUV/o3+PNz1NFK+2RgciXplac7qugIyuxIvBKuVFTBlCg0+if/0pAoGBAL8k
        845wKqOeiawwle/o9lKLGPy1T11GrE6l1A5jRuE1WTVM77jRrb0Hmo0mdfHaf5A0
        EjXGIX/fjcmQzBrEd78eCUsvI2Bgn6xXwhd4TTyWHGZfoQjFqAGkixuLN1oo2h1g
        bRreFKfAubFP8MC93z23vnH6tdY2VIA4h5ehUFyJAoGAJqxJrKLDJ+E2TmTTQR/8
        YPPTIdZ+UyzCrrvTXYTydJFeJLxM9suEYmcswJbePgMBNsQckgIGJ8DVlPzhJN88
        ZANKhPkcByKAiQGTfwPdITiqZE4C6rV/gMNi+bKeEa6TrVcC69Z8B/T94VLNo9fd
        58esbmSWmRiEkQ5u7f3u+6ECgYA8+6ANCLJB43nPCu07TpsP+LrvHTWF799XdEa0
        lG3vuiKNA8/TqmoAziU79VJZ6Dkcm9BXga/8aSmGboD/5UDDI+UZLJ/fxtQKmzEc
        ZdBWjRnge5AYCV+xrnqHPiJZzIDSMIp+sO3sG2vjKzsHc0x/F1lWagOLpWfORLrV
        4KyP6QKBgAafeSrfK3LM7idiCBuxckLCgFoHa7uXLUNJRS5iIU+bbZLPj2ozu/tk
        U0jp7sNk1CyMWI36lR3sujkSyH3lPIXVgrXMuGY3PJRGntN8WlWEsw4VUMGRj3h4
        5rB+y/UOS+nlEwQ6eOS09GByJDEXOXpcwjFcTr/f7V8mi0jH+gY/
        -----END RSA PRIVATE KEY-----
        """

    def test_sign_expire_start_ip(self):
        expected_url = "http://d2ragvjhlngfb6.cloudfront.net/index.html?foo=bar&Policy=eyJTdGF0ZW1lbnQiOlt7IkNvbmRpdGlvbiI6eyJEYXRlR3JlYXRlclRoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTQyMDA3MDQwMH0sIkRhdGVMZXNzVGhhbiI6eyJBV1M6RXBvY2hUaW1lIjoxNzY3MTM5MjAwfSwiSXBBZGRyZXNzIjp7IkFXUzpTb3VyY2VJcCI6IjU0LjI0MC4xOTYuMTY5LzMyIn19LCJSZXNvdXJjZSI6Imh0dHA6Ly9kMnJhZ3ZqaGxuZ2ZiNi5jbG91ZGZyb250Lm5ldC9pbmRleC5odG1sP2Zvbz1iYXIifV19&Signature=ggae69gtUM1c8Av6wWyqlkZWk1sSmUgzPSNn0tUwKwmuEeaDZEy8HqLu~iHYXjHw7uyQomB8O8kg4UozKn~RjIgg4rPo3SjFlcDHB4E-CK8F69w2-bFifLBYb92lhW~qIPtP1HLdc8jXnY3-vp3pj8Lpxl3m7z5UTDZPSAX~u9ZTFZvDo2HEdXWj86EKwXXLqdZlsFBoxC1kVo9hRJPG~zovp0xxz8MdgeidFrHJm-iyiW07A7AJ52mbSZ0KgLOa0TPNgcu-v1jZqUJKDIOtSGU10jh0DM3jpKqcT7gTZW3sQwmApw9Yklf6t0a0pnAE7TDYlLZ6ulnJeQMMKXN8FQ__&Key-Pair-Id=APKAJW2UAWQ7F2BI3OHA"
        self.assertEqual(expected_url, sign(
            "http://d2ragvjhlngfb6.cloudfront.net/index.html?foo=bar",
            self.key_id, self.private_key, expires=1767139200,
            starts=1420070400, ip_address="54.240.196.169"))

    def test_sign_expire_start(self):
        expected_url = "http://d2ragvjhlngfb6.cloudfront.net/index.html?Policy=eyJTdGF0ZW1lbnQiOlt7IkNvbmRpdGlvbiI6eyJEYXRlR3JlYXRlclRoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTQyMDA3MDQwMH0sIkRhdGVMZXNzVGhhbiI6eyJBV1M6RXBvY2hUaW1lIjoxNzY3MTM5MjAwfX0sIlJlc291cmNlIjoiaHR0cDovL2QycmFndmpobG5nZmI2LmNsb3VkZnJvbnQubmV0L2luZGV4Lmh0bWwifV19&Signature=DRQ8dBO5SNfoPtFHwmbMFp5MOve8WU5-IkUBm1EMX2xi1tHY1aAiQMlbMtWFel8vHCeYcgcd-aVHRYlwAsG3Fq28HivqGNKBGvhVXUzkM9Jd-BUIWifmpuvH6hw3g7Q6C~3txZ709jxqMBONNSLgBVjL4QXNEycHIgCq43uA9n9Vc3gVOcHf-SVTXpmRl0nt2ZdgjZaN2Dg06sLmE1xEWBbXPrKi455ykZtpsbUXALPHxbnfIOiCi~uF8qrxNvS~nxwQ1zf-kz3avVjd4ruf4Q4QTB8nuGtERBlMCTske8X5-7gzrDejrZW7FMhNiaGdG~QErX0FGMC80XxN-qe0Jw__&Key-Pair-Id=APKAJW2UAWQ7F2BI3OHA"
        self.assertEqual(expected_url, sign(
            "http://d2ragvjhlngfb6.cloudfront.net/index.html",
            self.key_id, self.private_key, expires=1767139200,
            starts=1420070400))

    def test_sign_expire_ip(self):
        expected_url = "http://d2ragvjhlngfb6.cloudfront.net/index.html?Policy=eyJTdGF0ZW1lbnQiOlt7IkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc2NzEzOTIwMH0sIklwQWRkcmVzcyI6eyJBV1M6U291cmNlSXAiOiI1NC4yNDAuMTk2LjAvMSJ9fSwiUmVzb3VyY2UiOiJodHRwOi8vZDJyYWd2amhsbmdmYjYuY2xvdWRmcm9udC5uZXQvaW5kZXguaHRtbCJ9XX0_&Signature=JQy1XUUal8fM50FYfVWtu4po0AfzXqN0YwImv0yLbZkYg7~J~ZeESznOdIG8lLyzRLIDXYmrP0Lz4PW-L7UYPkpCiqDI9mHHMBJUF7rMlleR4vSfdyeSqPAPq-R0SarelXNUYN9yaXkVWbgtalcaoC3jNBUwZun7Fhb6PI1~1oKIYIKRIGo~1mfqwOjzBS5B1oHlXO5SmW9yXE9MjkfYYcVlJrGizpwIgj0L6qe8eBCbSQNTq7BpyNc5~4YaiFS-tBv~GpQoJdUey1CSZJrYGfkqySAOZIeWphrNVInfxCy8Hai06UYs7QPszhTuK~hlPEJab2~sZJQ6Ce6hufXx9A__&Key-Pair-Id=APKAJW2UAWQ7F2BI3OHA"
        self.assertEqual(expected_url, sign(
            "http://d2ragvjhlngfb6.cloudfront.net/index.html",
            self.key_id, self.private_key, expires=1767139200,
            ip_address="54.240.196.0/1"))  # Note: VPN can not fool CloudFront
