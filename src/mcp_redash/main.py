"""Redash MCP server - tools and entrypoint."""

import json
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from dotenv import load_dotenv
from mcp.server.fastmcp import Context, FastMCP

from mcp_redash.client import RedashClient

load_dotenv()

logger = logging.getLogger(__name__)

try:
    _timeout = int(os.getenv("REDASH_TIMEOUT", "30000"))
except ValueError:
    _timeout = 30000


@dataclass
class RedashContext:
    client: RedashClient


@asynccontextmanager
async def redash_lifespan(server: FastMCP) -> AsyncIterator[RedashContext]:
    client = RedashClient(timeout=_timeout / 1000.0)
    yield RedashContext(client=client)


def get_client(ctx: Context) -> RedashClient:
    return ctx.request_context.lifespan_context.client


mcp = FastMCP("redash-mcp", lifespan=redash_lifespan)


def _json(obj: object) -> str:
    return json.dumps(obj, indent=2)


# --- Query tools ---


@mcp.tool()
async def get_query(ctx: Context, query_id: int) -> str:
    """Get details of a Redash query by ID."""
    try:
        client = get_client(ctx)
        result = client.get_query(query_id)
        return _json(result)
    except Exception as e:
        logger.exception("get_query failed")
        return f"Error getting query {query_id}: {e}"


@mcp.tool()
async def list_queries(
    ctx: Context,
    page: int = 1,
    page_size: int = 25,
    q: str | None = None,
) -> str:
    """List Redash queries with optional search and pagination."""
    try:
        client = get_client(ctx)
        result = client.get_queries(page=page, page_size=page_size, q=q)
        return _json(result)
    except Exception as e:
        logger.exception("list_queries failed")
        return f"Error listing queries: {e}"


@mcp.tool()
async def create_query(
    ctx: Context,
    name: str,
    data_source_id: int,
    query: str,
    description: str = "",
    options: str | None = None,
    schedule: str | None = None,
    tags: str | None = None,
) -> str:
    """Create a new Redash query. options/schedule/tags as JSON strings if needed."""
    try:
        client = get_client(ctx)
        opts = json.loads(options) if options else {}
        sched = json.loads(schedule) if schedule else None
        tag_list = json.loads(tags) if tags else []
        result = client.create_query(
            name=name,
            data_source_id=data_source_id,
            query=query,
            description=description,
            options=opts,
            schedule=sched,
            tags=tag_list if isinstance(tag_list, list) else [],
        )
        return _json(result)
    except Exception as e:
        logger.exception("create_query failed")
        return f"Error creating query: {e}"


@mcp.tool()
async def update_query(
    ctx: Context,
    query_id: int,
    name: str | None = None,
    data_source_id: int | None = None,
    query: str | None = None,
    description: str | None = None,
    options: str | None = None,
    schedule: str | None = None,
    tags: str | None = None,
    is_archived: bool | None = None,
    is_draft: bool | None = None,
) -> str:
    """Update an existing Redash query. Pass only fields to update."""
    try:
        client = get_client(ctx)
        kwargs = {}
        if name is not None:
            kwargs["name"] = name
        if data_source_id is not None:
            kwargs["data_source_id"] = data_source_id
        if query is not None:
            kwargs["query"] = query
        if description is not None:
            kwargs["description"] = description
        if options is not None:
            kwargs["options"] = json.loads(options)
        if schedule is not None:
            kwargs["schedule"] = json.loads(schedule)
        if tags is not None:
            kwargs["tags"] = json.loads(tags)
        if is_archived is not None:
            kwargs["is_archived"] = is_archived
        if is_draft is not None:
            kwargs["is_draft"] = is_draft
        result = client.update_query(query_id, **kwargs)
        return _json(result)
    except Exception as e:
        logger.exception("update_query failed")
        return f"Error updating query {query_id}: {e}"


@mcp.tool()
async def archive_query(ctx: Context, query_id: int) -> str:
    """Archive (soft-delete) a Redash query."""
    try:
        client = get_client(ctx)
        result = client.archive_query(query_id)
        return _json(result)
    except Exception as e:
        logger.exception("archive_query failed")
        return f"Error archiving query {query_id}: {e}"


@mcp.tool()
async def list_data_sources(ctx: Context) -> str:
    """List all Redash data sources (for creating queries)."""
    try:
        client = get_client(ctx)
        result = client.get_data_sources()
        return _json(result)
    except Exception as e:
        logger.exception("list_data_sources failed")
        return f"Error listing data sources: {e}"


@mcp.tool()
async def execute_query(
    ctx: Context,
    query_id: int,
    parameters: str | None = None,
) -> str:
    """Execute a Redash query by ID. parameters: optional JSON object."""
    try:
        client = get_client(ctx)
        params = json.loads(parameters) if parameters else {}
        result = client.execute_query(query_id, parameters=params)
        return _json(result)
    except Exception as e:
        logger.exception("execute_query failed")
        return f"Error executing query {query_id}: {e}"


@mcp.tool()
async def execute_adhoc_query(
    ctx: Context,
    query: str,
    data_source_id: int,
) -> str:
    """Execute an ad-hoc query without saving it to Redash."""
    try:
        client = get_client(ctx)
        result = client.execute_adhoc_query(query, data_source_id)
        return _json(result)
    except Exception as e:
        logger.exception("execute_adhoc_query failed")
        return f"Error executing adhoc query: {e}"


@mcp.tool()
async def get_query_results_csv(
    ctx: Context,
    query_id: int,
    refresh: bool = False,
) -> str:
    """Get query results as CSV. Set refresh=True to get latest data."""
    try:
        client = get_client(ctx)
        result = client.get_query_results_csv(query_id, refresh=refresh)
        return result
    except Exception as e:
        logger.exception("get_query_results_csv failed")
        return f"Error getting CSV for query {query_id}: {e}"


@mcp.tool()
async def get_schema(ctx: Context, data_source_id: int) -> str:
    """Get schema (tables/columns) for a Redash data source."""
    try:
        client = get_client(ctx)
        result = client.get_schema(data_source_id)
        return _json(result)
    except Exception as e:
        logger.exception("get_schema failed")
        return f"Error getting schema for data source {data_source_id}: {e}"


@mcp.tool()
async def fork_query(ctx: Context, query_id: int) -> str:
    """Fork (copy) an existing query."""
    try:
        client = get_client(ctx)
        result = client.fork_query(query_id)
        return _json(result)
    except Exception as e:
        logger.exception("fork_query failed")
        return f"Error forking query {query_id}: {e}"


@mcp.tool()
async def get_my_queries(
    ctx: Context,
    page: int = 1,
    page_size: int = 25,
) -> str:
    """List queries owned by the current user."""
    try:
        client = get_client(ctx)
        result = client.get_my_queries(page=page, page_size=page_size)
        return _json(result)
    except Exception as e:
        logger.exception("get_my_queries failed")
        return f"Error listing my queries: {e}"


@mcp.tool()
async def get_recent_queries(
    ctx: Context,
    page: int = 1,
    page_size: int = 25,
) -> str:
    """List recently used queries."""
    try:
        client = get_client(ctx)
        result = client.get_recent_queries(page=page, page_size=page_size)
        return _json(result)
    except Exception as e:
        logger.exception("get_recent_queries failed")
        return f"Error listing recent queries: {e}"


@mcp.tool()
async def get_query_tags(ctx: Context) -> str:
    """List all query tags."""
    try:
        client = get_client(ctx)
        result = client.get_query_tags()
        return _json(result)
    except Exception as e:
        logger.exception("get_query_tags failed")
        return "Error getting query tags"


# --- Dashboard tools ---


@mcp.tool()
async def list_dashboards(
    ctx: Context,
    page: int = 1,
    page_size: int = 25,
) -> str:
    """List Redash dashboards."""
    try:
        client = get_client(ctx)
        result = client.get_dashboards(page=page, page_size=page_size)
        return _json(result)
    except Exception as e:
        logger.exception("list_dashboards failed")
        return f"Error listing dashboards: {e}"


@mcp.tool()
async def get_dashboard(ctx: Context, dashboard_id: int) -> str:
    """Get dashboard details and widgets/visualizations."""
    try:
        client = get_client(ctx)
        result = client.get_dashboard(dashboard_id)
        return _json(result)
    except Exception as e:
        logger.exception("get_dashboard failed")
        return f"Error getting dashboard {dashboard_id}: {e}"


@mcp.tool()
async def create_dashboard(
    ctx: Context,
    name: str,
    tags: str | None = None,
) -> str:
    """Create a new dashboard. tags: optional JSON array of strings."""
    try:
        client = get_client(ctx)
        tag_list = json.loads(tags) if tags else []
        result = client.create_dashboard(name=name, tags=tag_list)
        return _json(result)
    except Exception as e:
        logger.exception("create_dashboard failed")
        return f"Error creating dashboard: {e}"


@mcp.tool()
async def update_dashboard(
    ctx: Context,
    dashboard_id: int,
    name: str | None = None,
    tags: str | None = None,
    is_archived: bool | None = None,
    is_draft: bool | None = None,
    dashboard_filters_enabled: bool | None = None,
) -> str:
    """Update a dashboard. Pass only fields to update."""
    try:
        client = get_client(ctx)
        kwargs = {}
        if name is not None:
            kwargs["name"] = name
        if tags is not None:
            kwargs["tags"] = json.loads(tags)
        if is_archived is not None:
            kwargs["is_archived"] = is_archived
        if is_draft is not None:
            kwargs["is_draft"] = is_draft
        if dashboard_filters_enabled is not None:
            kwargs["dashboard_filters_enabled"] = dashboard_filters_enabled
        result = client.update_dashboard(dashboard_id, **kwargs)
        return _json(result)
    except Exception as e:
        logger.exception("update_dashboard failed")
        return f"Error updating dashboard {dashboard_id}: {e}"


@mcp.tool()
async def archive_dashboard(ctx: Context, dashboard_id: int) -> str:
    """Archive a dashboard."""
    try:
        client = get_client(ctx)
        result = client.archive_dashboard(dashboard_id)
        return _json(result)
    except Exception as e:
        logger.exception("archive_dashboard failed")
        return f"Error archiving dashboard {dashboard_id}: {e}"


@mcp.tool()
async def fork_dashboard(ctx: Context, dashboard_id: int) -> str:
    """Fork (copy) a dashboard."""
    try:
        client = get_client(ctx)
        result = client.fork_dashboard(dashboard_id)
        return _json(result)
    except Exception as e:
        logger.exception("fork_dashboard failed")
        return f"Error forking dashboard {dashboard_id}: {e}"


@mcp.tool()
async def get_public_dashboard(ctx: Context, token: str) -> str:
    """Get a public dashboard by its share token."""
    try:
        client = get_client(ctx)
        result = client.get_public_dashboard(token)
        return _json(result)
    except Exception as e:
        logger.exception("get_public_dashboard failed")
        return f"Error fetching public dashboard: {e}"


@mcp.tool()
async def share_dashboard(ctx: Context, dashboard_id: int) -> str:
    """Create a public share link for a dashboard."""
    try:
        client = get_client(ctx)
        result = client.share_dashboard(dashboard_id)
        return _json(result)
    except Exception as e:
        logger.exception("share_dashboard failed")
        return f"Error sharing dashboard {dashboard_id}: {e}"


@mcp.tool()
async def unshare_dashboard(ctx: Context, dashboard_id: int) -> str:
    """Revoke public sharing for a dashboard."""
    try:
        client = get_client(ctx)
        result = client.unshare_dashboard(dashboard_id)
        return _json(result)
    except Exception as e:
        logger.exception("unshare_dashboard failed")
        return f"Error unsharing dashboard {dashboard_id}: {e}"


@mcp.tool()
async def get_my_dashboards(
    ctx: Context,
    page: int = 1,
    page_size: int = 25,
) -> str:
    """List dashboards owned by the current user."""
    try:
        client = get_client(ctx)
        result = client.get_my_dashboards(page=page, page_size=page_size)
        return _json(result)
    except Exception as e:
        logger.exception("get_my_dashboards failed")
        return f"Error listing my dashboards: {e}"


@mcp.tool()
async def get_favorite_dashboards(
    ctx: Context,
    page: int = 1,
    page_size: int = 25,
) -> str:
    """List favorite dashboards."""
    try:
        client = get_client(ctx)
        result = client.get_favorite_dashboards(page=page, page_size=page_size)
        return _json(result)
    except Exception as e:
        logger.exception("get_favorite_dashboards failed")
        return f"Error listing favorite dashboards: {e}"


@mcp.tool()
async def add_dashboard_favorite(ctx: Context, dashboard_id: int) -> str:
    """Add a dashboard to favorites."""
    try:
        client = get_client(ctx)
        result = client.add_dashboard_favorite(dashboard_id)
        return _json(result)
    except Exception as e:
        logger.exception("add_dashboard_favorite failed")
        return f"Error adding dashboard {dashboard_id} to favorites: {e}"


@mcp.tool()
async def remove_dashboard_favorite(ctx: Context, dashboard_id: int) -> str:
    """Remove a dashboard from favorites."""
    try:
        client = get_client(ctx)
        result = client.remove_dashboard_favorite(dashboard_id)
        return _json(result)
    except Exception as e:
        logger.exception("remove_dashboard_favorite failed")
        return f"Error removing dashboard {dashboard_id} from favorites: {e}"


@mcp.tool()
async def get_dashboard_tags(ctx: Context) -> str:
    """List all dashboard tags."""
    try:
        client = get_client(ctx)
        result = client.get_dashboard_tags()
        return _json(result)
    except Exception as e:
        logger.exception("get_dashboard_tags failed")
        return "Error getting dashboard tags"


# --- Visualization tools ---


@mcp.tool()
async def get_visualization(ctx: Context, visualization_id: int) -> str:
    """Get a visualization by ID."""
    try:
        client = get_client(ctx)
        result = client.get_visualization(visualization_id)
        return _json(result)
    except Exception as e:
        logger.exception("get_visualization failed")
        return f"Error getting visualization {visualization_id}: {e}"


@mcp.tool()
async def create_visualization(
    ctx: Context,
    query_id: int,
    type: str,
    name: str,
    description: str | None = None,
    options: str = "{}",
) -> str:
    """Create a visualization for a query. options: JSON object."""
    try:
        client = get_client(ctx)
        opts = json.loads(options)
        result = client.create_visualization(
            query_id=query_id,
            type=type,
            name=name,
            description=description,
            options=opts,
        )
        return _json(result)
    except Exception as e:
        logger.exception("create_visualization failed")
        return f"Error creating visualization: {e}"


@mcp.tool()
async def update_visualization(
    ctx: Context,
    visualization_id: int,
    type: str | None = None,
    name: str | None = None,
    description: str | None = None,
    options: str | None = None,
) -> str:
    """Update a visualization. Pass only fields to update. options: JSON string."""
    try:
        client = get_client(ctx)
        kwargs = {}
        if type is not None:
            kwargs["type"] = type
        if name is not None:
            kwargs["name"] = name
        if description is not None:
            kwargs["description"] = description
        if options is not None:
            kwargs["options"] = json.loads(options)
        result = client.update_visualization(visualization_id, **kwargs)
        return _json(result)
    except Exception as e:
        logger.exception("update_visualization failed")
        return f"Error updating visualization {visualization_id}: {e}"


@mcp.tool()
async def delete_visualization(ctx: Context, visualization_id: int) -> str:
    """Delete a visualization."""
    try:
        client = get_client(ctx)
        client.delete_visualization(visualization_id)
        return f"Visualization {visualization_id} deleted successfully"
    except Exception as e:
        logger.exception("delete_visualization failed")
        return f"Error deleting visualization {visualization_id}: {e}"


# --- Alert tools ---


@mcp.tool()
async def list_alerts(ctx: Context) -> str:
    """List all Redash alerts."""
    try:
        client = get_client(ctx)
        result = client.get_alerts()
        return _json(result)
    except Exception as e:
        logger.exception("list_alerts failed")
        return f"Error listing alerts: {e}"


@mcp.tool()
async def get_alert(ctx: Context, alert_id: int) -> str:
    """Get an alert by ID."""
    try:
        client = get_client(ctx)
        result = client.get_alert(alert_id)
        return _json(result)
    except Exception as e:
        logger.exception("get_alert failed")
        return f"Error getting alert {alert_id}: {e}"


@mcp.tool()
async def create_alert(
    ctx: Context,
    name: str,
    query_id: int,
    options: str,
    rearm: int | None = None,
) -> str:
    """Create an alert. options: JSON with column, op, value (e.g. {"column":"count","op":">","value":0})."""
    try:
        client = get_client(ctx)
        opts = json.loads(options)
        result = client.create_alert(
            name=name,
            query_id=query_id,
            options=opts,
            rearm=rearm,
        )
        return _json(result)
    except Exception as e:
        logger.exception("create_alert failed")
        return f"Error creating alert: {e}"


@mcp.tool()
async def update_alert(
    ctx: Context,
    alert_id: int,
    name: str | None = None,
    query_id: int | None = None,
    options: str | None = None,
    rearm: int | None = None,
) -> str:
    """Update an alert. options: JSON string."""
    try:
        client = get_client(ctx)
        kwargs = {}
        if name is not None:
            kwargs["name"] = name
        if query_id is not None:
            kwargs["query_id"] = query_id
        if options is not None:
            kwargs["options"] = json.loads(options)
        if rearm is not None:
            kwargs["rearm"] = rearm
        result = client.update_alert(alert_id, **kwargs)
        return _json(result)
    except Exception as e:
        logger.exception("update_alert failed")
        return f"Error updating alert {alert_id}: {e}"


@mcp.tool()
async def delete_alert(ctx: Context, alert_id: int) -> str:
    """Delete an alert."""
    try:
        client = get_client(ctx)
        result = client.delete_alert(alert_id)
        return _json(result)
    except Exception as e:
        logger.exception("delete_alert failed")
        return f"Error deleting alert {alert_id}: {e}"


@mcp.tool()
async def mute_alert(ctx: Context, alert_id: int) -> str:
    """Mute an alert."""
    try:
        client = get_client(ctx)
        result = client.mute_alert(alert_id)
        return _json(result)
    except Exception as e:
        logger.exception("mute_alert failed")
        return f"Error muting alert {alert_id}: {e}"


@mcp.tool()
async def get_alert_subscriptions(ctx: Context, alert_id: int) -> str:
    """Get subscriptions for an alert."""
    try:
        client = get_client(ctx)
        result = client.get_alert_subscriptions(alert_id)
        return _json(result)
    except Exception as e:
        logger.exception("get_alert_subscriptions failed")
        return f"Error getting alert {alert_id} subscriptions: {e}"


@mcp.tool()
async def add_alert_subscription(
    ctx: Context,
    alert_id: int,
    destination_id: int | None = None,
) -> str:
    """Add a subscription to an alert (e.g. current user)."""
    try:
        client = get_client(ctx)
        result = client.add_alert_subscription(alert_id, destination_id=destination_id)
        return _json(result)
    except Exception as e:
        logger.exception("add_alert_subscription failed")
        return f"Error adding subscription to alert {alert_id}: {e}"


@mcp.tool()
async def remove_alert_subscription(
    ctx: Context,
    alert_id: int,
    subscription_id: int,
) -> str:
    """Remove a subscription from an alert."""
    try:
        client = get_client(ctx)
        result = client.remove_alert_subscription(alert_id, subscription_id)
        return _json(result)
    except Exception as e:
        logger.exception("remove_alert_subscription failed")
        return f"Error removing subscription {subscription_id} from alert {alert_id}: {e}"


def main() -> None:
    """Run the Redash MCP server (stdio transport)."""
    mcp.run(transport="stdio")
