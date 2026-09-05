# Confirmed Requirements: Normalized Greeting CLI

The reader is an implementation Agent. These decisions are final:

- Preserve `greeting(name)` as the public Python function.
- Normalize the supplied name by trimming leading and trailing whitespace.
- A non-empty normalized name returns and prints `Hello, <name>!`.
- An empty normalized name is invalid: the CLI writes `name must not be blank` to stderr and exits with status 2.
- The function raises `ValueError` with the same message for an empty normalized name.
- Do not add dependencies or change the command shape `python3 app.py NAME`.
- Acceptance evidence is `python3 -m unittest -v` in the fixture repository.
- No external writes or network access are needed.
