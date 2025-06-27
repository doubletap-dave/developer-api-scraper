# Refactoring Phase 6: Structured Logging
**Version**: `1.4.0`

## Objective
Implement structured, two-level logging using `structlog` to provide both human-readable console output and comprehensive, machine-readable JSON logs for advanced analysis and monitoring.

---

## 1. Add `structlog` Dependency
*   **File**: `requirements.txt`
*   **Action**: Add `structlog` to the dependencies.
    ```
    structlog
    ```
*   **Action**: Run `pip install -r requirements.txt`.

## 2. Create `LoggingService`
A dedicated service will encapsulate all logging configuration. This keeps the setup logic clean and separate from the application's business logic.

*   **File**: `wyrm/services/logging_service.py`
*   **Class**: `LoggingService`
    *   **Action**: Create a `setup_logging` method that takes the log level (e.g., 'INFO', 'DEBUG') and config file as input.
    *   **Logic**: This method will contain the full `structlog` configuration. It will configure two "handlers":
        1.  **Console Handler ("Normal")**:
            *   **Level**: `INFO`.
            *   **Formatter**: Use `structlog.dev.ConsoleRenderer` for beautiful, colorized, key-value-style logs that are easy to read during development.
        2.  **File Handler ("Everything")**:
            *   **Level**: `DEBUG`.
            *   **Formatter**: Use `structlog.processors.JSONRenderer` to write every log entry as a structured JSON object.
            *   **Filename**: The log file path should be read from the config (e.g., `logs/wyrm.json`).
    *   **Processors**: Configure `structlog` with standard processors to add context like `timestamp`, `log_level`, `function_name`, and `line_number` to every log entry automatically.

## 3. Integrate `LoggingService`
*   **File**: `main.py`
*   **Action**:
    *   At the very beginning of the `main` function (the `Typer` command), instantiate `LoggingService` and call `setup_logging()`.
    *   This ensures logging is configured before any other part of the application runs.

*   **File**: All other services (e.g., `Orchestrator`, `ScrapingService`)
*   **Action**:
    *   At the top of each file, get a logger instance with `logger = structlog.get_logger(__name__)`.
    *   Replace all `logging.info(...)` calls with `logger.info(...)`.
    *   Enhance log messages by passing key-value pairs for context, for example:
        ```python
        # Old way
        logging.info(f"Scraping item {item_id}")

        # New structlog way
        logger.info("Scraping item", item_id=item_id, url=item.url)
        ```

## 4. Update Version
*   **File**: `VERSION`
*   **Action**: Change the content from `1.3.1` to `1.4.0`.

## Expected Outcome
- When running the application, the console shows clean, readable `INFO`-level logs.
- A `wyrm.json` file is created in the `logs` directory, containing `DEBUG`-level logs where each line is a complete JSON object.
- Logs are now enriched with contextual key-value data, making debugging and analysis significantly more powerful.
- The project version is updated to `1.4.0`. 