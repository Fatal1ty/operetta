devel:
    poetry install

clean:
    rm -rf build dist
    rm -rf `find . -type d -name __pycache__`
    rm -f `find . -type f -name '*.py[co]'`
    rm -rf `find . -type d -name .pytest_cache`
    rm -rf `find . -type d -name .mypy_cache`
    rm -rf *.egg-info
    rm -rf htmlcov
    rm -f .coverage
    rm -f .coverage.*

lint:
    isort --check --diff operetta
    black --check --diff operetta
    # flake8 operetta
    mypy operetta

format:
    isort operetta
    black operetta
