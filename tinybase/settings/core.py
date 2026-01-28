"""
Runtime settings from database. Cached in memory, invalidated on any change.

Core settings are defined as class properties that return actual values.
Extension settings are accessed via get() and return AppSetting objects.

Usage:
    from tinybase.settings import settings

    # Core settings via properties (IDE autocompletion, returns actual values)
    settings.instance_name          # Returns "TinyBase" (str)
    settings.storage.enabled        # Returns False (bool)
    settings.auth.portal.enabled    # Returns False (bool)
    settings.jobs.admin_report.enabled  # Returns True (bool)

    # Extension/any settings via get() (returns AppSetting object)
    settings.get("ext.my_extension.api_key")  # Returns AppSetting | None
    settings.get("core.instance_name")        # Returns AppSetting | None

    # Get all settings
    settings.get_all()              # Returns dict[str, AppSetting]
    settings.get_all(flat=True)     # Returns dict[str, Any] (values only)

    # Set any setting (core or extension)
    settings.set("core.instance_name", "My App")
    settings.set("ext.my_extension.api_key", "xxx")
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tinybase.db.models import AppSetting

logger = logging.getLogger(__name__)


def _deserialize_value(value: str | None, value_type: str) -> Any:
    """Deserialize a JSON-encoded value based on its type."""
    if value is None:
        return None

    if value_type == "str":
        return value
    elif value_type == "int":
        return int(value)
    elif value_type == "bool":
        return value.lower() in ("true", "1", "yes")
    elif value_type == "float":
        return float(value)
    elif value_type == "json":
        return json.loads(value)
    elif value_type == "datetime":
        return datetime.fromisoformat(value)
    else:
        # Default: try to parse as JSON
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value


def _serialize_value(value: Any) -> tuple[str, str]:
    """Serialize a value to JSON string and determine its type."""
    if value is None:
        return ("null", "str")
    elif isinstance(value, bool):
        return ("true" if value else "false", "bool")
    elif isinstance(value, int):
        return (str(value), "int")
    elif isinstance(value, float):
        return (str(value), "float")
    elif isinstance(value, str):
        return (value, "str")
    elif isinstance(value, datetime):
        return (value.isoformat(), "datetime")
    else:
        # Complex types: serialize as JSON
        return (json.dumps(value), "json")


class Settings:
    """
    Runtime settings accessor with caching.

    Core settings: properties that return actual typed values (str, bool, int, etc.)
    Extension settings: get() method returns AppSetting objects
    """

    _cache: dict[str, AppSetting]
    _loaded: bool

    def __init__(self) -> None:
        self._cache = {}
        self._loaded = False

    def load(self) -> None:
        """Load all settings from database into cache."""
        from sqlmodel import Session, select

        from tinybase.db.core import get_db_engine
        from tinybase.db.models import AppSetting

        engine = get_db_engine()
        with Session(engine) as session:
            stmt = select(AppSetting)
            results = session.exec(stmt).all()

            self._cache = {}
            for app_setting in results:
                # Deserialize value
                app_setting.value = _deserialize_value(app_setting.value, app_setting.value_type)
                self._cache[app_setting.key] = app_setting

            self._loaded = True
            logger.info(f"Loaded {len(self._cache)} settings from database")

    def reload(self) -> None:
        """Reload cache. Call after any AppSetting change."""
        self._cache.clear()
        self._loaded = False
        self.load()

    def _get_value(self, key: str, default: Any) -> Any:
        """Get setting value from cache, or return default. Used by properties."""
        if not self._loaded:
            self.load()
        if key in self._cache:
            return self._cache[key].value
        return default

    def get(self, key: str) -> AppSetting | None:
        """Get any setting by key as AppSetting object. Returns None if not found."""
        if not self._loaded:
            self.load()
        return self._cache.get(key)

    def set(self, key: str, value: Any) -> AppSetting:
        """Set a setting value. Validates prefix, writes to DB, reloads cache."""
        if not key.startswith(("core.", "ext.")):
            raise ValueError("Key must start with 'core.' or 'ext.'")

        from sqlmodel import Session

        from tinybase.db.core import get_db_engine
        from tinybase.db.models import AppSetting
        from tinybase.utils import utcnow

        # Serialize value
        value_str, value_type = _serialize_value(value)

        engine = get_db_engine()
        with Session(engine) as session:
            app_setting = session.get(AppSetting, key)

            if app_setting is None:
                # Create new setting
                app_setting = AppSetting(
                    key=key,
                    value=value_str,
                    value_type=value_type,
                    created_at=utcnow(),
                    updated_at=utcnow(),
                )
                session.add(app_setting)
            else:
                # Update existing setting
                app_setting.value = value_str
                app_setting.value_type = value_type
                app_setting.updated_at = utcnow()

            session.commit()
            session.refresh(app_setting)

            # Deserialize for cache
            app_setting.value = _deserialize_value(app_setting.value, app_setting.value_type)
            session.expunge(app_setting)

        # Reload cache
        self.reload()

        return app_setting

    def delete(self, key: str) -> None:
        """Delete a setting. Reloads cache."""
        from sqlmodel import Session

        from tinybase.db.core import get_db_engine
        from tinybase.db.models import AppSetting

        engine = get_db_engine()
        with Session(engine) as session:
            app_setting = session.get(AppSetting, key)
            if app_setting is not None:
                session.delete(app_setting)
                session.commit()

        # Reload cache
        self.reload()

    def get_all(self, flat: bool = False) -> dict[str, AppSetting] | dict[str, Any]:
        """
        Get all settings.

        Args:
            flat: If True, returns dict[str, Any] with just values.
                  If False (default), returns dict[str, AppSetting].
        """
        if not self._loaded:
            self.load()
        if flat:
            return {k: v.value for k, v in self._cache.items()}
        return dict(self._cache)

    # ─────────────────────────────────────────────────────────────────
    # Core settings - properties that return actual typed values
    # ─────────────────────────────────────────────────────────────────

    @property
    def instance_name(self) -> str:
        return self._get_value("core.instance_name", "TinyBase")

    @property
    def server_timezone(self) -> str:
        return self._get_value("core.server_timezone", "UTC")

    @property
    def auth(self) -> AuthSettings:
        return AuthSettings(self)

    @property
    def storage(self) -> StorageSettings:
        return StorageSettings(self)

    @property
    def scheduler(self) -> SchedulerSettings:
        return SchedulerSettings(self)

    @property
    def jobs(self) -> JobsSettings:
        return JobsSettings(self)

    @property
    def limits(self) -> LimitsSettings:
        return LimitsSettings(self)


# ─────────────────────────────────────────────────────────────────────────
# Nested accessor classes for grouped settings (return actual values)
# ─────────────────────────────────────────────────────────────────────────


class AuthSettings:
    def __init__(self, s: Settings) -> None:
        self._s = s

    @property
    def allow_public_registration(self) -> bool:
        return self._s._get_value("core.auth.allow_public_registration", True)

    @property
    def portal(self) -> AuthPortalSettings:
        return AuthPortalSettings(self._s)


class AuthPortalSettings:
    def __init__(self, s: Settings) -> None:
        self._s = s

    @property
    def enabled(self) -> bool:
        return self._s._get_value("core.auth.portal.enabled", False)

    @property
    def logo_url(self) -> str | None:
        return self._s._get_value("core.auth.portal.logo_url", None)

    @property
    def primary_color(self) -> str | None:
        return self._s._get_value("core.auth.portal.primary_color", None)

    @property
    def background_image_url(self) -> str | None:
        return self._s._get_value("core.auth.portal.background_image_url", None)

    @property
    def login_redirect_url(self) -> str | None:
        return self._s._get_value("core.auth.portal.login_redirect_url", None)

    @property
    def register_redirect_url(self) -> str | None:
        return self._s._get_value("core.auth.portal.register_redirect_url", None)


class StorageSettings:
    def __init__(self, s: Settings) -> None:
        self._s = s

    @property
    def enabled(self) -> bool:
        return self._s._get_value("core.storage.enabled", False)

    @property
    def url(self) -> str | None:
        return self._s._get_value("core.storage.url", None)

    @property
    def bucket(self) -> str | None:
        return self._s._get_value("core.storage.bucket", None)

    @property
    def access_key(self) -> str | None:
        return self._s._get_value("core.storage.access_key", None)

    @property
    def secret_key(self) -> str | None:
        return self._s._get_value("core.storage.secret_key", None)

    @property
    def region(self) -> str | None:
        return self._s._get_value("core.storage.region", None)


class SchedulerSettings:
    def __init__(self, s: Settings) -> None:
        self._s = s

    @property
    def function_timeout_seconds(self) -> int:
        return self._s._get_value("core.scheduler.function_timeout_seconds", 1800)

    @property
    def max_schedules_per_tick(self) -> int:
        return self._s._get_value("core.scheduler.max_schedules_per_tick", 100)

    @property
    def max_concurrent_executions(self) -> int:
        return self._s._get_value("core.scheduler.max_concurrent_executions", 10)


class JobsSettings:
    def __init__(self, s: Settings) -> None:
        self._s = s

    @property
    def token_cleanup(self) -> TokenCleanupJobSettings:
        return TokenCleanupJobSettings(self._s)

    @property
    def metrics(self) -> MetricsJobSettings:
        return MetricsJobSettings(self._s)

    @property
    def admin_report(self) -> AdminReportJobSettings:
        return AdminReportJobSettings(self._s)


class TokenCleanupJobSettings:
    def __init__(self, s: Settings) -> None:
        self._s = s

    @property
    def interval(self) -> int:
        return self._s._get_value("core.jobs.token_cleanup.interval", 60)


class MetricsJobSettings:
    def __init__(self, s: Settings) -> None:
        self._s = s

    @property
    def interval(self) -> int:
        return self._s._get_value("core.jobs.metrics.interval", 360)


class AdminReportJobSettings:
    def __init__(self, s: Settings) -> None:
        self._s = s

    @property
    def enabled(self) -> bool:
        return self._s._get_value("core.jobs.admin_report.enabled", True)

    @property
    def interval_days(self) -> int:
        return self._s._get_value("core.jobs.admin_report.interval_days", 7)


class LimitsSettings:
    def __init__(self, s: Settings) -> None:
        self._s = s

    @property
    def max_concurrent_functions_per_user(self) -> int:
        return self._s._get_value("core.limits.max_concurrent_functions_per_user", 10)


settings = Settings()  # Singleton instance
