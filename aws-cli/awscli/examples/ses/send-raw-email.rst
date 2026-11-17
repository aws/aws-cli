**To send a raw email using Amazon SES**

The following ``send-raw-email`` example sends an email with a TXT attachment. ::

    aws ses send-raw-email \
        --cli-binary-format raw-in-base64-out \
        --raw-message file://message.json

The raw message is a JSON data structure saved in a file named ``message.json`` in the current directory.

Contents of ``message.json``::

    {
        "Data": "From: sender@example.com\nTo: recipient@example.com\nSubject: Test email sent using the AWS CLI (contains an attachment)\nMIME-Version: 1.0\nContent-type: Multipart/Mixed; boundary=\"NextPart\"\n\n--NextPart\nContent-Type: text/plain\n\nThis is the message body.\n\n--NextPart\nContent-Type: text/plain;\nContent-Disposition: attachment; filename=\"attachment.txt\"\n\nThis is the text in the attachment.\n\n--NextPart--"
    }

As you can see, "Data" is one long string that contains the entire raw email content in MIME format, including an attachment called attachment.txt.

Output::

    {
        "MessageId": "EXAMPLEf3f73d99b-c63fb06f-d263-41f8-a0fb-d0dc67d56c07-000000"
    }

Replace sender@example.com and recipient@example.com with the addresses you want to use. Note that the sender's email address must be verified with Amazon SES. Until you are granted production access to Amazon SES, you must also verify the email address of the recipient
unless the recipient is the Amazon SES mailbox simulator. For more information on verification, see `Verified identities in Amazon SES <https://docs.aws.amazon.com/ses/latest/dg/verify-addresses-and-domains.html>`__ in the *Amazon Simple Email Service Developer Guide*.

The Message ID in the output indicates that the call to send-raw-email was successful.

If you don't receive the email, check your Junk box.

For more information, see `Sending raw email using the Amazon SES API v2 <https://docs.aws.amazon.com/ses/latest/dg/send-email-raw.html>`__ in the *Amazon Simple Email Service Developer Guide*.
