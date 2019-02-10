The following command enables versioning on a bucket named ``my-bucket``::

  aws s3api put-bucket-versioning --bucket my-bucket --versioning-configuration Status=Enabled

The following command enables MFA Delete Versioning on an S3 bucket using an MFA device ARN with a recently generated MFA code from the MFA device::

  aws s3api put-bucket-versioning --bucket my-bucket --versioning-configuration MFADelete=Enabled,Status=Enabled --mfa "arn:aws:iam::01234567891:mfa/root-account-mfa-device 123456"

The following command enables versioning, and uses an mfa code ::

  aws s3api put-bucket-versioning --bucket my-bucket --versioning-configuration Status=Enabled --mfa "SERIAL 123456"
