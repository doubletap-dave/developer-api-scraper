from typing import Dict, List, Optional
import structlog

from wyrm.models.scrape import SidebarStructure

class TaskQueue:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.logger = structlog.get_logger(__name__)

    async def process_items_from_structure(
        self,
        sidebar_structure: SidebarStructure,
        config_values: Dict,
        force: bool,
        test_item_id: Optional[str],
        max_items: Optional[int],
        resume_info: bool,
        from_cache: bool,
    ) -> None:
        valid_items = self.orchestrator.parsing_service._get_valid_items(sidebar_structure)
        items_to_process = self.orchestrator.item_processor.filter_items(valid_items, config_values, force, test_item_id, max_items)
        
        if resume_info:
            self.logger.info("Resume info requested", total_items=len(items_to_process))
            return
        
        await self.orchestrator.item_processor.process_items(items_to_process, config_values)
