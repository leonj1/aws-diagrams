.PHONY: test clean

PYTHON = python3
TEST_MODULE = unittest
TEST_FILES = test_tf_scanner.py test_mappings.py

test:
	$(PYTHON) -m $(TEST_MODULE) $(TEST_FILES) -v

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
