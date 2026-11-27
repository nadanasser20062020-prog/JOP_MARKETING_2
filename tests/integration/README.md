# Integration Tests

This directory is reserved for tests across application components, including local SQLite repositories, API services, migrations, and the matching service.

Use temporary SQLite files and approved fixtures only. Never run test setup against the demonstration database without an explicit safeguard. Integration tests must not require a network database service.
