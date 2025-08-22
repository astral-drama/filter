"""Command algebra for composable Filter operations.

This module provides the mathematical foundation for Filter's command system,
implementing categorical composition laws and type-safe morphisms.
"""

from typing import TypeVar, Generic, Protocol, Callable, List, Union, Any, Optional
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from pathlib import Path
import functools
from enum import Enum

from .logging_config import get_logger, audit_log

logger = get_logger(__name__)

# Type variables for categorical composition
T = TypeVar('T')
U = TypeVar('U') 
V = TypeVar('V')


class EffectType(Enum):
    """Types of side effects that commands can perform."""
    FILESYSTEM = "filesystem"
    GIT = "git"
    DOCKER = "docker"
    NETWORK = "network"
    CONFIG = "config"
    AUDIT = "audit"


@dataclass(frozen=True)
class Effect:
    """Represents a side effect with context."""
    type: EffectType
    description: str
    context: Optional[dict] = None
    
    def __str__(self) -> str:
        if self.context:
            ctx_str = ', '.join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.type.value}({self.description}, {ctx_str})"
        return f"{self.type.value}({self.description})"


class Morphism(Protocol[T, U]):
    """A morphism between two types with categorical composition properties.
    
    Morphisms must satisfy:
    1. Identity law: id ∘ f = f ∘ id = f
    2. Associativity: (f ∘ g) ∘ h = f ∘ (g ∘ h)
    """
    
    def __call__(self, input: T) -> U:
        """Apply the morphism to transform input to output."""
        ...
    
    def compose(self, other: 'Morphism[U, V]') -> 'Morphism[T, V]':
        """Compose this morphism with another (categorical composition)."""
        ...


@dataclass(frozen=True)
class FilterCommand(Generic[T, U]):
    """A composable Filter command with explicit types and effects.
    
    This represents a morphism in the Filter command category, with:
    - Explicit input/output types for safety
    - Tracked side effects for reasoning
    - Compositional structure following category laws
    """
    
    name: str
    action: Callable[[T], U]
    effects: List[Effect] = field(default_factory=list)
    description: str = ""
    
    def __call__(self, input: T) -> U:
        """Execute the command with full auditing."""
        logger.info(f"Executing command: {self.name}", 
                   extra={'command': self.name, 'input_type': type(input).__name__})
        
        # Audit command execution
        audit_log(f"Command started: {self.name}",
                 command=self.name,
                 effects=[str(e) for e in self.effects],
                 description=self.description)
        
        try:
            result = self.action(input)
            
            # Log successful completion
            logger.info(f"Command completed: {self.name}",
                       extra={'command': self.name, 'output_type': type(result).__name__})
            
            audit_log(f"Command completed: {self.name}",
                     command=self.name,
                     success=True)
            
            return result
            
        except Exception as e:
            logger.error(f"Command failed: {self.name}: {e}",
                        extra={'command': self.name, 'error': str(e)})
            
            audit_log(f"Command failed: {self.name}",
                     command=self.name,
                     success=False,
                     error=str(e))
            raise
    
    def compose(self, other: 'FilterCommand[U, V]') -> 'FilterCommand[T, V]':
        """Compose two commands following categorical composition laws.
        
        Creates a new command that applies this command, then the other.
        Effects are combined in execution order.
        """
        def composed_action(input: T) -> V:
            intermediate = self(input)
            return other(intermediate)
        
        return FilterCommand(
            name=f"{self.name} >> {other.name}",
            action=composed_action,
            effects=self.effects + other.effects,
            description=f"Composition: {self.description} then {other.description}"
        )
    
    def map_input(self, f: Callable[[V], T]) -> 'FilterCommand[V, U]':
        """Map over the input type (contravariant functor)."""
        def mapped_action(input: V) -> U:
            transformed_input = f(input)
            return self(transformed_input)
        
        return FilterCommand(
            name=f"map_input({self.name})",
            action=mapped_action,
            effects=self.effects,
            description=f"Input-mapped: {self.description}"
        )
    
    def map_output(self, f: Callable[[U], V]) -> 'FilterCommand[T, V]':
        """Map over the output type (covariant functor)."""
        def mapped_action(input: T) -> V:
            result = self(input)
            return f(result)
        
        return FilterCommand(
            name=f"map_output({self.name})",
            action=mapped_action,
            effects=self.effects,
            description=f"Output-mapped: {self.description}"
        )
    
    def with_effects(self, *effects: Effect) -> 'FilterCommand[T, U]':
        """Add additional effects to this command."""
        return FilterCommand(
            name=self.name,
            action=self.action,
            effects=list(self.effects) + list(effects),
            description=self.description
        )
    
    def with_description(self, description: str) -> 'FilterCommand[T, U]':
        """Add or update the command description."""
        return FilterCommand(
            name=self.name,
            action=self.action,
            effects=self.effects,
            description=description
        )


class IdentityCommand(FilterCommand[T, T]):
    """The identity morphism for any type T.
    
    Satisfies: id ∘ f = f ∘ id = f for any command f
    """
    
    def __init__(self):
        super().__init__(
            name="identity",
            action=lambda x: x,
            effects=[],
            description="Identity command (no-op)"
        )


def identity() -> IdentityCommand[T]:
    """Create an identity command (categorical identity morphism)."""
    return IdentityCommand()


def pure(value: U) -> FilterCommand[Any, U]:
    """Lift a pure value into the command category."""
    return FilterCommand(
        name=f"pure({value})",
        action=lambda _: value,
        effects=[],
        description=f"Pure value: {value}"
    )


class CommandPipeline(Generic[T, U]):
    """A sequence of composable commands forming a category-theoretic pipeline."""
    
    def __init__(self, commands: List[FilterCommand]):
        self.commands = commands
        self._validate_composition()
    
    def _validate_composition(self):
        """Validate that commands compose properly (types align)."""
        # In a real implementation, we'd use mypy or runtime type checking
        # For now, we trust the type system
        pass
    
    def compose(self) -> FilterCommand[T, U]:
        """Compose all commands into a single command."""
        if not self.commands:
            return identity()
        
        if len(self.commands) == 1:
            return self.commands[0]
        
        # Fold the commands using categorical composition
        result = self.commands[0]
        for cmd in self.commands[1:]:
            result = result.compose(cmd)
        
        return result
    
    def add(self, command: FilterCommand) -> 'CommandPipeline':
        """Add a command to the pipeline."""
        return CommandPipeline(self.commands + [command])
    
    def effects(self) -> List[Effect]:
        """Get all effects from the pipeline."""
        all_effects = []
        for cmd in self.commands:
            all_effects.extend(cmd.effects)
        return all_effects


# Utility functions for common patterns

def sequence(*commands: FilterCommand) -> CommandPipeline:
    """Create a pipeline from a sequence of commands."""
    return CommandPipeline(list(commands))


def parallel(*commands: FilterCommand[T, U]) -> FilterCommand[T, List[U]]:
    """Execute commands in parallel (conceptually - actual implementation may vary)."""
    def parallel_action(input: T) -> List[U]:
        # In a real implementation, this could use asyncio or threading
        results = []
        for cmd in commands:
            results.append(cmd(input))
        return results
    
    all_effects = []
    for cmd in commands:
        all_effects.extend(cmd.effects)
    
    command_names = [cmd.name for cmd in commands]
    
    return FilterCommand(
        name=f"parallel({', '.join(command_names)})",
        action=parallel_action,
        effects=all_effects,
        description=f"Parallel execution of: {', '.join(command_names)}"
    )


def conditional(predicate: Callable[[T], bool], 
                then_cmd: FilterCommand[T, U], 
                else_cmd: FilterCommand[T, U]) -> FilterCommand[T, U]:
    """Conditional command execution based on predicate."""
    def conditional_action(input: T) -> U:
        if predicate(input):
            logger.debug(f"Conditional: executing then branch")
            return then_cmd(input)
        else:
            logger.debug(f"Conditional: executing else branch")
            return else_cmd(input)
    
    return FilterCommand(
        name=f"if({then_cmd.name}, {else_cmd.name})",
        action=conditional_action,
        effects=then_cmd.effects + else_cmd.effects,  # Conservative: assume both might execute
        description=f"Conditional: {then_cmd.description} or {else_cmd.description}"
    )


# Decorator for converting regular functions to FilterCommands

def filter_command(name: str, 
                  effects: List[Effect] = None,
                  description: str = ""):
    """Decorator to convert a function into a FilterCommand."""
    def decorator(func: Callable[[T], U]) -> FilterCommand[T, U]:
        return FilterCommand(
            name=name,
            action=func,
            effects=effects or [],
            description=description or func.__doc__ or ""
        )
    return decorator


# Example usage and testing utilities

if __name__ == "__main__":
    # Example: Demonstrate categorical composition
    
    @filter_command("validate_path", 
                   effects=[Effect(EffectType.FILESYSTEM, "path validation")],
                   description="Validate that a path exists")
    def validate_path(path: Path) -> Path:
        if not path.exists():
            raise ValueError(f"Path does not exist: {path}")
        return path
    
    @filter_command("create_directory",
                   effects=[Effect(EffectType.FILESYSTEM, "directory creation")],
                   description="Create a directory if it doesn't exist")
    def create_directory(path: Path) -> Path:
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    # Compose commands
    ensure_directory = validate_path.compose(create_directory)
    
    # Test composition laws (identity)
    id_cmd = identity()
    composed_with_id = validate_path.compose(id_cmd)
    
    # In a real test suite, we'd verify:
    # assert composed_with_id.name == validate_path.name  # (modulo implementation details)
    # assert composed_with_id.effects == validate_path.effects
    
    print("Command algebra module loaded successfully!")
    print(f"Example composition: {ensure_directory.name}")
    print(f"Effects: {[str(e) for e in ensure_directory.effects]}")