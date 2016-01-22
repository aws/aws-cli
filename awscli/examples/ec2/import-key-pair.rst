**To import a public key**

First, generate a key pair with the tool of your choice. For example, use this OpenSSL command:

Command::

  openssl genrsa -out my-key.pem 2048
  
Next, save the public key to a local file. For example, use this OpenSSL command:

Command::

  openssl rsa -in my-key.pem -pubout > my-key.pub
  
Finally, this example command imports the specified public key. The public key is the text in the .pub file that is between ``-----BEGIN PUBLIC KEY-----`` and ``-----END PUBLIC KEY-----``.

Command::

  aws ec2 import-key-pair --key-name my-key --public-key-material MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAuhrGNglwb2Zz/Qcz1zV+l12fJOnWmJxC2GMwQOjAX/L7p01o9vcLRoHXxOtcHBx0TmwMo+i85HWMUE7aJtYclVWPMOeepFmDqR1AxFhaIc9jDe88iLA07VK96wY4oNpp8+lICtgCFkuXyunsk4+KhuasN6kOpk7B2w5cUWveooVrhmJprR90FOHQB2Uhe9MkRkFjnbsA/hvZ/Ay0Cflc2CRZm/NG00lbLrV4l/SQnZmP63DJx194T6pI3vAev2+6UMWSwptNmtRZPMNADjmo50KiG2c3uiUIltiQtqdbSBMh9ztL/98AHtn88JG0s8u2uSRTNEHjG55tyuMbLD40QEXAMPLE
  
Output::

  {
    "KeyName": "my-key",
    "KeyFingerprint": "1f:51:ae:28:bf:89:e9:d8:1f:25:5d:37:2d:7d:b8:ca"
  }