"""
Integration Factory for ag3ntwerk Tools.

Provides a unified way to create and manage integrations with proper configuration.
"""

import logging
from typing import Any, Callable, Dict, Optional, Type, TypeVar
from functools import lru_cache

from ag3ntwerk.tools.config import get_config_manager, IntegrationConfig
from ag3ntwerk.tools.exceptions import (
    IntegrationError,
    IntegrationNotConfiguredError,
    IntegrationAuthError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class IntegrationFactory:
    """
    Factory for creating configured integration instances.

    Handles:
    - Configuration injection
    - Credential management
    - Instance caching
    - Error handling

    Example:
        factory = get_integration_factory()

        # Get a configured Slack integration
        slack = factory.get("slack")

        # Or with custom config
        slack = factory.get("slack", bot_token="xoxb-...")
    """

    _instance: Optional["IntegrationFactory"] = None

    def __init__(self):
        self._instances: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._register_defaults()

    @classmethod
    def get_instance(cls) -> "IntegrationFactory":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _register_defaults(self) -> None:
        """Register default integration factories."""
        # Communication
        self.register("slack", self._create_slack)
        self.register("discord", self._create_discord)
        self.register("email", self._create_email)
        self.register("calendar", self._create_calendar)
        self.register("notion", self._create_notion)

        # Data
        self.register("sql", self._create_sql)
        self.register("dataframes", self._create_dataframes)
        self.register("visualization", self._create_visualization)
        self.register("spreadsheets", self._create_spreadsheets)

        # DevOps
        self.register("github", self._create_github)
        self.register("docker", self._create_docker)
        self.register("cloud", self._create_cloud)

        # Research
        self.register("scraping", self._create_scraping)
        self.register("news", self._create_news)
        self.register("papers", self._create_papers)

        # Business
        self.register("crm", self._create_crm)
        self.register("payments", self._create_payments)
        self.register("projects", self._create_projects)
        self.register("workflows", self._create_workflows)

        # Documents
        self.register("pdf", self._create_pdf)
        self.register("ocr", self._create_ocr)
        self.register("generator", self._create_generator)

    def register(
        self,
        name: str,
        factory: Callable[[Optional[IntegrationConfig]], Any],
    ) -> None:
        """Register an integration factory."""
        self._factories[name] = factory
        logger.debug(f"Registered integration factory: {name}")

    def get(
        self,
        name: str,
        cached: bool = True,
        **overrides,
    ) -> Any:
        """
        Get an integration instance.

        Args:
            name: Integration name
            cached: Whether to use cached instance
            **overrides: Override configuration values

        Returns:
            Configured integration instance

        Raises:
            IntegrationNotConfiguredError: If integration is not configured
        """
        # Check for cached instance
        cache_key = f"{name}:{hash(frozenset(overrides.items()))}"
        if cached and cache_key in self._instances:
            return self._instances[cache_key]

        # Get factory
        factory = self._factories.get(name)
        if not factory:
            raise IntegrationError(
                message=f"Unknown integration: {name}",
                integration_name=name,
            )

        # Get config
        config_manager = get_config_manager()
        config = config_manager.get_integration(name)

        # Apply overrides
        if overrides:
            if config is None:
                config = IntegrationConfig(name=name)
            # Clone and override
            config = IntegrationConfig(
                name=config.name,
                enabled=config.enabled,
                credentials={**config.credentials, **overrides},
                settings=config.settings,
            )

        # Check if enabled
        if config and not config.enabled:
            raise IntegrationError(
                message=f"Integration '{name}' is disabled",
                integration_name=name,
            )

        # Create instance
        try:
            instance = factory(config)
            if cached:
                self._instances[cache_key] = instance
            return instance
        except IntegrationNotConfiguredError:
            raise
        except Exception as e:
            raise IntegrationError(
                message=f"Failed to create integration '{name}': {e}",
                integration_name=name,
                cause=e,
            )

    def clear_cache(self, name: Optional[str] = None) -> None:
        """Clear cached instances."""
        if name:
            keys_to_remove = [k for k in self._instances if k.startswith(f"{name}:")]
            for key in keys_to_remove:
                del self._instances[key]
        else:
            self._instances.clear()

    # Integration factory methods

    def _create_slack(self, config: Optional[IntegrationConfig]) -> Any:
        """Create Slack integration."""
        try:
            from ag3ntwerk.integrations.communication.slack import SlackIntegration, SlackConfig

            if config:
                bot_token = config.get_credential("bot_token")
                app_token = config.get_credential("app_token")

                if bot_token:
                    slack_config = SlackConfig(
                        bot_token=bot_token,
                        app_token=app_token,
                    )
                    return SlackIntegration(config=slack_config)

            # Try environment variables
            return SlackIntegration()

        except ImportError:
            raise IntegrationNotConfiguredError(
                integration_name="slack",
                required_config=["slack-sdk package"],
            )

    def _create_discord(self, config: Optional[IntegrationConfig]) -> Any:
        """Create Discord integration."""
        try:
            from ag3ntwerk.integrations.communication.discord import DiscordIntegration, DiscordConfig

            if config:
                bot_token = config.get_credential("bot_token")
                if bot_token:
                    discord_config = DiscordConfig(bot_token=bot_token)
                    return DiscordIntegration(config=discord_config)

            return DiscordIntegration()

        except ImportError:
            raise IntegrationNotConfiguredError(
                integration_name="discord",
                required_config=["discord.py package"],
            )

    def _create_email(self, config: Optional[IntegrationConfig]) -> Any:
        """Create Email integration."""
        try:
            from ag3ntwerk.integrations.communication.email import EmailIntegration, EmailConfig

            if config:
                email_config = EmailConfig(
                    smtp_host=config.get_setting("smtp_host", "smtp.gmail.com"),
                    smtp_port=config.get_setting("smtp_port", 587),
                    username=config.get_credential("username", ""),
                    password=config.get_credential("password", ""),
                    use_tls=config.get_setting("use_tls", True),
                )
                return EmailIntegration(config=email_config)

            return EmailIntegration()

        except ImportError:
            raise IntegrationNotConfiguredError(
                integration_name="email",
                required_config=["aiosmtplib package"],
            )

    def _create_calendar(self, config: Optional[IntegrationConfig]) -> Any:
        """Create Calendar integration."""
        try:
            from ag3ntwerk.integrations.communication.calendar import (
                CalendarIntegration,
                CalendarConfig,
            )

            if config:
                calendar_config = CalendarConfig(
                    provider=config.get_setting("provider", "google"),
                    credentials_file=config.get_credential("credentials_file", ""),
                )
                return CalendarIntegration(config=calendar_config)

            return CalendarIntegration()

        except ImportError:
            raise IntegrationNotConfiguredError(
                integration_name="calendar",
                required_config=["google-api-python-client package"],
            )

    def _create_notion(self, config: Optional[IntegrationConfig]) -> Any:
        """Create Notion integration."""
        try:
            from ag3ntwerk.integrations.communication.notion import NotionIntegration, NotionConfig

            if config:
                api_key = config.get_credential("api_key")
                if api_key:
                    notion_config = NotionConfig(api_key=api_key)
                    return NotionIntegration(config=notion_config)

            return NotionIntegration()

        except ImportError:
            raise IntegrationNotConfiguredError(
                integration_name="notion",
                required_config=["notion-client package"],
            )

    def _create_sql(self, config: Optional[IntegrationConfig]) -> Any:
        """Create SQL integration."""
        try:
            from ag3ntwerk.integrations.data.sql import SQLIntegration

            connection_string = None
            if config:
                connection_string = config.get_credential("connection_string")

            return SQLIntegration(connection_string=connection_string or "")

        except ImportError:
            raise IntegrationNotConfiguredError(
                integration_name="sql",
                required_config=["sqlalchemy package"],
            )

    def _create_dataframes(self, config: Optional[IntegrationConfig]) -> Any:
        """Create DataFrames integration."""
        try:
            from ag3ntwerk.integrations.data.dataframes import DataFrameIntegration

            engine = "pandas"
            if config:
                engine = config.get_setting("engine", "pandas")

            return DataFrameIntegration(engine=engine)

        except ImportError:
            raise IntegrationNotConfiguredError(
                integration_name="dataframes",
                required_config=["pandas or polars package"],
            )

    def _create_visualization(self, config: Optional[IntegrationConfig]) -> Any:
        """Create Visualization integration."""
        try:
            from ag3ntwerk.integrations.data.visualization import VisualizationIntegration

            return VisualizationIntegration()

        except ImportError:
            raise IntegrationNotConfiguredError(
                integration_name="visualization",
                required_config=["matplotlib or plotly package"],
            )

    def _create_spreadsheets(self, config: Optional[IntegrationConfig]) -> Any:
        """Create Spreadsheets integration."""
        try:
            from ag3ntwerk.integrations.data.spreadsheets import SpreadsheetIntegration

            return SpreadsheetIntegration()

        except ImportError:
            raise IntegrationNotConfiguredError(
                integration_name="spreadsheets",
                required_config=["openpyxl package"],
            )

    def _create_github(self, config: Optional[IntegrationConfig]) -> Any:
        """Create GitHub integration."""
        try:
            from ag3ntwerk.integrations.devops.github import GitHubIntegration, GitHubConfig

            if config:
                token = config.get_credential("token")
                if token:
                    github_config = GitHubConfig(token=token)
                    return GitHubIntegration(config=github_config)

            return GitHubIntegration()

        except ImportError:
            raise IntegrationNotConfiguredError(
                integration_name="github",
                required_config=["PyGithub package"],
            )

    def _create_docker(self, config: Optional[IntegrationConfig]) -> Any:
        """Create Docker integration."""
        try:
            from ag3ntwerk.integrations.devops.docker import DockerIntegration

            return DockerIntegration()

        except ImportError:
            raise IntegrationNotConfiguredError(
                integration_name="docker",
                required_config=["docker package"],
            )

    def _create_cloud(self, config: Optional[IntegrationConfig]) -> Any:
        """Create Cloud integration."""
        try:
            from ag3ntwerk.integrations.devops.cloud import CloudIntegration

            provider = "aws"
            if config:
                provider = config.get_setting("provider", "aws")

            return CloudIntegration(provider=provider)

        except ImportError:
            raise IntegrationNotConfiguredError(
                integration_name="cloud",
                required_config=["boto3 or google-cloud package"],
            )

    def _create_scraping(self, config: Optional[IntegrationConfig]) -> Any:
        """Create Scraping integration."""
        try:
            from ag3ntwerk.integrations.research.scraping import ScrapingIntegration

            return ScrapingIntegration()

        except ImportError:
            raise IntegrationNotConfiguredError(
                integration_name="scraping",
                required_config=["playwright package"],
            )

    def _create_news(self, config: Optional[IntegrationConfig]) -> Any:
        """Create News integration."""
        try:
            from ag3ntwerk.integrations.research.news import NewsIntegration, NewsConfig

            if config:
                api_key = config.get_credential("api_key")
                if api_key:
                    news_config = NewsConfig(api_key=api_key)
                    return NewsIntegration(config=news_config)

            return NewsIntegration()

        except ImportError:
            raise IntegrationNotConfiguredError(
                integration_name="news",
                required_config=["newsapi-python or feedparser package"],
            )

    def _create_papers(self, config: Optional[IntegrationConfig]) -> Any:
        """Create Papers integration."""
        try:
            from ag3ntwerk.integrations.research.papers import PapersIntegration

            return PapersIntegration()

        except ImportError:
            raise IntegrationNotConfiguredError(
                integration_name="papers",
                required_config=["arxiv package"],
            )

    def _create_crm(self, config: Optional[IntegrationConfig]) -> Any:
        """Create CRM integration."""
        try:
            from ag3ntwerk.integrations.business.crm import CRMIntegration, CRMConfig, CRMProvider

            if config:
                provider_name = config.get_setting("provider", "hubspot")
                api_key = config.get_credential("api_key")

                provider = CRMProvider(provider_name)
                crm_config = CRMConfig(
                    provider=provider,
                    api_key=api_key or "",
                )
                return CRMIntegration(config=crm_config)

            return CRMIntegration()

        except ImportError:
            raise IntegrationNotConfiguredError(
                integration_name="crm",
                required_config=["hubspot-api-client or salesforce package"],
            )

    def _create_payments(self, config: Optional[IntegrationConfig]) -> Any:
        """Create Payments integration."""
        try:
            from ag3ntwerk.integrations.business.payments import PaymentsIntegration, PaymentsConfig

            if config:
                api_key = config.get_credential("api_key")
                if api_key:
                    payments_config = PaymentsConfig(api_key=api_key)
                    return PaymentsIntegration(config=payments_config)

            return PaymentsIntegration()

        except ImportError:
            raise IntegrationNotConfiguredError(
                integration_name="payments",
                required_config=["stripe package"],
            )

    def _create_projects(self, config: Optional[IntegrationConfig]) -> Any:
        """Create Projects integration."""
        try:
            from ag3ntwerk.integrations.business.projects import (
                ProjectsIntegration,
                ProjectsConfig,
                ProjectProvider,
            )

            if config:
                provider_name = config.get_setting("provider", "jira")
                provider = ProjectProvider(provider_name)

                projects_config = ProjectsConfig(
                    provider=provider,
                    api_key=config.get_credential("api_key", ""),
                    domain=config.get_setting("domain", ""),
                    email=config.get_credential("email", ""),
                )
                return ProjectsIntegration(config=projects_config)

            return ProjectsIntegration()

        except ImportError:
            raise IntegrationNotConfiguredError(
                integration_name="projects",
                required_config=["jira or linear package"],
            )

    def _create_workflows(self, config: Optional[IntegrationConfig]) -> Any:
        """Create Workflows integration."""
        try:
            from ag3ntwerk.integrations.business.workflows import WorkflowIntegration, WorkflowProvider

            provider = WorkflowProvider.ZAPIER
            if config:
                provider_name = config.get_setting("provider", "zapier")
                provider = WorkflowProvider(provider_name)

                return WorkflowIntegration(
                    provider=provider,
                    n8n_url=config.get_setting("n8n_url", "http://localhost:5678"),
                    n8n_api_key=config.get_credential("n8n_api_key", ""),
                )

            return WorkflowIntegration(provider=provider)

        except ImportError:
            raise IntegrationNotConfiguredError(
                integration_name="workflows",
                required_config=["aiohttp package"],
            )

    def _create_pdf(self, config: Optional[IntegrationConfig]) -> Any:
        """Create PDF integration."""
        try:
            from ag3ntwerk.integrations.documents.pdf import PDFIntegration

            return PDFIntegration()

        except ImportError:
            raise IntegrationNotConfiguredError(
                integration_name="pdf",
                required_config=["pypdf and reportlab packages"],
            )

    def _create_ocr(self, config: Optional[IntegrationConfig]) -> Any:
        """Create OCR integration."""
        try:
            from ag3ntwerk.integrations.documents.ocr import OCRIntegration, OCRConfig

            if config:
                ocr_config = OCRConfig(
                    tesseract_cmd=config.get_setting("tesseract_cmd", ""),
                    language=config.get_setting("language", "eng"),
                )
                return OCRIntegration(config=ocr_config)

            return OCRIntegration()

        except ImportError:
            raise IntegrationNotConfiguredError(
                integration_name="ocr",
                required_config=["pytesseract and pillow packages"],
            )

    def _create_generator(self, config: Optional[IntegrationConfig]) -> Any:
        """Create Document Generator integration."""
        try:
            from ag3ntwerk.integrations.documents.generator import DocumentGenerator

            return DocumentGenerator()

        except ImportError:
            raise IntegrationNotConfiguredError(
                integration_name="generator",
                required_config=["python-docx and jinja2 packages"],
            )


def get_integration_factory() -> IntegrationFactory:
    """Get the global integration factory instance."""
    return IntegrationFactory.get_instance()


def get_integration(name: str, **overrides) -> Any:
    """
    Convenience function to get an integration.

    Example:
        slack = get_integration("slack")
        github = get_integration("github", token="ghp_...")
    """
    return get_integration_factory().get(name, **overrides)
