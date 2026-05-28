"""JobPilot CLI command modules.

Each module registers its ``@app.command()`` functions onto the shared
``app`` defined in ``jobpilot.cli``. Importing this package (done at the
bottom of ``jobpilot.cli``) triggers command registration.
"""
