"""State definitions for Filter entities.

This module defines the phantom state types used throughout Filter
to ensure type-safe state transitions and prevent invalid operations.
"""

from .phantom import PhantomType


# Repository states

class Uninitialised(PhantomType):
    """Repository exists but has no Filter metadata."""
    pass


class Initialised(PhantomType):
    """Repository has .filter directory and metadata."""
    pass


class Cloned(PhantomType):
    """Repository has been cloned from remote source."""
    pass


class Configured(PhantomType):
    """Repository has complete Filter configuration."""
    pass


# Workspace states

class Created(PhantomType):
    """Workspace directory structure exists."""
    pass


class Running(PhantomType):
    """Workspace containers are active."""
    pass


class Stopped(PhantomType):
    """Workspace containers are stopped."""
    pass


class Destroyed(PhantomType):
    """Workspace has been cleaned up."""
    pass


# Story states

class Draft(PhantomType):
    """Story is being written."""
    pass


class Ready(PhantomType):
    """Story is ready for development."""
    pass


class InProgress(PhantomType):
    """Story is being actively worked on."""
    pass


class Testing(PhantomType):
    """Story is in testing phase."""
    pass


class Complete(PhantomType):
    """Story has been completed."""
    pass


# Project states

class Empty(PhantomType):
    """Project directory exists but is empty."""
    pass


class Populated(PhantomType):
    """Project has kanban structure and metadata."""
    pass


class Active(PhantomType):
    """Project has active stories and workspaces."""
    pass


# Composite states for complex relationships

class ReadyForWorkspace(PhantomType):
    """Entity is ready to have a workspace created.
    
    Combines: Repository[Initialised] + Story[Ready]
    """
    pass


class DeploymentReady(PhantomType):
    """Entity is ready for deployment.
    
    Combines: Workspace[Running] + Story[Testing]
    """
    pass


# State validation helpers

def is_repository_state(state_type: type) -> bool:
    """Check if a state type is valid for repositories."""
    return state_type in {Uninitialised, Initialised, Cloned, Configured}


def is_workspace_state(state_type: type) -> bool:
    """Check if a state type is valid for workspaces."""
    return state_type in {Created, Running, Stopped, Destroyed}


def is_story_state(state_type: type) -> bool:
    """Check if a state type is valid for stories."""
    return state_type in {Draft, Ready, InProgress, Testing, Complete}


def is_project_state(state_type: type) -> bool:
    """Check if a state type is valid for projects."""
    return state_type in {Empty, Populated, Active}


# State transition matrices (valid transitions)

REPOSITORY_TRANSITIONS = {
    # From -> {Valid To states}
    Uninitialised: {Initialised, Cloned},
    Initialised: {Configured},
    Cloned: {Initialised, Configured},
    Configured: set()  # Terminal state
}

WORKSPACE_TRANSITIONS = {
    Created: {Running, Destroyed},
    Running: {Stopped, Destroyed},
    Stopped: {Running, Destroyed},
    Destroyed: set()  # Terminal state
}

STORY_TRANSITIONS = {
    Draft: {Ready},
    Ready: {InProgress},
    InProgress: {Testing, Ready},  # Can go back to Ready
    Testing: {Complete, InProgress},  # Can go back to InProgress
    Complete: set()  # Terminal state
}

PROJECT_TRANSITIONS = {
    Empty: {Populated},
    Populated: {Active},
    Active: {Populated}  # Can become inactive
}


def is_valid_transition(from_state: type, to_state: type) -> bool:
    """Check if a state transition is valid."""
    # Find the appropriate transition matrix
    for transitions in [REPOSITORY_TRANSITIONS, WORKSPACE_TRANSITIONS, 
                       STORY_TRANSITIONS, PROJECT_TRANSITIONS]:
        if from_state in transitions:
            return to_state in transitions[from_state]
    
    # If not found in any matrix, assume invalid
    return False


def get_valid_transitions(from_state: type) -> set:
    """Get all valid states that can be transitioned to from the given state."""
    for transitions in [REPOSITORY_TRANSITIONS, WORKSPACE_TRANSITIONS,
                       STORY_TRANSITIONS, PROJECT_TRANSITIONS]:
        if from_state in transitions:
            return transitions[from_state]
    
    return set()


# State hierarchy for subtyping relationships

class StateHierarchy:
    """Defines subtyping relationships between states.
    
    Some states are more specific versions of others, enabling
    safe coercion in the type system.
    """
    
    # Configured repositories are also Initialised
    SUBTYPES = {
        Configured: {Initialised},
        Running: {Created},
        Complete: {Testing, InProgress, Ready}
    }
    
    @classmethod
    def is_subtype(cls, subtype: type, supertype: type) -> bool:
        """Check if subtype is a subtype of supertype."""
        if subtype == supertype:
            return True
        
        return supertype in cls.SUBTYPES.get(subtype, set())
    
    @classmethod
    def can_coerce(cls, from_type: type, to_type: type) -> bool:
        """Check if from_type can be safely coerced to to_type."""
        return cls.is_subtype(from_type, to_type)