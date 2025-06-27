# Refactoring Phase 4: Data Modeling with Pydantic
**Version**: `1.3.0`

## Objective
Introduce strong data contracts by defining and integrating Pydantic models for all data structures that are passed between services. This eliminates "stringly-typed" programming and makes the data flow explicit and validated.

---

## 1. Create `wyrm/models` Directory
We need a dedicated package for our data models.

*   **Action**: Create a new directory `wyrm/models`.
*   **Action**: Create an `__init__.py` file inside `wyrm/models` to make it a package.

## 2. Define Core Data Models
Analyze the data currently being passed around (e.g., as dictionaries from the config, or tuples from parsing functions) and define Pydantic models for them.

*   **File**: `wyrm/models/config.py`
*   **Action**: Create `Config` models.
    *   Define models like `Timeouts`, `Paths`, `Site`, and a main `AppConfig` model that composes them. This will replace dictionary access like `config['timeouts']['navigation']` with type-hinted `config.timeouts.navigation`.

*   **File**: `wyrm/models/scrape.py`
*   **Action**: Create `Scrape` models.
    *   Define a `SidebarItem` model to represent an item parsed from the sidebar (e.g., containing `id`, `name`, `level`, `parent_id`).
    *   Define a `ScrapedContent` model to represent the final extracted data for a page (e.g., `title`, `url`, `markdown_content`, `breadcrumbs`).
    *   Define a `ResumeInfo` model for the data in `resume_info.json`.

## 3. Integrate Models into Services

### 3.1 `ConfigService`
*   **Action**: Refactor the `ConfigService` to load the YAML file and parse it directly into the `AppConfig` Pydantic model.
*   **Benefit**: The rest of the application can now access configuration through a type-safe object instead of a dictionary.

### 3.2 `ScrapingService`
*   **Action**: Update the methods in `ScrapingService` to return Pydantic models.
    *   `parse_sidebar()` should return a `List[SidebarItem]`.
    *   `extract_content()` should return a `ScrapedContent` object.
*   **Benefit**: The data contract is now explicit. The `Orchestrator` knows exactly what fields to expect.

### 3.3 `StorageService`
*   **Action**: Update `StorageService` methods to accept Pydantic models.
    *   `save_content_to_file()` should accept a `ScrapedContent` object. The method will handle serializing it to a string for saving.
    *   `load_resume_info()` should return a `ResumeInfo` object.
*   **Benefit**: The service's API is now clearer and less prone to errors from malformed data.

### 3.4 `Orchestrator`
*   **Action**: Update the `Orchestrator` to use the new models.
*   **Benefit**: The logic within the `run()` method will be cleaner, accessing data via attributes (`scraped_item.title`) instead of dictionary keys (`scraped_item['title']`), with full autocompletion and type checking from the IDE.

## 4. Update Version
*   **File**: `VERSION`
*   **Action**: Change the content from `1.2.0` to `1.3.0`.

## Expected Outcome
- Unstructured dictionaries are eliminated from the application's core logic.
- Data flowing between services is now explicit, validated, and self-documenting.
- The risk of runtime errors due to misspelled keys or incorrect data types is significantly reduced.
- The project's data architecture is robust and easy to reason about.
- The project version is updated to `1.3.0`.
