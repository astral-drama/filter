"""Functorial transformations for Filter entities.

This module provides functors that enable systematic transformations
between different contexts while preserving categorical structure.
"""

from .workspace import WorkspaceFunctor
from .story import StoryFunctor
from .repository import RepositoryFunctor
from .project import ProjectFunctor

__all__ = [
    'WorkspaceFunctor',
    'StoryFunctor', 
    'RepositoryFunctor',
    'ProjectFunctor'
]