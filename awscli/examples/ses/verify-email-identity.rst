**To verify an email address with Amazon SES**

The following ``verify-email-identity`` example verifies an email address. ::

    aws ses verify-email-identity \
        --email-address user@example.com

This command produces no output.

Before you can send an email using Amazon SES, you must verify the address or domain that you are sending the email
from to prove that you own it. If you do not have production access yet, you also need to verify any email addresses
that you send emails to except for email addresses provided by the Amazon SES mailbox simulator.

After verify-email-identity is called, the email address will receive a verification email. The user must click on the link in
the email to complete the verification process.

For more information, see `Creating and verifying identities in Amazon SES <https://docs.aws.amazon.com/ses/latest/dg/creating-identities.html>`__ in the *Amazon Simple Email Service Developer Guide*.
