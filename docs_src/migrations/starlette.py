#!/usr/bin/env python
import os
import sys
from pathlib import Path

from my_project.utils import get_db_connection
from starlette.applications import Starlette

from saffier.migrations import Migrate


def build_path():
    """
    Builds the path of the project and project root.
    """
    Path(__file__).resolve().parent.parent
    SITE_ROOT = os.path.dirname(os.path.realpath(__file__))

    if SITE_ROOT not in sys.path:
        sys.path.append(SITE_ROOT)
        sys.path.append(os.path.join(SITE_ROOT, "apps"))


def get_application():
    """
    This is optional. The function is only used for organisation purposes.
    """
    build_path()
    database, registry = get_db_connection()

    app = Starlette(__name__)

    Migrate(app=app, registry=registry)
    return app


app = get_application()
