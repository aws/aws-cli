"""Setup configuration for awsclilinter package."""

from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="awsclilinter",
    version="1.0.0",
    author="Amazon Web Services",
    description="CLI tool to lint and upgrade bash scripts from AWS CLI v1 to v2",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/aws/aws-cli",
    project_urls={
        "Bug Tracker": "https://github.com/aws/aws-cli/issues",
        "Documentation": "https://github.com/aws/aws-cli",
        "Source Code": "https://github.com/aws/aws-cli",
    },
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Software Development :: Testing",
        "Topic :: Utilities",
    ],
    python_requires=">=3.9",
    install_requires=[
        "ast-grep-py>=0.39.6",
    ],
    extras_require={
        "dev": [
            "pytest>=8.0.0",
            "black>=24.1.1",
            "isort>=5.13.2",
        ],
    },
    entry_points={
        "console_scripts": [
            "upgrade-aws-cli=awsclilinter.cli:main",
        ],
    },
    license="Apache-2.0",
    keywords="aws cli linter bash script migration v1 v2",
    zip_safe=False,
)
