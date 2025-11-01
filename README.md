# firma-pricing

A lightweight toolkit that helps engineers quickly estimate the cost of HLZ line boxes.
It contains a core pricing engine and a simple command line interface.

## Installation

Create and activate a virtual environment, then install the project in editable mode:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Usage

Run the command line interface using Python's module invocation:

```bash
python -m firma_pricing.cli galvanised_steel 800 400 350 4 25 --complexity standard --cable-management --emc-shielding
```

This prints a human readable breakdown. Add `--json` to receive the
values in JSON format for further processing.

## Running tests

```bash
pytest
```
