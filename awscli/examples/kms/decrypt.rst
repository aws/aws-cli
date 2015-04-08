The following command decrypts a KMS encrypted, binary encoded version of a 256 bit key named ``encryptedkey-binary`` in the current folder::

  aws kms decrypt --ciphertext-blob fileb://encryptedkey-binary

The fileb:// prefix instructs the AWS CLI not to attempt to decode the binary data in the file.
  
The output of this command includes the ID of the key used to decrypt the key, and a base64 encoded version of the decrypted key. Use ``base64 -d`` to reverse the base64 encoding and view the original hexadecimal (or otherwise encoded) version of the key. The following command uses an AWS CLI query to isolate the base64 plaintext and pipe it into ``base64``::

  aws kms decrypt --ciphertext-blob fileb://encryptedkey-binary --query Plaintext --output text | base64 -d