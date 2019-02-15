The following command enables versioning on a bucket named ``my-bucket``::

  aws s3api put-bucket-versioning --bucket my-bucket --versioning-configuration Status=Enabled

The following command enables MFA Delete Versioning on an S3 bucket using an MFA device ARN with a recently generated MFA code from the AWS root account's MFA device. **Please note:** To turn on S3's MFA Delete versioning feature, you will need to use AWS root account credentials with an MFA device from the root account.::

  aws s3api put-bucket-versioning --bucket my-bucket --versioning-configuration MFADelete=Enabled,Status=Enabled --mfa "arn:aws:iam::01234567891:mfa/root-account-mfa-device 123456 --profile root_account_credentials"

The following command enables versioning, and uses an mfa code ::

  aws s3api put-bucket-versioning --bucket my-bucket --versioning-configuration Status=Enabled --mfa "SERIAL 123456"
