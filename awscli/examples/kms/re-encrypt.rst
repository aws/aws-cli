**Example 1: To re-encrypt encrypted data under a different CMK**

The following ``re-encrypt`` example re-encrypts data that was encrypted using the ``encrypt`` operation in the AWS CLI. You can use the ``re-encrypt`` command to re-encrypt the result of any AWS KMS operation that encrypted data or data keys. 

This example writes the output to the command line so you can see the all of the properties in the response. However, unless you're testing or demonstrating this operation, you should base64-decode the encrypted data and save it in a file.

The command in this example re-encrypts the data under a different CMK, but you can re-encrypt it under the same CMK to change characteristics of the encryption, such as the encryption context. 

To run this command, you must have ``kms:ReEncryptFrom`` permission on the CMK that encrypted the data and ``kms:ReEncryptTo`` permissions on the CMK that you use to re-encrypt the data.

* The ``--ciphertext-blob`` parameter identifies the ciphertext to re-encrypt. The file ``ExampleEncryptedFile`` contains the base64-decoded output of the encrypt command. 
* The ``fileb://`` prefix of the file name tells the CLI to treat the input file as binary instead of text. 
* The ``--destination-key-id`` parameter specifies the CMK under which the data is to be re-encrypted. This example uses the key ID to identify the CMK, but you can use a key ID, key ARN, alias name, or alias ARN in this command.
* You do not need to specify the CMK that was used to encrypt the data. AWS KMS gets that information from metadata in the ciphertext. ::

    aws kms re-encrypt \
        --ciphertext-blob fileb://ExampleEncryptedFile \
        --destination-key-id 0987dcba-09fe-87dc-65ba-ab0987654321

The output includes the following properties:

* The ``SourceKeyID`` is the key ID of the CMK that originally encrypted the CMK.
* The ``KeyId`` is the ID of the CMK that re-encrypted the data.
* The ``CiphertextBlob``, which is the re-encrypted data in base64-encoded format. ::

    {
        "CiphertextBlob": "AQICAHgJtIvJqgOGUX6NLvVXnW5OOQT...",
        "SourceKeyId": "arn:aws:kms:us-west-2:123456789012:key/1234abcd-12ab-34cd-56ef-1234567890ab",
        "KeyId": "arn:aws:kms:us-west-2:123456789012:key/0987dcba-09fe-87dc-65ba-ab0987654321"
    }

**Example 2: To re-encrypt encrypted data under a different CMK (Linux or macOs)**

The following ``re-encrypt`` example demonstrates the recommended way to re-encrypt data with the AWS CLI. This example re-encrypts the ciphertext that was encrypted by the encrypt command, but you can use the same procedure to re-encrypt data keys.

This example is the same as the previous example except that it does not write the output to the command line. Instead, after re-encrypting the ciphertext under a different CMK, it extracts the re-encrypted ciphertext from the response, base64-decodes it, and saves the binary data in a file. You can store the file safely. Then, you can use the file in decrypt or re-encrypt commands in the AWS CLI.

To run this command, you must have ``kms:ReEncryptFrom`` permission on the CMK that encrypted the data and ``kms:ReEncryptTo`` permissions on the CMK that will re-encrypt the data.
The ``--ciphertext-blob`` parameter identifies the ciphertext to re-encrypt. 

* The ``fileb://`` prefix tells the CLI to treat the input file as binary instead of text. 
* The ``--destination-key-id`` parameter specifies the CMK under which the data is re-encrypted. This example uses the key ID to identify the CMK, but you can use a key ID, key ARN, alias name, or alias ARN in this command.
* You do not need to specify the CMK that was used to encrypt the data. AWS KMS gets that information from metadata in the ciphertext. 
* The ``--output`` parameter with a value of ``text`` directs the AWS CLI to return the output as text, instead of JSON. 
* The ``--query`` parameter extracts the value of the ``CiphertextBlob`` property from the response.
* The pipe operator ( | ) sends the output of the CLI command to the ``base64`` utility, which decodes the extracted output. The ``CiphertextBlob`` that the re-encrypt operation returns is base64-encoded text. However, the ``decrypt`` and ``re-encrypt`` commands require binary data. The example decodes the base64-encoded ciphertext back to binary and then saves it in a file. You can use the file as input to the decrypt or re-encrypt commands. ::

    aws kms re-encrypt \
        --ciphertext-blob fileb://ExampleEncryptedFile \
        --destination-key-id 0987dcba-09fe-87dc-65ba-ab0987654321 \
        --output text \
        --query CiphertextBlob | base64 --decode > ExampleReEncryptedFile

This command produces no output on screen because it is redirected to a file.

**Example 3: To re-encrypted encrypted data under a different CMK (Windows Command Prompt)**

This example is the same as the previous example, except that it uses the ``certutil`` utility in Windows to base64-decode the ciphertext before saving it in a file.
 
* The first command re-encrypts the ciphertext and saves the base64-encoded ciphertext in a temporary file named ``ExampleReEncryptedFile.base64``.
* The second command uses the ``certutil -decode`` command to decode the base64-encoded ciphertext in the file to binary. Then, it saves the binary ciphertext in the file ``ExampleReEncryptedFile``. This file is ready to be used in a decrypt or re-encrypt command in the AWS CLI. ::

    aws kms re-encrypt ^
        --ciphertext-blob fileb://ExampleEncryptedFile ^
        --destination-key-id 0987dcba-09fe-87dc-65ba-ab0987654321 ^
        --output text ^
        --query CiphertextBlob  > ExampleReEncryptedFile.base64 
    certutil -decode ExampleReEncryptedFile.base64 ExampleReEncryptedFile

Output::

    Input Length = 18
    Output Length = 12
    CertUtil: -decode command completed successfully.

For more information, see `ReEncrypt <https://docs.aws.amazon.com/kms/latest/APIReference/API_ReEncrypt.html>`__ in the *AWS Key Management Service API Reference*.
