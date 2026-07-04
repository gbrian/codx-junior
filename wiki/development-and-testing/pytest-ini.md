# Development and Testing Environment Configuration

This project utilizes `pytest` as its primary testing framework. To ensure proper module resolution during test execution, the configuration defines a specific search path.

## Test Environment Setup

The testing environment is configured to include the `api` directory in the Python search path. This ensures that the test runner correctly locates and imports modules contained within the `api` component of the project.

### Configuration Details
- **Tool:** pytest
- **Python Path:** `api`

For further details on this configuration, refer to the project's internal testing setup documentation.