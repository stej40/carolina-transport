from collections.abc import Iterator
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import (
    DEV_BOOTSTRAP_PASSWORD,
    DEV_SECRET_PLACEHOLDER,
    Settings,
    _resolve_env_profile,
    get_settings,
)

API_DIR = Path(__file__).resolve().parents[1]

_ALL_SETTING_VARS = (
    "APP_ENV",
    "DEBUG",
    "DATABASE_URL",
    "SECRET_KEY",
    "ACCESS_TOKEN_TTL_MIN",
    "REFRESH_TOKEN_TTL_DAYS",
    "S3_ENDPOINT",
    "S3_ACCESS_KEY",
    "S3_SECRET_KEY",
    "S3_BUCKET",
    "S3_REGION",
    "PRESIGN_TTL_SEC",
    "CORS_ORIGINS",
    "BOOTSTRAP_ADMIN_EMAIL",
    "BOOTSTRAP_ADMIN_PASSWORD",
)

_EXPECTED_EXAMPLE_KEYS = frozenset(_ALL_SETTING_VARS)

_VALID_PROD_SECRET = "x" * 40
_VALID_PROD_BOOTSTRAP = "correct-horse-battery-staple"


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.chdir(tmp_path)
    for var in _ALL_SETTING_VARS:
        monkeypatch.delenv(var, raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class TestProfileSelection:
    def test_helper_maps_profiles(self, monkeypatch: pytest.MonkeyPatch) -> None:
        profile, env_file = _resolve_env_profile()
        assert (profile, env_file) == ("local", Path(".env.local"))
        monkeypatch.setenv("APP_ENV", "prod")
        profile, env_file = _resolve_env_profile()
        assert (profile, env_file) == ("prod", Path(".env.prod"))

    def test_unknown_profile_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("APP_ENV", "staging")
        with pytest.raises(ValueError, match="staging"):
            _resolve_env_profile()
        with pytest.raises(ValueError, match="not a valid profile"):
            get_settings()

    def test_default_profile_loads_env_local(self, tmp_path: Path) -> None:
        (tmp_path / ".env.local").write_text(
            "DEBUG=true\nDATABASE_URL=postgresql+asyncpg://local:local@h:5432/db\n"
        )
        settings = get_settings()
        assert settings.app_env == "local"
        assert settings.debug is True
        assert settings.database_url == "postgresql+asyncpg://local:local@h:5432/db"

    def test_missing_local_file_falls_back_to_defaults(self) -> None:
        settings = get_settings()
        assert settings.app_env == "local"
        assert settings.debug is False
        assert settings.secret_key == DEV_SECRET_PLACEHOLDER

    def test_prod_loads_env_prod_and_ignores_env_local(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / ".env.local").write_text(
            "DATABASE_URL=postgresql+asyncpg://local:v@h/db1\nDEBUG=true\n"
        )
        (tmp_path / ".env.prod").write_text(
            "DATABASE_URL=postgresql+asyncpg://prod:v@h/db2\nDEBUG=false\n"
            f"SECRET_KEY={_VALID_PROD_SECRET}\nBOOTSTRAP_ADMIN_PASSWORD={_VALID_PROD_BOOTSTRAP}\n"
        )
        monkeypatch.setenv("APP_ENV", "prod")
        settings = get_settings()
        assert settings.app_env == "prod"
        assert settings.database_url.endswith("/db2")
        assert settings.debug is False


class TestPrecedence:
    def test_process_env_wins_over_dotenv(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / ".env.local").write_text("DATABASE_URL=postgresql+asyncpg://file:v@h/db\n")
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://process:v@h/db")
        assert get_settings().database_url.endswith("process:v@h/db")


class TestProdSafetyGuard:
    def test_prod_requires_env_file(self) -> None:
        with pytest.raises(ValidationError, match=r"\.env\.prod"):
            Settings(app_env="prod", secret_key=_VALID_PROD_SECRET)

    def test_prod_rejects_placeholder_secret(self, tmp_path: Path) -> None:
        (tmp_path / ".env.prod").write_text("DEBUG=false\n")
        with pytest.raises(ValidationError, match="SECRET_KEY"):
            Settings(app_env="prod", secret_key=DEV_SECRET_PLACEHOLDER)

    def test_prod_rejects_short_secret(self, tmp_path: Path) -> None:
        (tmp_path / ".env.prod").write_text("DEBUG=false\n")
        with pytest.raises(ValidationError, match="SECRET_KEY"):
            Settings(app_env="prod", secret_key="too-short")

    def test_prod_rejects_debug_enabled(self, tmp_path: Path) -> None:
        (tmp_path / ".env.prod").write_text("DEBUG=true\n")
        with pytest.raises(ValidationError, match="DEBUG must not be enabled"):
            Settings(app_env="prod", secret_key=_VALID_PROD_SECRET, debug=True)

    def test_valid_prod_settings_pass(self, tmp_path: Path) -> None:
        (tmp_path / ".env.prod").write_text("DEBUG=false\n")
        settings = Settings(
            app_env="prod",
            secret_key=_VALID_PROD_SECRET,
            bootstrap_admin_password=_VALID_PROD_BOOTSTRAP,
        )
        assert settings.debug is False

    def test_prod_rejects_placeholder_bootstrap_password(self, tmp_path: Path) -> None:
        (tmp_path / ".env.prod").write_text("DEBUG=false\n")
        with pytest.raises(ValidationError, match="BOOTSTRAP_ADMIN_PASSWORD"):
            Settings(
                app_env="prod",
                secret_key=_VALID_PROD_SECRET,
                bootstrap_admin_password=DEV_BOOTSTRAP_PASSWORD,
            )

    def test_prod_rejects_empty_bootstrap_password(self, tmp_path: Path) -> None:
        (tmp_path / ".env.prod").write_text("DEBUG=false\n")
        with pytest.raises(ValidationError, match="BOOTSTRAP_ADMIN_PASSWORD"):
            Settings(app_env="prod", secret_key=_VALID_PROD_SECRET, bootstrap_admin_password="")

    def test_prod_rejects_short_bootstrap_password(self, tmp_path: Path) -> None:
        (tmp_path / ".env.prod").write_text("DEBUG=false\n")
        with pytest.raises(ValidationError, match="BOOTSTRAP_ADMIN_PASSWORD"):
            Settings(
                app_env="prod", secret_key=_VALID_PROD_SECRET, bootstrap_admin_password="12345"
            )

    def test_prod_rejects_empty_bootstrap_email(self, tmp_path: Path) -> None:
        (tmp_path / ".env.prod").write_text("DEBUG=false\n")
        with pytest.raises(ValidationError, match="BOOTSTRAP_ADMIN_EMAIL"):
            Settings(
                app_env="prod",
                secret_key=_VALID_PROD_SECRET,
                bootstrap_admin_email="   ",
                bootstrap_admin_password=_VALID_PROD_BOOTSTRAP,
            )

    def test_prod_accepts_compliant_bootstrap_credentials(self, tmp_path: Path) -> None:
        (tmp_path / ".env.prod").write_text("DEBUG=false\n")
        settings = Settings(
            app_env="prod",
            secret_key=_VALID_PROD_SECRET,
            bootstrap_admin_email="root@agro-karolina.cz",
            bootstrap_admin_password=_VALID_PROD_BOOTSTRAP,
        )
        assert settings.bootstrap_admin_email == "root@agro-karolina.cz"

    def test_local_accepts_bootstrap_defaults(self) -> None:
        settings = get_settings()
        assert settings.app_env == "local"
        assert settings.bootstrap_admin_email == "systemadmin@example.local"
        assert settings.bootstrap_admin_password == DEV_BOOTSTRAP_PASSWORD


class TestExampleTemplates:
    @pytest.mark.parametrize("name", [".env.local.example", ".env.prod.example"])
    def test_examples_cover_all_settings_fields(self, name: str) -> None:
        text = (API_DIR / name).read_text()
        keys = {
            line.split("=", 1)[0].strip()
            for line in text.splitlines()
            if line.strip() and not line.lstrip().startswith("#") and "=" in line
        }
        assert keys == _EXPECTED_EXAMPLE_KEYS

    def test_local_example_boots_in_local_profile(self, tmp_path: Path) -> None:
        content = (API_DIR / ".env.local.example").read_text()
        (tmp_path / ".env.local").write_text(content)
        settings = get_settings()
        assert settings.debug is True

    def test_prod_example_boots_in_prod_profile(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        content = (API_DIR / ".env.prod.example").read_text()
        (tmp_path / ".env.prod").write_text(content)
        monkeypatch.setenv("APP_ENV", "prod")
        settings = get_settings()
        assert settings.app_env == "prod"
        assert settings.debug is False
