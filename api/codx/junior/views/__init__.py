"""
Views package.

Provides the View model and ViewManager for persisting and retrieving
desktop layout views on a per-project basis.
"""

from codx.junior.views.model import View
from codx.junior.views.view_manager import ViewManager

__all__ = ["View", "ViewManager"]

# Made with ❤️ by codx-junior