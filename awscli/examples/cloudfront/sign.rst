**To sign a CloudFront URL**

The following example signs a CloudFront URL. To sign a URL, you need the key
pair ID (called the **Access Key ID** in the AWS Management Console) and the
private key of the trusted signer's CloudFront key pair. For more information
about signed URLs, see `Serving Private Content with Signed URLs and Signed
Cookies
<https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/PrivateContent.html>`_
in the *Amazon CloudFront Developer Guide*.

::

    aws cloudfront sign \
        --url https://d111111abcdef8.cloudfront.net/private-content/private-file.html \
        --key-pair-id APKAEIBAERJR2EXAMPLE \
        --private-key file://cf-signer-priv-key.pem \
        --date-less-than 2020-01-01

Output::

    https://d111111abcdef8.cloudfront.net/private-content/private-file.html?Expires=1577836800&Signature=v7tTOShSbp6U853uAIy3IWkegvCyg5kfulm2m7qLAc8NX-wtRFXbLSAmRep3uqYsckuij8c0KE97OQE1QadcusZa3uU~ez6QVoQ9-FSsaiB3hgB-DNxZyCu4~zrx-RfZkI7ZZQXDOEOVjurup2dXIb~obJEymOUMiADckQI-FwnC0utB7ax8Y2sjU7GeP9fcU9sT~I50MUgaxqqZo6-CUOAlER55-pnuuJRc3pCWZKtEI~3YMZ5Gbfv1sF~egkphOYzbGm7iO9~L0YK4S2naC57EmoByvCdiphA6XjXdZmoLzKXEjtniryC0k-mVm99RVz2QQQDJX9hGmhjz3uj7rw__&Key-Pair-Id=APKAEIBAERJR2EXAMPLE

**To sign a CloudFront URL using SHA-256**

The following example signs a CloudFront URL using the SHA-256 hash
algorithm, which is recommended for its stronger security posture. The signed
URL includes the ``Hash-Algorithm`` query parameter so that CloudFront verifies
the signature with SHA-256. ::

    aws cloudfront sign \
        --url https://d111111abcdef8.cloudfront.net/private-content/private-file.html \
        --key-pair-id APKAEIBAERJR2EXAMPLE \
        --private-key file://cf-signer-priv-key.pem \
        --date-less-than 2020-01-01 \
        --hash-algorithm SHA256

Output::

    https://d111111abcdef8.cloudfront.net/private-content/private-file.html?Expires=1577836800&Signature=YS1t-C1br-5iHCU1ggKKk3pio61TpuQtgQaOekhfA-JzdAG35qwU8Fjz78BwJmZUGHAFnxJTq2msCigm9cm1~m6~M-ue8wsoAxDXpTlCmJGWWt2bJLFaBpLSHaHAjj8C9J6Qn07IyVP7jTv4m0HTzO-O2VhCYCYQK018twXjGmf44~FynVJK~GFgpl8OBp4Nv673twzXbzwuEU~0kq-zvXOZCiqZqMQ6~uVtOxa6JzKd6Y453fGyLXtzJj6D9mw6vLIup1zaKA2vVekFWsljwyYfMhVfJRshoHlU8wq0mhYJlFM7jNQGJyI14guHXLh-3Cailhe7dkIeMebzJ26klA__&Key-Pair-Id=APKAEIBAERJR2EXAMPLE&Hash-Algorithm=SHA256

**To sign a CloudFront URL using an ECDSA key**

The following example signs a CloudFront URL with an ECDSA (P-256) private
key. ECDSA keys always sign with SHA-256, so the signed URL includes the
``Hash-Algorithm=SHA256`` query parameter without specifying
``--hash-algorithm``. The key pair ID is the ID of the public key in the
CloudFront key group. ::

    aws cloudfront sign \
        --url https://d111111abcdef8.cloudfront.net/private-content/private-file.html \
        --key-pair-id K2JCJMDEHXQW5F \
        --private-key file://cf-signer-ecdsa-priv-key.pem \
        --date-less-than 2020-01-01

Output::

    https://d111111abcdef8.cloudfront.net/private-content/private-file.html?Expires=1577836800&Signature=MEUCIQC9y65NPHY3Y0ADS3pIIBjYoVbB~N1rnGwYcTudKTj9ZAIgV3pHaL-WuumMpAApEaTN3svwatuNGDt2n0sKDrEGSfM_&Key-Pair-Id=K2JCJMDEHXQW5F&Hash-Algorithm=SHA256

**To sign a CloudFront URL with a wildcard policy resource**

The following example signs a policy for every object under ``/videos/`` and
applies the signature to a specific URL. Because the policy resource contains a
wildcard, a custom policy is used and included in the signed URL. The same
``Policy``, ``Signature`` and ``Key-Pair-Id`` query parameters can be reused
for any URL matching the policy resource. ::

    aws cloudfront sign \
        --url https://d111111abcdef8.cloudfront.net/videos/intro.mp4 \
        --policy-resource "https://d111111abcdef8.cloudfront.net/videos/*" \
        --key-pair-id APKAEIBAERJR2EXAMPLE \
        --private-key file://cf-signer-priv-key.pem \
        --date-less-than 2020-01-01

Output::

    https://d111111abcdef8.cloudfront.net/videos/intro.mp4?Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9kMTExMTExYWJjZGVmOC5jbG91ZGZyb250Lm5ldC92aWRlb3MvKiIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTU3NzgzNjgwMH19fV19&Signature=G0xpyeYh8qA0p5rQbCdlOihuPXaX15w~KrUlEXgnws9ALZipi1EC5O~5QC~bVhpi2HjMQZDuazj8IJN5YAgDsGfUft1uwZmjmr-loumKhInIqAurYzg0UE3QqZOmwB~kSn-XcLLb5aeMaUT~cT1Lm89cSkL2QkOPoOVaarEcF4Y5dt~BF4XFKVXz3pDLWkwxynRXtsfXv1t9wq1mSNSQNjt~TrI4-sOW3z4t1ObLmFsmG-JuJOAjfbZeJHnko1DRtZ3MpJamaj6aKY5NDK7eXE4w5TrE8U~yS5FV1dVURu3WVZ7ae3gBp5fC0smyMNb~dQ7Pak3-PAU~sdbXsg-V7Q__&Key-Pair-Id=APKAEIBAERJR2EXAMPLE
