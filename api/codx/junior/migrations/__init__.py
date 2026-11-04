"""
Data migrations for codx-junior.

Each migration is a pure function over a project's ``.codx`` folder tree, so it
can be run from the store (on first load), from a test or from a maintenance
script. Migrations must always be **idempotent**: running one twice must leave
the project in the same state and never lose data.

Made with ❤️ by codx-junior
"""

from codx.junior.migrations.kanban_v1_to_v2 import migrate_kanban_v1_to_v2

__all__ = ["migrate_kanban_v1_to_v2"]

# Made with ❤️ by codx-junior