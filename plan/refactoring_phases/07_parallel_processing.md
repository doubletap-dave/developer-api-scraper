# Refactoring Phase 7: Parallel Processing
**Version**: `1.5.0`

## Objective
Significantly improve performance by refactoring the `Orchestrator` to scrape multiple documentation pages concurrently using `asyncio`.

---

## 1. Add Concurrency Configuration
*   **File**: `config.yaml`
*   **Action**: Add a new setting to control the level of parallelism.
    ```yaml
    behavior:
      # ... existing settings ...
      max_concurrent_tasks: 5 # Number of items to scrape at the same time
    ```

## 2. Refactor `Orchestrator` for Concurrency
This is the core of the phase and involves changing the `run` method from a sequential loop to a concurrent task manager.

*   **File**: `wyrm/services/orchestrator.py`
*   **Action**: Modify the `Orchestrator.run()` method.
    1.  **Gather All Items First**: Instead of iterating and processing one-by-one, first get the complete list of all `SidebarItem` objects that need to be scraped.
    2.  **Create a Semaphore**: Instantiate an `asyncio.Semaphore` using the `max_concurrent_tasks` value from the config. This is critical to limit how many browsers/tasks run at once, preventing system overload and respecting the target server.
    3.  **Create Worker Tasks**: For each `SidebarItem` in the list, create a new asynchronous "worker" coroutine (e.g., `scrape_worker`). Pass the `SidebarItem` and the `Semaphore` to this worker.
    4.  **Run with `asyncio.gather`**: Use `await asyncio.gather(*tasks)` to run all the worker tasks concurrently.

## 3. Create the `scrape_worker` Method
*   **File**: `wyrm/services/orchestrator.py`
*   **Action**: Create a new private async method, `_scrape_worker(item, semaphore)`.
    *   **Logic**: This worker represents the lifecycle of scraping a single page. It will:
        1.  **Acquire Semaphore**: `async with semaphore:` - This will block until a "slot" is available for it to run.
        2.  **Create Self-Contained Services**: Inside the `async with` block, the worker must create its *own* instances of the services it needs, specifically the `WebDriverManager`. This is crucial because a single WebDriver instance is **not** thread-safe and cannot be shared across concurrent tasks.
            ```python
            driver_manager = WebDriverManager(self.config)
            driver = driver_manager.get_driver()
            # Pass driver to other services as needed
            navigation_service = NavigationService(driver)
            scraping_service = ScrapingService(driver)
            ```
        3.  **Perform the Scrape**: Use these services to perform all actions for this single item (navigate, click, extract content).
        4.  **Save the Data**: Use the `StorageService` to save the result.
        5.  **Cleanup**: Crucially, ensure the WebDriver instance is closed within a `finally` block to prevent orphaned browser processes. `driver_manager.close_driver()`.
        6.  The semaphore is automatically released when the `async with` block exits.

## 4. Update Progress Bar
*   The existing `rich` progress bar will need to be adapted. It can be initialized with the total number of items, and each worker task will call `progress.update(task_id, advance=1)` upon completion. This requires passing the `progress` object and the `task_id` to the worker.

## 5. Update Version
*   **File**: `VERSION`
*   **Action**: Change the content from `1.4.0` to `1.5.0`.

## Expected Outcome
- The scraper's total runtime is drastically reduced.
- The level of concurrency is easily configurable.
- The application remains stable due to the use of a semaphore and by ensuring each concurrent task has its own isolated WebDriver instance.
- The project version is updated to `1.5.0`. 