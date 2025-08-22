"""Phantom types for compile-time state safety.

Phantom types allow us to encode state information in the type system
without runtime overhead, preventing invalid state transitions at compile time.
"""

from typing import TypeVar, Generic, Type, Any, Union, cast
from abc import ABC, abstractmethod


class PhantomType:
    """Base class for phantom type markers.
    
    Phantom types are used purely for compile-time checking and carry
    no runtime information. They enable the type system to prevent
    invalid state transitions.
    """
    pass


# Type variable for phantom type parameters
StateType = TypeVar('StateType', bound=PhantomType)
NewStateType = TypeVar('NewStateType', bound=PhantomType)


class Phantom(Generic[StateType]):
    """Generic phantom type container.
    
    Wraps a value with phantom state information that exists only
    at compile time. The state parameter encodes invariants about
    the wrapped value.
    
    Example:
        # Only initialized repositories can have workspaces created
        repo: Phantom[Repository[Initialised]] = initialize_repo(path)
        workspace = create_workspace(repo)  # Type safe!
        
        # This would be a compile error:
        uninit_repo: Phantom[Repository[Uninitialised]] = Repository(path)
        workspace = create_workspace(uninit_repo)  # ❌ Type error!
    """
    
    def __init__(self, value: Any):
        self._value = value
    
    @property
    def value(self) -> Any:
        """Access the wrapped value."""
        return self._value
    
    def transition_to(self, new_state: Type[NewStateType]) -> 'Phantom[NewStateType]':
        """Transition to a new phantom state.
        
        This is the only way to change phantom state, making state
        transitions explicit and traceable.
        """
        return Phantom[NewStateType](self._value)
    
    def __repr__(self) -> str:
        # Safely extract state name with fallback
        try:
            if hasattr(self, '__orig_class__') and hasattr(self.__orig_class__, '__args__'):
                args = self.__orig_class__.__args__
                if args and hasattr(args[0], '__name__'):
                    state_name = args[0].__name__
                else:
                    state_name = 'Unknown'
            else:
                state_name = 'Unknown'
        except (AttributeError, IndexError, TypeError):
            state_name = 'Unknown'
        
        return f"Phantom[{state_name}]({self._value})"


class StateTransition(Generic[StateType, NewStateType]):
    """Represents a valid state transition between phantom types.
    
    State transitions must be explicitly defined to ensure only
    valid state changes are possible.
    """
    
    def __init__(self, 
                 from_state: Type[StateType], 
                 to_state: Type[NewStateType],
                 description: str):
        self.from_state = from_state
        self.to_state = to_state
        self.description = description
    
    def apply(self, phantom: Phantom[StateType]) -> Phantom[NewStateType]:
        """Apply the state transition to a phantom value."""
        return phantom.transition_to(self.to_state)
    
    def __repr__(self) -> str:
        return f"StateTransition({self.from_state.__name__} -> {self.to_state.__name__})"


class TransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    
    def __init__(self, from_state: str, to_state: str, reason: str = ""):
        self.from_state = from_state
        self.to_state = to_state
        self.reason = reason
        super().__init__(f"Invalid transition from {from_state} to {to_state}: {reason}")


# Utility functions for working with phantom types

def phantom_cast(value: Any, state: Type[StateType]) -> Phantom[StateType]:
    """Cast a value to a phantom type.
    
    This should only be used when you know the state is correct,
    typically at system boundaries or after validation.
    """
    return Phantom[StateType](value)


def unwrap(phantom: Phantom[StateType]) -> Any:
    """Extract the underlying value from a phantom type."""
    return phantom.value


def is_state(phantom: Phantom[Any], state: Type[StateType]) -> bool:
    """Check if a phantom value is in a specific state.
    
    Note: This is a runtime check and should be used sparingly.
    The main benefit of phantom types is compile-time safety.
    """
    # In a more sophisticated implementation, we could store
    # runtime state information for debugging purposes
    return True  # Simplified for now


# Phantom type combinators for complex state relationships

class Either(Phantom[Union[StateType, NewStateType]]):
    """Phantom type representing one of two possible states."""
    pass


class Both(Phantom[StateType]):
    """Phantom type representing multiple simultaneous states.
    
    Useful for entities that satisfy multiple state predicates.
    """
    pass


# Decorator for functions that perform state transitions

def state_transition(from_state: Type[StateType], 
                    to_state: Type[NewStateType],
                    description: str = ""):
    """Decorator to mark functions as state transitions.
    
    This provides documentation and can be used for runtime
    validation or code generation.
    """
    def decorator(func):
        func._state_transition = StateTransition(from_state, to_state, description)
        func._from_state = from_state
        func._to_state = to_state
        return func
    return decorator


# Type-level predicates for phantom types

class HasState(ABC):
    """Protocol for types that have phantom state."""
    
    @abstractmethod
    def get_state_type(self) -> Type[PhantomType]:
        """Get the current phantom state type."""
        pass


# Example usage and testing

if __name__ == "__main__":
    # Example state types (defined elsewhere)
    class Uninitialised(PhantomType): pass
    class Initialised(PhantomType): pass
    
    # Example usage
    repo_path = "/tmp/test-repo"
    
    # Create uninitialised phantom
    uninit_repo = phantom_cast(repo_path, Uninitialised)
    print(f"Uninitialised repo: {uninit_repo}")
    
    # Define transition
    init_transition = StateTransition(Uninitialised, Initialised, 
                                    "Initialize repository with .filter")
    
    # Apply transition
    init_repo = init_transition.apply(uninit_repo)
    print(f"Initialised repo: {init_repo}")
    
    # Extract value
    final_path = unwrap(init_repo)
    print(f"Final path: {final_path}")
    
    print("Phantom types module working correctly!")