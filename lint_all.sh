#!/bin/bash

echo "Sorting imports with isort..."
isort .

echo "Reformatting with black..."
black .

echo "Linting with flake8..."
flake8 .

echo "Linting with pylint..."
pylint src/
