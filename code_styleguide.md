# AWS CLI code guidelines

This page outlines the code guidelines to use when submitting pull requests for the AWS Command Line Interface (AWS CLI). These are the same set of guidelines that the core contributors use when submitting changes, and we ask the same of all community contributions as well.

The code guidelines include the following:

* The SDK is released under the [Apache license](http://aws.amazon.com/apache2.0/). Any code you submit will be released under that license.
* We maintain a high percentage of code coverage in our unit tests. As a general rule of thumb, code changes should not lower the overall code coverage percentage for the project. In practice, this means that every bug fix and feature addition should include tests.
* Code should follow the [`pep8`](https://www.python.org/dev/peps/pep-0008/) style guide. If you are modifying an existing module, it is more important for the code to be consistent if there are any discrepancies. Using [`flake8`](https://flake8.pycqa.org/en/latest/) can assist in identifying `pep8` compliance issues.
* Code must work on `python3.7` and higher.
* The AWS CLI is cross platform and code must work on at least Linux, Windows, and Mac OS X. Avoid platform specific behavior.
* To implement support for a significant feature that is not yet available in the AWS CLI, talk to the maintainers beforehand to avoid any duplication of effort. You can [file an issue](https://github.com/aws/aws-cli/issues) in the *AWS CLI GitHub* repository to discuss the feature request further.