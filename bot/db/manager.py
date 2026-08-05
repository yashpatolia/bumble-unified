from db.queries.api_usage import ApiUsageQueries
from db.queries.dyes import DyesQueries
from db.queries.guild_members import GuildMembersQueries
from db.queries.message_counts import MessageCountsQueries
from db.queries.panel_users import PanelUsersQueries
from db.queries.users import UsersQueries


class DatabaseManager(
    UsersQueries,
    DyesQueries,
    GuildMembersQueries,
    PanelUsersQueries,
    ApiUsageQueries,
    MessageCountsQueries,
):
    """Centralized PostgreSQL access via a threaded connection pool.

    Behavior lives in the per-domain mixins under db/queries/; this class just
    composes them. __init__ (which builds the pool) and the shared _cursor()
    contextmanager both come from BaseQueries via the mixin chain.
    """
