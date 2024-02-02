# Contributing guide

This chapter is reserved for developers who wish to contribute to
`pycrdt-websocket`.

All commands are to be run from the root of the repository unless otherwise
specified.

## Developer installation

To install this project in editable mode, along with optional dependencies
needed to run tests and build documentation:

```
pip install -e ".[test,docs]"
```

## Documentation

To build documentation:

```
mkdocs build
```

## Integration tests

The NPM test dependencies must first be installed:

```
cd tests/
npm install
cd ..
```

To run the integration tests:

```
pytest
```

To run a specific test file:

```
pytest tests/<filename>
```

Notably helpful `pytest` options include:

- `-rP`: print all standard output, which is hidden for passing tests by default.
- `-k <test-name>`: run a specific test function (not file) by its name.
