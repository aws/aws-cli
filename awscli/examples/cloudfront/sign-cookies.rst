**To generate CloudFront signed cookies**

The following example generates signed cookies that grant access to every
object in a CloudFront distribution. To generate signed cookies, you need the
key pair ID (called the **Access Key ID** in the AWS Management Console) and
the private key of the trusted signer's CloudFront key pair. Because the
resource contains a wildcard, a custom policy is used. For more information
about signed cookies, see `Using signed cookies
<https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-signed-cookies.html>`_
in the *Amazon CloudFront Developer Guide*. ::

    aws cloudfront sign-cookies \
        --resource "https://d111111abcdef8.cloudfront.net/*" \
        --key-pair-id APKAEIBAERJR2EXAMPLE \
        --private-key file://cf-signer-priv-key.pem \
        --date-less-than 2020-01-01 \
        --hash-algorithm SHA256

Output::

    {
        "CloudFront-Policy": "eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9kMTExMTExYWJjZGVmOC5jbG91ZGZyb250Lm5ldC8qIiwiQ29uZGl0aW9uIjp7IkRhdGVMZXNzVGhhbiI6eyJBV1M6RXBvY2hUaW1lIjoxNTc3ODM2ODAwfX19XX0_",
        "CloudFront-Signature": "Uu8FSzfyZ1pUJfnPTfpZpXoR3cHtu6Vk41gOodDpfCGmY4j~TBvOMBUsXzrcBjAqRuVV9b0Aa1HBpHeY-TR3G3Jbb2Yn2cxNSlAfC4tIYwWOkwypCZl4csuHdFC8XaN0yA0G8GRHDsxNPHKY6lq3ypbnJcXDSzzCixTAgJpOO7M_",
        "CloudFront-Key-Pair-Id": "APKAEIBAERJR2EXAMPLE",
        "CloudFront-Hash-Algorithm": "SHA256"
    }

Set each cookie in the response to the viewer, adding the cookie attributes
(such as ``Domain``, ``Path``, ``Secure`` and ``HttpOnly``) that your
application needs.
