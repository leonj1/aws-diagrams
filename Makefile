.PHONY: test clean

PYTHON = python3
TEST_MODULE = unittest
TEST_DIR = tests

test:
	$(PYTHON) -m $(TEST_MODULE) discover $(TEST_DIR) -v

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
