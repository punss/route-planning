"""Decay-constrained vehicle routing for radiopharmaceutical delivery.

Package layout mirrors the project phases:
    config     - YAML loading (with `extends`) and time helpers
    decay      - radioactive decay maths
    geo        - synthetic Boston-metro geography and travel times
    instance   - the Instance data model, derived quantities, validation, I/O
    generator  - Phase 1 synthetic instance generator
    viz        - diagnostic plots
"""

from .config import load_config
from .generator import generate
from .instance import Instance

__all__ = ["Instance", "generate", "load_config"]
