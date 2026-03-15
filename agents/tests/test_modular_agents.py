"""Tests for modular agent framework.

Tests the AgentBuilder, plugins, and agent hierarchy.
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path

import pytest

# Set up environment for tests
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

from agents.core import AgentBuilder
from agents.plugins import (
    AgentPlugin,
    TodoPlugin,
    TaskPlugin,
    BackgroundPlugin,
    SubagentPlugin,
    TeamPlugin,
    PlanPlugin,
)
from agents.agents import (
    SimpleAgent,
    TodoAgent,
    SubagentAgent,
    TeamAgent,
    FullAgent,
    SFullAgent,
)


class TestAgentBuilder:
    """Test AgentBuilder fluent API."""

    def test_builder_creation(self):
        """Test creating a basic builder."""
        builder = AgentBuilder()
        assert builder is not None

    def test_with_base_tools(self):
        """Test adding base tools."""
        builder = AgentBuilder().with_base_tools()
        assert builder._base_tools_added is True

    def test_with_plugin(self):
        """Test adding a plugin."""
        builder = AgentBuilder().with_plugin(TodoPlugin())
        assert "todo" in builder._plugin_names
        assert len(builder._plugins) == 1

    def test_duplicate_plugin_detection(self):
        """Test that duplicate plugins raise ValueError."""
        builder = AgentBuilder().with_plugin(TodoPlugin())
        with pytest.raises(ValueError, match="Plugin 'todo' already registered"):
            builder.with_plugin(TodoPlugin())

    def test_with_system(self):
        """Test setting system prompt."""
        builder = AgentBuilder().with_system("Custom prompt")
        assert builder._system_prompt == "Custom prompt"

    def test_with_system_append(self):
        """Test appending to system prompt."""
        builder = AgentBuilder().with_system_append("Extra context")
        assert builder._system_append == "Extra context"

    def test_build_without_tools_raises(self):
        """Test that building without tools raises ValueError."""
        builder = AgentBuilder()
        with pytest.raises(ValueError, match="Agent must have at least one tool"):
            builder.build()

    def test_simple_agent_builder(self):
        """Test simple_agent() predefined builder."""
        builder = AgentBuilder.simple_agent()
        assert builder._base_tools_added is True

    def test_todo_agent_builder(self):
        """Test todo_agent() predefined builder."""
        builder = AgentBuilder.todo_agent()
        assert builder._base_tools_added is True
        assert "todo" in builder._plugin_names

    def test_full_agent_builder(self):
        """Test full_agent() predefined builder."""
        builder = AgentBuilder.full_agent()
        assert builder._base_tools_added is True
        assert "todo" in builder._plugin_names
        assert "task" in builder._plugin_names
        assert "background" in builder._plugin_names
        assert "subagent" in builder._plugin_names
        assert "team" in builder._plugin_names
        assert "plan" in builder._plugin_names


class TestTodoPlugin:
    """Test TodoPlugin functionality."""

    def test_plugin_name(self):
        """Test plugin name."""
        plugin = TodoPlugin()
        assert plugin.name == "todo"

    def test_get_tools(self):
        """Test getting tools from plugin."""
        plugin = TodoPlugin()
        tools = plugin.get_tools()
        assert len(tools) == 1
        assert tools[0].__tool_spec__["name"] == "todo"


class TestTaskPlugin:
    """Test TaskPlugin functionality."""

    def test_plugin_name(self):
        """Test plugin name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin = TaskPlugin(tasks_dir=Path(tmpdir))
            assert plugin.name == "task"

    def test_get_tools(self):
        """Test getting tools from plugin."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin = TaskPlugin(tasks_dir=Path(tmpdir))
            tools = plugin.get_tools()
            assert len(tools) == 4
            tool_names = [t.__tool_spec__["name"] for t in tools]
            assert "task_create" in tool_names
            assert "task_get" in tool_names
            assert "task_update" in tool_names
            assert "task_list" in tool_names


class TestBackgroundPlugin:
    """Test BackgroundPlugin functionality."""

    def test_plugin_name(self):
        """Test plugin name."""
        plugin = BackgroundPlugin()
        assert plugin.name == "background"

    def test_get_tools(self):
        """Test getting tools from plugin."""
        plugin = BackgroundPlugin()
        tools = plugin.get_tools()
        assert len(tools) == 2
        tool_names = [t.__tool_spec__["name"] for t in tools]
        assert "bg_run" in tool_names
        assert "bg_check" in tool_names


class TestSubagentPlugin:
    """Test SubagentPlugin functionality."""

    def test_plugin_name(self):
        """Test plugin name."""
        plugin = SubagentPlugin()
        assert plugin.name == "subagent"

    def test_get_tools(self):
        """Test getting tools from plugin."""
        plugin = SubagentPlugin()
        tools = plugin.get_tools()
        assert len(tools) == 1
        assert tools[0].__tool_spec__["name"] == "subagent"


class TestTeamPlugin:
    """Test TeamPlugin functionality."""

    def test_plugin_name(self):
        """Test plugin name."""
        with tempfile.TemporaryDirectory() as team_dir, tempfile.TemporaryDirectory() as inbox_dir:
            plugin = TeamPlugin(
                team_dir=Path(team_dir),
                inbox_dir=Path(inbox_dir)
            )
            assert plugin.name == "team"

    def test_get_tools(self):
        """Test getting tools from plugin."""
        with tempfile.TemporaryDirectory() as team_dir, tempfile.TemporaryDirectory() as inbox_dir:
            plugin = TeamPlugin(
                team_dir=Path(team_dir),
                inbox_dir=Path(inbox_dir)
            )
            tools = plugin.get_tools()
            assert len(tools) == 7
            tool_names = [t.__tool_spec__["name"] for t in tools]
            assert "spawn_teammate" in tool_names
            assert "list_teammates" in tool_names
            assert "teammate_idle" in tool_names
            assert "claim_work" in tool_names
            assert "send_msg" in tool_names
            assert "broadcast" in tool_names
            assert "read_inbox" in tool_names


class TestPlanPlugin:
    """Test PlanPlugin functionality."""

    def test_plugin_name(self):
        """Test plugin name."""
        plugin = PlanPlugin()
        assert plugin.name == "plan"

    def test_get_tools(self):
        """Test getting tools from plugin."""
        plugin = PlanPlugin()
        tools = plugin.get_tools()
        assert len(tools) == 3
        tool_names = [t.__tool_spec__["name"] for t in tools]
        assert "submit_plan" in tool_names
        assert "review_plan" in tool_names
        assert "get_plan" in tool_names


class TestAgentHierarchy:
    """Test agent class hierarchy."""

    def test_simple_agent_creation(self):
        """Test SimpleAgent can be created."""
        agent = SimpleAgent()
        assert agent is not None

    def test_todo_agent_creation(self):
        """Test TodoAgent can be created."""
        agent = TodoAgent()
        assert agent is not None

    def test_subagent_agent_creation(self):
        """Test SubagentAgent can be created."""
        agent = SubagentAgent()
        assert agent is not None

    def test_team_agent_creation(self):
        """Test TeamAgent can be created."""
        agent = TeamAgent()
        assert agent is not None

    def test_full_agent_creation(self):
        """Test FullAgent can be created."""
        agent = FullAgent()
        assert agent is not None

    def test_sfull_agent_alias(self):
        """Test SFullAgent is an alias for FullAgent."""
        assert SFullAgent is FullAgent

    def test_inheritance_chain(self):
        """Test the inheritance hierarchy."""
        assert issubclass(TodoAgent, SimpleAgent)
        assert issubclass(SubagentAgent, TodoAgent)
        assert issubclass(TeamAgent, SubagentAgent)
        assert issubclass(FullAgent, TeamAgent)


class TestIntegration:
    """Integration tests."""

    def test_task_plugin_crud(self):
        """Test TaskPlugin CRUD operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin = TaskPlugin(tasks_dir=Path(tmpdir))

            # Create task
            result = plugin._task_create("Test Task", "Description")
            task = json.loads(result)
            assert task["title"] == "Test Task"
            task_id = task["id"]

            # Get task
            result = plugin._task_get(task_id)
            task = json.loads(result)
            assert task["id"] == task_id

            # Update task
            result = plugin._task_update(task_id, status="completed")
            task = json.loads(result)
            assert task["status"] == "completed"

            # List tasks
            result = plugin._task_list()
            tasks = json.loads(result)
            assert len(tasks) == 1

    def test_plan_plugin_workflow(self):
        """Test PlanPlugin submit/review workflow."""
        plugin = PlanPlugin()

        # Submit plan
        result = plugin._submit_plan("Test plan")
        data = json.loads(result)
        assert data["status"] == "pending"
        plan_id = data["plan_id"]

        # Approve plan
        result = plugin._review_plan(plan_id, approve=True)
        plan = json.loads(result)
        assert plan["status"] == "approved"

        # Verify is_approved
        assert plugin.is_approved(plan_id) is True

    def test_team_plugin_messaging(self):
        """Test TeamPlugin messaging."""
        with tempfile.TemporaryDirectory() as team_dir, tempfile.TemporaryDirectory() as inbox_dir:
            plugin = TeamPlugin(
                team_dir=Path(team_dir),
                inbox_dir=Path(inbox_dir)
            )

            # Spawn teammate
            result = plugin._spawn_teammate("TestTeammate", "developer")
            teammate = json.loads(result)
            assert teammate["name"] == "TestTeammate"

            # List teammates
            result = plugin._list_teammates()
            teammates = json.loads(result)
            assert len(teammates) == 1

            # Send message
            result = plugin._send_msg("TestTeammate", "Hello!")
            assert "sent" in result.lower()

            # Read inbox
            result = plugin._read_inbox("TestTeammate")
            messages = json.loads(result)
            assert len(messages) == 1
            assert messages[0]["content"] == "Hello!"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
