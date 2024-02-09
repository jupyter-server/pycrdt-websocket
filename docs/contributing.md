# Contributing guide

This chapter is reserved for developers who wish to contribute to
`pycrdt-websocket`.

All commands are to be run from the root of the repository unless otherwise
specified.

## Developer installation

It is recommended to use a package manager such as [pixi](https://prefix.dev/docs/pixi/overview).
You will need to install `pip` and `npm`:

```bash
pixi init
pixi add pip nodejs
pixi shell
```

To install this project in editable mode, along with optional dependencies
needed to run tests and build documentation:

```bash
pip install -e ".[test,docs]"
```

## Documentation

To build the documentation and start a server:

```bash
mkdocs serve
```

Then open a browser at [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Integration tests

The NPM test dependencies must first be installed:

```bash
cd tests/
npm install
cd ..
```

To run the integration tests:

```
pytest -v
```

To run a specific test file:

```bash
pytest tests/<filename>
```

Notably helpful `pytest` options include:

- `-rP`: print all standard output, which is hidden for passing tests by default.
- `-k <test-name>`: run a specific test function (not file) by its name.
