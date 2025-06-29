import asyncio
from typing import Dict, Optional
import structlog

from wyrm.models.config import AppConfig
from wyrm.models.scrape import SidebarStructure

class Runner:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.logger = structlog.get_logger(__name__)

    async def run_scraping_workflow(
        self,
        config_path: str,
        headless: Optional[bool] = None,
        log_level: Optional[str] = None,
        save_structure: bool = False,
        save_html: bool = False,
        debug: bool = False,
        max_expand_attempts: Optional[int] = None,
        force: bool = False,
        test_item_id: Optional[str] = None,
        max_items: Optional[int] = None,
        resume_info: bool = False,
        structure_filename: Optional[str] = None,
        html_filename: Optional[str] = None,
        force_full_expansion: bool = False,
    ) -> None:
        try:
            config = self.orchestrator.config_service.load_config(config_path)
            cli_args = {
                "headless": headless,
                "log_level": log_level,
                "max_expand_attempts": max_expand_attempts,
                "force_full_expansion": force_full_expansion,
            }
            config = self.orchestrator.config_service.merge_cli_overrides(config, cli_args)

            self.orchestrator._config = config
            if debug:
                save_structure = True
                save_html = True
                self.logger.info("Debug mode enabled")

            config_values = self.orchestrator.config_service.extract_configuration_values(config)
            self.orchestrator._initialize_endpoint_aware_services(config)
            self.orchestrator.config_service.setup_directories(config_values)

            sidebar_structure, from_cache = await self.orchestrator.structure_handler.handle_sidebar_structure(
                config, config_values, save_structure, save_html,
                structure_filename, html_filename, resume_info, force
            )

            await self.orchestrator.item_processor.process_items_from_structure(
                sidebar_structure, config_values, force,
                test_item_id, max_items, resume_info, from_cache
            )

        except KeyboardInterrupt:
            self.logger.warning("User interrupted execution")
            raise
        except Exception as e:
            self.logger.exception("An unexpected error occurred", error=str(e))
            raise
        finally:
            await self.orchestrator._cleanup()
