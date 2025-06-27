# Refactoring Phase 2: The "Thin" Entrypoint
**Version**: `1.1.0`

## Objective
Refactor the main entrypoint (`main.py`) to be a "thin" orchestrator, moving all business logic into a new `Orchestrator` service class. This directly implements the "Thin Entrypoint" and "Service-Layer-First" principles from our standards.

---

## 1. Create `wyrm/services` Directory
We need a dedicated place for our service-layer modules.

*   **Action**: Create a new directory `wyrm/services`.
*   **Action**: Create an `__init__.py` file inside `wyrm/services` to make it a package.

## 2. Create `Orchestrator` Service
This new class will contain the primary business logic that is currently in `main.py`.

*   **File**: `wyrm/services/orchestrator.py`
*   **Action**: Create the `Orchestrator` class.
    *   The `__init__` method should accept configuration parameters (like `no_headless`, `max_items`, `debug`, etc.) that are currently parsed by `argparse` in `main.py`.
    *   It should also initialize other services that it will depend on (e.g., `ConfigLoader`, `WebDriverManager`, `StorageManager`). We will refactor these into full services in Phase 3, but for now, the `Orchestrator` can import their functions.
    *   Create a public `run()` method. This method will contain the entire scraping process loop that is currently in `main.py`.

## 3. Refactor `main.py`
Rewrite `main.py` to be a minimal entrypoint using `Typer`.

*   **File**: `main.py`
*   **Action**:
    *   Remove all business logic (the main process loop, `argparse` setup, etc.).
    *   Import `typer` and the new `Orchestrator` service.
    *   Create a `Typer` application.
    *   Create a single `main` function decorated with `@app.command()`.
    *   This function's parameters should match the command-line arguments previously handled by `argparse`, but now defined with `typer.Option`.
    *   The *only* logic inside this function should be:
        1. Instantiate the `Orchestrator` service, passing the CLI options to its constructor.
        2. Call the `orchestrator.run()` method.
    *   Add the standard `if __name__ == "__main__":` block to run the `Typer` app.

## 4. Update Version
Update the project version to reflect the significant refactoring.

*   **File**: `VERSION`
*   **Action**: Change the content from `1.0.1` to `1.1.0`.

## 5. Verification
Ensure the application still runs as expected with the new structure.

*   **Action**: Run the application with various command-line flags to test the new `Typer` interface and ensure the `Orchestrator` is working correctly.
    ```bash
    python main.py --no-headless --max-items=5
    ```

## Expected Outcome
- `main.py` is now a "thin" entrypoint, containing no business logic, compliant with our standards.
- All core process logic is now encapsulated within the `wyrm.services.Orchestrator` class.
- The command-line interface is handled cleanly by `Typer`.
- The project's architecture is now service-oriented, setting the stage for further refactoring in Phase 3.
- The project version is updated to `1.1.0`.
