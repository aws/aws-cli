---
name: "\U0001F6AB SignatureDoesNotMatch error report"
about: Report a `SignatureDoesNotMatch` client error.
title: 'SignatureDoesNotMatch error report'
labels: needs-triage
assignees: ''

---

If you have encountered an error message like the following, you're in the right place! If not, please file a standard bug report (https://github.com/aws/aws-cli/issues/new/choose).

> `A client error (SignatureDoesNotMatch) occurred when calling the <ApiCall> operation: The request signature we calculated does not match the signature you provided. Check your key and signing method.`

where `<ApiCall>` changes depending on what command you ran.

## Do this first!

If you have encountered this error, please do the following FIRST (change the [] boxes to [x]):

- [ ] Read the user guide troubleshooting chapter (https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-troubleshooting.html) to check for known issues like clock skew.
- [ ] Confirm that the error occurs even if you use one of the supported installation methods (https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html).

If possible, try using the credentials with another non-Python SDK, like Javascript (http://aws.amazon.com/javascript).

## Required information

If you have done these things, please fill out the following sections:

### Command line version

*You can get this by running `aws --version`.*

### Operating system

*Please include the OS version (e.g., Fedora 32 or Windows 10).*

### Installation method

*Describe how you installed the client, e.g. pip, Windows installer, etc. Also, if different, describe which of the supported installation methods (https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html) you used to test.*

### Command being run and output

Please provide the full command the output with debug mode on (`aws --debug ...`)

*Important!!! Be sure to redact sensitive information like account numbers, ARNs, etc.*

### Other environment details

*This might include a container image (like Docker), CI/CD suite (like Travis), or a cloud instance (an EC2).*

### Does the secret key you are using have special characters, like ‘+’ or ‘/’, in it?

*If possible, do not delete the credentials that are failing so that we can follow up with further debugging commands.*
