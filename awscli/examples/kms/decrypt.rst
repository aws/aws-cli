The following command demonstrates the recommended way to decrypt data with the AWS CLI.

.. code::

    aws kms decrypt --ciphertext-blob fileb://ExampleEncryptedFile --output text --query Plaintext | base64 --decode > ExamplePlaintextFile

The command does several things:

#. Uses the ``fileb://`` prefix to specify the ``--ciphertext-blob`` parameter.

    The ``fileb://`` prefix instructs the CLI to read the encrypted data, called the *ciphertext*, from a file and pass the file's contents to the command's ``--ciphertext-blob`` parameter.  If the file is not in the current directory, type the full path to file. For example: ``fileb:///var/tmp/ExampleEncryptedFile`` or ``fileb://C:\Temp\ExampleEncryptedFile``.

    For more information about reading AWS CLI parameter values from a file, see `Loading Parameters from a File <https://docs.aws.amazon.com/cli/latest/userguide/cli-using-param.html#cli-using-param-file>`_ in the *AWS Command Line Interface User Guide* and `Best Practices for Local File Parameters <https://blogs.aws.amazon.com/cli/post/TxLWWN1O25V1HE/Best-Practices-for-Local-File-Parameters>`_ on the AWS Command Line Tool Blog.

    The command assumes the ciphertext in ``ExampleEncryptedFile`` is binary data. The `encrypt examples <encrypt.html#examples>`_ demonstrate how to save a ciphertext this way.

#. Uses the ``--output`` and ``--query`` parameters to control the command's output.

    These parameters extract the decrypted data, called the *plaintext*, from the command's output. For more information about controlling output, see `Controlling Command Output <https://docs.aws.amazon.com/cli/latest/userguide/controlling-output.html>`_ in the *AWS Command Line Interface User Guide*.

#. Uses the ``base64`` utility.

    This utility decodes the extracted plaintext to binary data. The plaintext that is returned by a successful ``decrypt`` command is base64-encoded text. You must decode this text to obtain the original plaintext.

#. Saves the binary plaintext to a file.

    The final part of the command (``> ExamplePlaintextFile``) saves the binary plaintext data to a file.

**Example: Using the AWS CLI to decrypt data from the Windows command prompt**

The preceding example assumes the ``base64`` utility is available, which is commonly the case on Linux and Mac OS X. For the Windows command prompt, use ``certutil`` instead of ``base64``. This requires two commands, as shown in the following examples.

.. code::

    aws kms decrypt --ciphertext-blob fileb://ExampleEncryptedFile --output text --query Plaintext > ExamplePlaintextFile.base64

.. code::

    certutil -decode ExamplePlaintextFile.base64 ExamplePlaintextFile