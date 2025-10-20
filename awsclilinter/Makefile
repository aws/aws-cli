.PHONY: setup test format lint clean

setup:
	./setup.sh

test:
	pytest tests/ -v

format:
	black awsclilinter tests
	isort awsclilinter tests

lint:
	black --check awsclilinter tests
	isort --check awsclilinter tests

clean:
	rm -rf venv
	rm -rf build dist *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
