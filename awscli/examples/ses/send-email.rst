**To send a formatted email using Amazon SES**

The following example uses the ``send-email`` command to send a formatted email::

    aws ses send-email --source sender@example.com --destination file://c:\temp\destination.json --message file://c:\temp\message.json

Output::

 {
    "ResponseMetadata": {
        "RequestId": "31f3102a-d3aa-11e2-8d2d-31a6f641cb5f"
    },
    "MessageId": "EXAMPLEf3a5efcd1-51adec81-d2a4-4e3f-9fe2-5d85c1b23783-000000"
 }

The destination and the message are JSON data structures saved in .json files in a directory called c:\\temp. These files are as follows: 


destination.json is below::

 {
	"to_addresses":  ["recipient1@example.com", "recipient2@example.com"],
	"cc_addresses":  ["recipient3@example.com"],
	"bcc_addresses": []
 }

message.json is below::

 {
    "subject": {
        "data": "Test email sent using the AWS CLI",
        "charset": "UTF-8"
    },
    "body": {
        "text": {
            "data": "This is the message body in text format.",
            "charset": "UTF-8"
        },
        "html": {
            "data": "This message body contains HTML formatting. It can, for example, contain links like this one: <a class=\"ulink\" href=\"http://docs.aws.amazon.com/ses/latest/DeveloperGuide\" target=\"_blank\">Amazon SES Developer Guide</a>.",
            "charset": "UTF-8"
        }
    }
 }

Replace the sender and recipient email addresses with the ones you want to use. Note that the sender's email address must be verified with Amazon SES. Until you are granted production access to Amazon SES, you must also verify the email address of each recipient
unless the recipient is the Amazon SES mailbox simulator. For more information on verification, see `Verifying Email Addresses and Domains in Amazon SES`_ in the *Amazon Simple Email Service Developer Guide*.

The Message ID in the output indicates that the call to send-email was successful.

If you don't receive the email, check your Junk box.

For more information on sending formatted email, see `Sending Formatted Email Using the Amazon SES API`_ in the *Amazon Simple Email Service Developer Guide*.

.. _`Verifying Email Addresses and Domains in Amazon SES`: http://docs.aws.amazon.com/ses/latest/DeveloperGuide/verify-addresses-and-domains.html
.. _`Sending Formatted Email Using the Amazon SES API`: http://docs.aws.amazon.com/ses/latest/DeveloperGuide/send-email-formatted.html
