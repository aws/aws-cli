**Example 1: To generate a 256-bit random number**

The following ``generate-random`` example generates a 256-bit (32-byte) random number. 

When you run this command, you must use the ``number-of-bytes`` parameter to specify the length of the random number in bytes.

You don't specify a CMK when you run this command. Unless you specify a `custom key store <https://docs.aws.amazon.com/kms/latest/developerguide/custom-key-store-overview.html>`__, AWS KMS generates the random number. It is not associated with any particular CMK. ::

    aws kms generate-random --number-of-bytes 32

In the output, the random number is in the ``Plaintext`` field. ::

    {
        "Plaintext": "Hcl7v6T2E+Iangu357rhmlKZUnsb/LqzhHiNt6XNfQ0="
    }

**Example 2: To generate a 256-bit random number and save it to a file (Linux or macOs)**

The following example uses the ``generate-random`` command to generate a 256-bit (32-byte), base64-encoded random byte string on a Linix or macOS computer. The example decodes the byte string and saves it in the ``ExampleRandom`` file. 

When you run this command, you must use the ``number-of-bytes`` parameter to specify the length of the random number in bytes.

You don't specify a CMK when you run this command. Unless you specify a `custom key store <https://docs.aws.amazon.com/kms/latest/developerguide/custom-key-store-overview.html>`__, AWS KMS generates the random number. It is not associated with any particular CMK. 

* The ``--number-of-bytes`` parameter with a value of ``32`` requests a 32-byte (256-bit) string. 
* The ``--output`` parameter with a value of ``text`` directs the AWS CLI to return the output as text, instead of JSON. 
* The ``--query`` parameter extracts the value of the ``Plaintext`` property from the response.
* The pipe operator ( | ) sends the output of the command to the ``base64`` utility, which decodes the extracted output. 
* The redirection operator (>) saves the decoded byte string to the ``ExampleRandom`` file.

    aws kms generate-random --number-of-bytes 32 --output text --query Plaintext | base64 --decode > ExampleRandom

This command produces no output.

**Example 3: To generate a 256-bit random number and save it to a file(Windows Command Prompt)**

The following example uses the ``generate-random`` command to generate a 256-bit (32-byte), base64-encoded random byte string. The example decodes the byte string and saves it in the `ExampleRandom.base64` file.

This example is the same as the previous example, except that it uses the ``certutil`` utility in Windows to base64-decode the random byte string before saving it in a file.

The first command generates the base64-encoded random byte string and saves it in a temporary file, ``ExampleRandom.base64``. The second command uses the ``certutil -decode`` command to decode the base64-encoded byte string in the ``ExampleRandom.base64`` file. Then, it saves the decoded byte string in the ``ExampleRandom`` file. ::
    
    aws kms generate-random --number-of-bytes 32 --output text --query Plaintext > ExampleRandom.base64
    certutil -decode ExampleRandom.base64 ExampleRandom

Output::

    Input Length = 18
    Output Length = 12
    CertUtil: -decode command completed successfully.

For more information, see `GenerateRandom <https://docs.aws.amazon.com/kms/latest/APIReference/API_GenerateRandom.html>`__ in the *AWS Key Management Service API Reference*.
