"""MCP server exposing the graph tools. One process = one tenant (set TENANT), so agents cannot cross tenants.

Run standalone: TENANT=acme python mcp_server.py   (stdio transport)
"""
import functools
import os

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

import tools

TENANT = os.environ.get("TENANT", "acme")
mcp = MCPServer("devops-graph")


def _user_errors(fn):
    """MCP hides a plain exception's text from the model; ToolError shows it, so the agent can fix a bad id."""
    @functools.wraps(fn)
    def wrap(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ValueError as e:
            raise ToolError(str(e)) from None
    return wrap


@mcp.tool()
@_user_errors
def get_blast_radius(service_id: str, max_hops: int = 3) -> dict:
    """Services that depend on service_id (directly or transitively, up to max_hops), with tier,
    owning team and PageRank criticality. Use first to judge how bad an incident is."""
    return tools.get_blast_radius(TENANT, service_id, max_hops)


@mcp.tool()
@_user_errors
def find_expert_path(service_id: str, issue_type: str) -> dict:
    """People who resolved past tickets of issue_type on service_id or a directly connected service,
    ranked by count, with graph paths as evidence. Also returns the owning team.
    issue_type is one of: latency, outage, memory_leak, auth_failure, data_loss, config_drift."""
    return tools.find_expert_path(TENANT, service_id, issue_type)


@mcp.tool()
@_user_errors
def decision_lineage(service_id: str) -> list[dict]:
    """Recent architecture decisions that changed service_id, who made them and what they superseded.
    Useful for spotting a recent change that may have caused the incident."""
    return tools.decision_lineage(TENANT, service_id)


@mcp.tool()
@_user_errors
def recall_memory(service_id: str, issue_type: str) -> dict:
    """Past incident episodes on service_id and the playbook steps for issue_type."""
    return tools.recall_memory(TENANT, service_id, issue_type)


@mcp.tool()
@_user_errors
def search_knowledge(query: str) -> list[dict]:
    """Keyword search across the company graph (services, people, teams, tickets, runbooks, decisions, customers,
    incidents, episodes). Returns node ids with their direct links. Use when you do not know exact ids."""
    return tools.search_knowledge(TENANT, query)


@mcp.tool()
@_user_errors
def service_overview(service_id: str) -> dict:
    """Owning team and members, dependencies both ways, runbooks with authors, and recent incidents for a service."""
    return tools.service_overview(TENANT, service_id)


@mcp.tool()
@_user_errors
def create_incident(service_id: str, issue_type: str, summary: str, suspected_root_cause: str = "",
                    candidate_assignees: list[str] | None = None) -> dict:
    """Write the triaged Incident node (shared handoff state). candidate_assignees are person ids like 'p7'."""
    return tools.create_incident(TENANT, service_id, issue_type, summary, suspected_root_cause, candidate_assignees)


@mcp.tool()
@_user_errors
def get_incident(incident_id: str) -> dict:
    """Read an Incident node written by the triage agent."""
    return tools.get_incident(TENANT, incident_id)


@mcp.tool()
@_user_errors
def assign_incident(incident_id: str, person_id: str, plan: list[str]) -> dict:
    """Assign the incident to one person and store the ordered remediation plan."""
    return tools.assign_incident(TENANT, incident_id, person_id, plan)


@mcp.tool()
@_user_errors
def log_episode(session_id: str, agent: str, service_id: str, issue_type: str, summary: str) -> dict:
    """Write an episodic memory entry so future incidents on this service can recall what happened."""
    return tools.log_episode(TENANT, session_id, agent, service_id, issue_type, summary)


@mcp.tool()
@_user_errors
def get_runbook(issue_type: str) -> dict:
    """The runbook for issue_type as ordered steps (ids like 'R-latency-2'), each with its if_fails fallback.
    Issue types: latency, outage, memory_leak, auth_failure, data_loss, config_drift."""
    return tools.get_runbook(TENANT, issue_type)


@mcp.tool()
@_user_errors
def update_runbook(issue_type: str, op: str, step_id: str, text: str = "", reason: str = "",
                   changed_by: str = "") -> dict:
    """Rewire the runbook graph so the next incident follows the new path. op is one of:
    replace (new text for step_id), insert_after (new step after step_id), remove (drop step_id),
    set_fallback (what to do if step_id fails; empty text clears it). Always pass reason and changed_by."""
    return tools.update_runbook(TENANT, issue_type, op, step_id, text, reason, changed_by)


@mcp.tool()
@_user_errors
def compare_actions(action_a: str, takes_down_a: list[str], action_b: str, takes_down_b: list[str],
                    incident_id: str = "") -> dict:
    """Counterfactual blast radius: for two candidate actions, give the service ids each one takes offline
    (e.g. restarting X takes down [X]; a traffic reroute may take down []). Returns services down, customers
    and VIPs hit with graph paths, PageRank risk, and the safer choice. With incident_id, stores a decision receipt."""
    return tools.compare_actions(TENANT, action_a, takes_down_a, action_b, takes_down_b, incident_id)


if __name__ == "__main__":
    mcp.run()
