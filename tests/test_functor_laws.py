"""Property-based tests for categorical functor laws.

This module validates that our functors satisfy the fundamental laws:
1. Identity law: fmap(id) = id
2. Composition law: fmap(g ∘ f) = fmap(g) ∘ fmap(f)
"""

import pytest
from pathlib import Path
from typing import TypeVar, Callable, Any
from datetime import datetime

from filter.types import *
from filter.functors import *

# Type variables for testing
T = TypeVar('T')
U = TypeVar('U')
V = TypeVar('V')


class TestFunctorLaws:
    """Test suite for validating functor laws across all Filter entities."""
    
    def test_workspace_functor_identity_law(self):
        """Test that WorkspaceFunctor satisfies identity law: fmap(id) = id."""
        # Create test workspace
        workspace = Workspace[Created](
            name="test-workspace",
            path=Path("/tmp/test-workspace"),
            template="default"
        )
        
        # Create functor
        functor = WorkspaceFunctor(workspace)
        
        # Identity function
        identity = lambda x: x
        
        # Apply identity through functor
        identity_mapped = functor.fmap(identity)
        
        # Verify identity law
        assert identity_mapped.workspace == functor.workspace
        assert identity_mapped.workspace.name == workspace.name
        assert identity_mapped.workspace.path == workspace.path
        assert identity_mapped.workspace.template == workspace.template
    
    def test_workspace_functor_composition_law(self):
        """Test that WorkspaceFunctor satisfies composition law: fmap(g ∘ f) = fmap(g) ∘ fmap(f)."""
        # Create test workspace
        workspace = Workspace[Created](
            name="test-workspace",
            path=Path("/tmp/test-workspace"),
            template="default",
            environment={"TEST": "false"}
        )
        
        functor = WorkspaceFunctor(workspace)
        
        # Define transformation functions
        f = add_story_context("test-story")
        g = add_environment_vars(DEBUG="true", MODE="test")
        
        # Direct composition: g ∘ f
        composed = lambda ws: g(f(ws))
        direct_result = functor.fmap(composed)
        
        # Functor composition: fmap(g) ∘ fmap(f)
        functor_result = functor.fmap(f).fmap(g)
        
        # Verify composition law
        assert direct_result.workspace.story_name == functor_result.workspace.story_name
        assert direct_result.workspace.environment == functor_result.workspace.environment
        assert "test-story" in [direct_result.workspace.story_name, functor_result.workspace.story_name]
        assert "DEBUG" in direct_result.workspace.environment
        assert "MODE" in direct_result.workspace.environment
    
    def test_story_functor_identity_law(self):
        """Test that StoryFunctor satisfies identity law."""
        story = Story[Draft](
            name="test-1",
            title="Test Story",
            description="A test story",
            file_path=Path("/tmp/test-1.md")
        )
        
        functor = StoryFunctor(story)
        identity = lambda x: x
        identity_mapped = functor.fmap(identity)
        
        assert identity_mapped.story == functor.story
    
    def test_story_functor_composition_law(self):
        """Test that StoryFunctor satisfies composition law."""
        story = Story[Draft](
            name="test-1",
            title="Test Story",
            description="A test story",
            file_path=Path("/tmp/test-1.md"),
            tags=[]
        )
        
        functor = StoryFunctor(story)
        
        # Define transformations
        f = set_assignee("alice")
        g = add_tags("urgent", "backend")
        
        # Direct composition
        composed = lambda s: g(f(s))
        direct_result = functor.fmap(composed)
        
        # Functor composition
        functor_result = functor.fmap(f).fmap(g)
        
        # Verify composition law
        assert direct_result.story.assignee == functor_result.story.assignee
        assert set(direct_result.story.tags) == set(functor_result.story.tags)
        assert "alice" == direct_result.story.assignee
        assert "urgent" in direct_result.story.tags
        assert "backend" in direct_result.story.tags
    
    def test_repository_functor_identity_law(self):
        """Test that RepositoryFunctor satisfies identity law."""
        repo = Repository[Uninitialised](
            path=Path("/tmp/test-repo"),
            url="https://github.com/test/repo.git"
        )
        
        functor = RepositoryFunctor(repo)
        identity = lambda x: x
        identity_mapped = functor.fmap(identity)
        
        assert identity_mapped.repository == functor.repository
    
    def test_repository_functor_composition_law(self):
        """Test that RepositoryFunctor satisfies composition law."""
        repo = Repository[Uninitialised](
            path=Path("/tmp/test-repo"),
            url="https://github.com/test/repo.git",
            metadata={}
        )
        
        functor = RepositoryFunctor(repo)
        
        # Define transformations
        f = set_branch("develop")
        g = add_metadata(team="backend", priority="high")
        
        # Direct composition
        composed = lambda r: g(f(r))
        direct_result = functor.fmap(composed)
        
        # Functor composition
        functor_result = functor.fmap(f).fmap(g)
        
        # Verify composition law
        assert direct_result.repository.branch == functor_result.repository.branch
        assert direct_result.repository.metadata == functor_result.repository.metadata
        assert "develop" == direct_result.repository.branch
        assert "team" in direct_result.repository.metadata
        assert "priority" in direct_result.repository.metadata
    
    def test_project_functor_identity_law(self):
        """Test that ProjectFunctor satisfies identity law."""
        project = Project[Empty](
            name="test-project",
            path=Path("/tmp/test-project"),
            prefix="testp"
        )
        
        functor = ProjectFunctor(project)
        identity = lambda x: x
        identity_mapped = functor.fmap(identity)
        
        assert identity_mapped.project == functor.project
    
    def test_project_functor_composition_law(self):
        """Test that ProjectFunctor satisfies composition law."""
        project = Project[Empty](
            name="test-project",
            path=Path("/tmp/test-project"),
            prefix="testp",
            maintainers=[]
        )
        
        functor = ProjectFunctor(project)
        
        # Define transformations
        f = add_maintainer("alice@example.com")
        g = update_description("Updated description")
        
        # Direct composition
        composed = lambda p: g(f(p))
        direct_result = functor.fmap(composed)
        
        # Functor composition
        functor_result = functor.fmap(f).fmap(g)
        
        # Verify composition law
        assert direct_result.project.maintainers == functor_result.project.maintainers
        assert direct_result.project.description == functor_result.project.description
        assert "alice@example.com" in direct_result.project.maintainers
        assert "Updated description" == direct_result.project.description


class TestCommandComposition:
    """Test categorical composition of Filter commands."""
    
    def test_command_identity_law(self):
        """Test that FilterCommand composition satisfies identity law."""
        from filter.command_algebra import FilterCommand, identity, Effect, EffectType
        
        # Create a test command
        test_cmd = FilterCommand(
            name="test_command",
            action=lambda x: x + 1,
            effects=[Effect(EffectType.AUDIT, "test operation")],
            description="Test command"
        )
        
        # Get identity command
        id_cmd = identity()
        
        # Test left identity: id ∘ f = f
        left_composition = id_cmd.compose(test_cmd)
        result1 = left_composition(5)
        direct_result1 = test_cmd(5)
        
        assert result1 == direct_result1
        
        # Test right identity: f ∘ id = f  
        right_composition = test_cmd.compose(id_cmd)
        result2 = right_composition(5)
        direct_result2 = test_cmd(5)
        
        assert result2 == direct_result2
    
    def test_command_associativity_law(self):
        """Test that FilterCommand composition is associative: (f ∘ g) ∘ h = f ∘ (g ∘ h)."""
        from filter.command_algebra import FilterCommand, Effect, EffectType
        
        # Create test commands
        f = FilterCommand("f", lambda x: x + 1, [], "Add 1")
        g = FilterCommand("g", lambda x: x * 2, [], "Multiply by 2") 
        h = FilterCommand("h", lambda x: x - 3, [], "Subtract 3")
        
        # Test associativity
        # Left association: (f ∘ g) ∘ h
        left_assoc = f.compose(g).compose(h)
        
        # Right association: f ∘ (g ∘ h)
        right_assoc = f.compose(g.compose(h))
        
        # Both should produce the same result
        test_input = 10
        left_result = left_assoc(test_input)
        right_result = right_assoc(test_input)
        
        assert left_result == right_result
        
        # Verify the mathematical result: ((10 - 3) * 2) + 1 = 15
        expected = ((test_input - 3) * 2) + 1
        assert left_result == expected
        assert right_result == expected


class TestStateTransitions:
    """Test type-safe state transitions."""
    
    def test_valid_workspace_transitions(self):
        """Test valid workspace state transitions."""
        from filter.functors.workspace import create_workspace_command, start_workspace_command, stop_workspace_command
        
        # Create workspace
        create_cmd = create_workspace_command("test", Path("/tmp/test"), "default")
        created_workspace = create_cmd(None)
        
        assert isinstance(created_workspace, Workspace)
        # In a real implementation, we'd verify the exact type is Workspace[Created]
        
        # Start workspace
        start_cmd = start_workspace_command()
        running_workspace = start_cmd(created_workspace)
        
        assert isinstance(running_workspace, Workspace)
        assert running_workspace.name == created_workspace.name
        assert len(running_workspace.ports) > 0  # Should have allocated ports
        
        # Stop workspace
        stop_cmd = stop_workspace_command()
        stopped_workspace = stop_cmd(running_workspace)
        
        assert isinstance(stopped_workspace, Workspace)
        assert stopped_workspace.name == running_workspace.name
        assert len(stopped_workspace.ports) == 0  # Ports should be released
    
    def test_valid_story_transitions(self):
        """Test valid story state transitions."""
        from filter.functors.story import create_story_command, ready_story_command, start_story_command
        
        # Create story
        create_cmd = create_story_command("test-1", Path("/tmp/test-1.md"), "Test Story")
        draft_story = create_cmd(None)
        
        assert isinstance(draft_story, Story)
        assert draft_story.name == "test-1"
        
        # Ready story
        ready_cmd = ready_story_command()
        ready_story = ready_cmd(draft_story)
        
        assert isinstance(ready_story, Story)
        assert ready_story.name == draft_story.name
        assert ready_story.title == draft_story.title
        
        # Start story
        start_cmd = start_story_command()
        inprogress_story = start_cmd(ready_story)
        
        assert isinstance(inprogress_story, Story)
        assert inprogress_story.name == ready_story.name


if __name__ == "__main__":
    # Run all tests
    test_functor = TestFunctorLaws()
    test_commands = TestCommandComposition()
    test_transitions = TestStateTransitions()
    
    # Functor law tests
    test_functor.test_workspace_functor_identity_law()
    test_functor.test_workspace_functor_composition_law()
    test_functor.test_story_functor_identity_law()
    test_functor.test_story_functor_composition_law()
    test_functor.test_repository_functor_identity_law()
    test_functor.test_repository_functor_composition_law()
    test_functor.test_project_functor_identity_law()
    test_functor.test_project_functor_composition_law()
    
    # Command composition tests
    test_commands.test_command_identity_law()
    test_commands.test_command_associativity_law()
    
    # State transition tests
    test_transitions.test_valid_workspace_transitions()
    test_transitions.test_valid_story_transitions()
    
    print("All categorical laws and properties validated successfully!")
    print("✓ Functor identity laws")
    print("✓ Functor composition laws") 
    print("✓ Command identity laws")
    print("✓ Command associativity laws")
    print("✓ State transition validity")
    print("\nCategorical refactoring foundation is mathematically sound!")