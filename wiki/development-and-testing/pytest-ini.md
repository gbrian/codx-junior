# Development and Testing Configuration

## Overview
This project uses `pytest` as its primary testing framework. To ensure proper module resolution during test execution, the configuration defines specific paths for the Python interpreter.

## Configuration Details
The testing environment is configured to include the `api` directory in the Python search path. This allows test suites to correctly import and interact with the application logic located within the `api` module.

### Settings
- **Python Path**: The configuration explicitly sets `pythonpath = api` to ensure that the internal API structure is accessible to the test runner.

***

**References**
- [Development and Testing] project="codx-junior" file="/pytest.ini"