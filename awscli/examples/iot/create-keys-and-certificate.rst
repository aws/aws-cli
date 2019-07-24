**To create an RSA key pair and issue an X.509 certificate**

The following ``create-keys-and-certificate`` creates a 2048-bit RSA key pair and issues an X.509 certificate using the issued public key. Because this is the only time that AWS IoT provides the private key for this certificate, be sure to keep it in a secure location. ::

    aws iot create-keys-and-certificate \
        --certificate-pem-outfile "myTest.cert.pem" \
        --public-key-outfile "myTest.public.key" \
        --private-key-outfile "myTest.private.key"
        
Output::

    {
        "certificateArn": "arn:aws:iot:us-west-2:123456789012:cert/9894ba17925e663f1d29c23af4582b8e3b7619c31f3fbd93adcb51ae54b83dc2",
        "certificateId": "9894ba17925e663f1d29c23af4582b8e3b7619c31f3fbd93adcb51ae54b83dc2",
        "certificatePem": "
    -----BEGIN CERTIFICATE-----
    MIICiTCCAfICCQD6m7oRw0uXOjANBgkqhkiG9w0BAQUFADCBiDELMAkGA1UEBhMC
    VVMxCzAJBgNVBAgTAldBMRAwDgYDVQQHEwdTZWF0dGxlMQ8wDQYDVQQKEwZBbWF6
    b24xFDASBgNVBAsTC0lBTSBDb25zb2xlMRIwEAYDVQQDEwlUZXN0Q2lsYWMxHzAd
    BgkqhkiG9w0BCQEWEG5vb25lQGFtYXpvbi5jb20wHhcNMTEwNDI1MjA0NTIxWhcN
    MTIwNDI0MjA0NTIxWjCBiDELMAkGA1UEBhMCVVMxCzAJBgNVBAgTAldBMRAwDgYD
    VQQHEwdTZWF0dGxlMQ8wDQYDVQQKEwZBbWF6b24xFDASBgNVBAsTC0lBTSBDb25z
    b2xlMRIwEAYDVQQDEwlUZXN0Q2lsYWMxHzAdBgkqhkiG9w0BCQEWEG5vb25lQGFt
    YXpvbi5jb20wgZ8wDQYJKoZIhvcNAQEBBQADgY0AMIGJAoGBAMaK0dn+a4GmWIWJ
    21uUSfwfEvySWtC2XADZ4nB+BLYgVIk60CpiwsZ3G93vUEIO3IyNoH/f0wYK8m9T
    rDHudUZg3qX4waLG5M43q7Wgc/MbQITxOUSQv7c7ugFFDzQGBzZswY6786m86gpE
    Ibb3OhjZnzcvQAaRHhdlQWIMm2nrAgMBAAEwDQYJKoZIhvcNAQEFBQADgYEAtCu4
    nUhVVxYUntneD9+h8Mg9q6q+auNKyExzyLwaxlAoo7TJHidbtS4J5iNmZgXL0Fkb
    FFBjvSfpJIlJ00zbhNYS5f6GuoEDmFJl0ZxBHjJnyp378OD8uTs7fLvjx79LjSTb
    NYiytVbZPQUQ5Yaxu2jXnimvw3rrszlaEXAMPLE=
    -----END CERTIFICATE-----\n",
        "keyPair": {
            "PublicKey": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAlYdG66N1nnyJwKSMHw4h\nMMVwOaqhxuuN/dMAS3fyce8DW/4+JP+ErPiyjmoF/YVF/gHr99VE48QbL8i5VF13\n59VK7cefK4NGp67GK+y+jikqXOgHh/xJTwo+sGpWAnmLBPjDz18xOd2ka4tCzuYc\nJpiahJbYkCPUBSU8opVkR7qk4rG6HGj1DR6sx2HocliOOLtu6Fkw91swQJd9bwTi\nGB3ZPrNh0PzQYvjUStZeccyNCx28vfdpMsvp9mQOUXP6plfgxwKRX2fEYKhJFFDa\nhJLXkX3rHU2xbxJSq7D+XLDuPjHKcw+LyFhI5mgFRl88eGdsAVpblps+lnI9EesG\nFQIDAQAB\n-----END PUBLIC KEY-----\n",
            "PrivateKey": "-----BEGIN RSA PRIVATE KEY-----\nkey omittted for security reasons\n-----END RSA PRIVATE KEY-----\n"
        }
    }

For more infomration, see `Create and Register an AWS IoT Device Certificate <https://docs.aws.amazon.com/iot/latest/developerguide/device-certs-create.html>`__ in the **AWS IoT Developer Guide**.
