# Running tests

When contributing to the AWS Command Line Interface (AWS CLI) via Pull Request, automated tests are run. All tests must be passed before a PR can be merged. You should run these locally before submitting a Pull Request and resolve any issues that come up. If you’re having difficulties resolving issues from these tests, reach out to the maintainers on your GitHub issue.

Before you can run tests [setup or update your contribution environment](setup.md). 

## To run all AWS CLI tests

Run the following commands to run all of the AWS CLI tests:

```sh
# Activate your virtual environment
$ source <path_to_venv>/activate  

# Navigate to the cloned AWS CLI repo
$ cd <path_to_awscli_repo>

# Run all tests
$ ./scripts/ci/run-tests
```

## To run a specific AWS CLI test

If you’re resolving an issue with a specific test, instead of rerunning all tests each time it’s faster to rerun the isolated test until all issues are clear. e.g. If you’re submitting an AWS CLI code example for the documentation, it’s useful to rerun the example test in isolation until all errors are cleared.

All tests are python files located in the `tests` folder in the AWS CLI repository. To run a specific test, use the file’s name and location when using the `pytests` command. The following workflow example uses the code examples test `test_examples.py`:

```sh
# Activate your virtual environment
$ source <path_to_venv>/activate  

# Navigate to the cloned AWS CLI repo
$ cd <path_to_awscli_repo>

# Run all tests
$ pytests tests/functional/docs/test_examples.py 
```