.PHONY: setup test format lint clean

setup:
	@echo "Setting up AWS CLI Linter..."
	@if [ ! -d "venv" ]; then \
		echo "Creating virtual environment..."; \
		python3.12 -m venv venv; \
	fi
	@echo "Installing dependencies..."
	@. venv/bin/activate && pip install --upgrade pip
	@if [ -f "requirements-dev-lock.txt" ]; then \
		echo "Using lockfile for reproducible builds..."; \
		. venv/bin/activate && pip install -r requirements-dev-lock.txt; \
	else \
		. venv/bin/activate && pip install -r requirements-dev.txt; \
	fi
	@echo "Installing package..."
	@. venv/bin/activate && pip install -e .
	@echo "Setup complete! Activate the virtual environment with: source venv/bin/activate"

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
