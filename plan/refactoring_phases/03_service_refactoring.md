# Refactoring Phase 3: Service-Oriented Refactoring
**Version**: `1.2.0`

## Objective
Convert existing functional modules (`driver_setup.py`, `navigation.py`, `storage.py`, `content_extractor.py`, `sidebar_parser.py`, `utils.py`) into proper service classes. This will fully align the codebase with the "Service-Layer-First" development model.

---

## 1. Plan of Attack
For each module, we will create a corresponding service class in the `wyrm/services/` directory. The original files will be removed after their logic has been successfully migrated.

## 2. Refactor `driver_setup.py`
*   **Action**: Create a `WebDriverManager` service.
*   **File**: `wyrm/services/driver_manager.py`
*   **Class**: `WebDriverManager`
    *   The `__init__` method will take configuration (e.g., headless mode, timeouts) as arguments.
    *   The `get_driver()` function will become a method of this class.
    *   Add a `close_driver()` method to properly quit the driver.
    *   The service should manage the state of the driver instance.
*   **Cleanup**: Delete `wyrm/driver_setup.py`.

## 3. Refactor `navigation.py`
*   **Action**: Create a `NavigationService`.
*   **File**: `wyrm/services/navigation_service.py`
*   **Class**: `NavigationService`
    *   The `__init__` will take the `WebDriver` instance as a dependency (Dependency Injection).
    *   All functions (`navigate_to_page`, `click_sidebar_item`, `expand_menu_containing_node`, etc.) will become methods of this class.
*   **Cleanup**: Delete `wyrm/navigation.py`.

## 4. Refactor `content_extractor.py` and `sidebar_parser.py`
*   **Action**: Combine these into a single `ScrapingService`.
*   **File**: `wyrm/services/scraping_service.py`
*   **Class**: `ScrapingService`
    *   `__init__` will take the `WebDriver` instance as a dependency.
    *   Methods will include `extract_content()`, `parse_sidebar()`, `get_all_item_ids()`, etc. Consolidating these makes sense as they both deal with parsing content from the driver.
*   **Cleanup**: Delete `wyrm/content_extractor.py` and `wyrm/sidebar_parser.py`.

## 5. Refactor `storage.py`
*   **Action**: Create a `StorageService`.
*   **File**: `wyrm/services/storage_service.py`
*   **Class**: `StorageService`
    *   `__init__` can take configuration like the output directory path.
    *   `save_content_to_file()` and `load_resume_info()` will become methods.
*   **Cleanup**: Delete `wyrm/storage.py`.

## 6. Refactor `utils.py`
*   **Action**: Create a `ConfigService` and move general utilities.
*   **File**: `wyrm/services/config_service.py`
    *   **Class**: `ConfigService` will be responsible for loading and providing access to `config.yaml`.
*   **File**: `wyrm/services/utility_service.py` (or similar)
    *   Pure, stateless utility functions like `get_file_path_from_title` can be moved to a general utility module within the services package.
*   **Cleanup**: Delete `wyrm/utils.py`.

## 7. Update `Orchestrator`
*   **Action**: Modify the `Orchestrator` to use the new services.
*   **File**: `wyrm/services/orchestrator.py`
    *   In the `__init__` method, instead of importing functions, it will now instantiate the new service classes (e.g., `self.driver_manager = WebDriverManager()`, `self.navigation_service = NavigationService(self.driver)`).
    *   Update the `run()` method to call methods on these service instances (e.g., `self.navigation_service.click_sidebar_item(...)`).

## 8. Update Version
*   **File**: `VERSION`
*   **Action**: Change the content from `1.1.0` to `1.2.0`.

## Expected Outcome
- The entire application logic is now encapsulated within service classes, promoting separation of concerns.
- The `Orchestrator` now acts as a true conductor, delegating tasks to specialized services.
- The codebase is significantly more modular, testable, and easier to understand.
- The project version is updated to `1.2.0`. 