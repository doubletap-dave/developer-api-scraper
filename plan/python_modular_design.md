# Wyrm - Python Modular Development Standards
*Version 1.0 - Mandatory for All Development*

## 🚨 CRITICAL: The Principle of Maintainable Modularity

**The Problem**: Large, monolithic Python files and classes are a significant source of technical debt. They are difficult to read, hard to test, and expensive to refactor. A single file trying to manage data fetching, processing, and output is a bug-prone and unscalable pattern.

**The Solution**: These standards are **MANDATORY** for all future Python development on this project. They are designed to enforce a modular-first architecture from day one, ensuring our codebase remains clean, testable, and maintainable.

---

## 1. Mandatory File & Code Size Limits

### 1.1 Hard Limits (CI/CD Will Fail)
- **Python Modules (`.py` files)**: Maximum 250 lines
- **Python Classes**: Maximum 150 lines
- **Python Functions/Methods**: Maximum 40 lines

### 1.2 Enforcement
- `flake8` with `mccabe` and other plugins will be configured to enforce these limits.
- The pre-commit hooks and CI/CD pipeline will fail any commit or build that exceeds these hard limits.
- Code reviews must include verification of these metrics.

---

## 2. Modular Architecture Patterns

### 2.1 "Thin" Entrypoints (MANDATORY)
Entrypoints (like `main.py`, a Flask/Django view, or a CLI command function) MUST be thin. Their only job is to orchestrate the flow of data by calling dedicated logic/service modules.

- **NO business logic in entrypoints.**
- **NO direct data manipulation in entrypoints.**
- **NO complex argument parsing in entrypoints (delegate to a configuration or parsing class).**

```python
# ❌ FORBIDDEN - Monolithic "fat" entrypoint
# main.py
def main():
    # 100+ lines of code doing everything...
    url = "http://example.com"
    # ... selenium setup ...
    # ... beautifulsoup parsing ...
    # ... data cleaning ...
    # ... file writing ...
    print("Done.")

# ✅ REQUIRED - "Thin" entrypoint delegating to services
# main.py
from wyrm.services import Orchestrator

def main():
    """Orchestrates the scraping process."""
    orchestrator = Orchestrator()
    orchestrator.run()
```

### 2.2 Service-Layer-First Development (MANDATORY)
All business logic, data processing, and external interactions (API calls, web scraping, database access) MUST be encapsulated within dedicated service classes or modules.

```python
# wyrm/services/orchestrator.py (MAX 250 lines)
from wyrm.services import WebDriverManager, Scraper, Storage

class Orchestrator:
    """A service class to manage the entire scraping workflow."""

    def __init__(self):
        self.driver_manager = WebDriverManager()
        self.scraper = Scraper()
        self.storage = Storage()

    def run(self):
        """Execute the full scraping process."""
        driver = self.driver_manager.get_driver()
        raw_data = self.scraper.extract_content(driver, "some_url")
        processed_data = self.process(raw_data) # private method
        self.storage.save(processed_data)
        self.driver_manager.close_driver()

    def process(self, data):
        # ... logic is contained here, not in main() ...
        return data.strip()
```

### 2.3 Class and Function Decomposition (MANDATORY)
Break down classes and modules based on the Single Responsibility Principle.

- **`driver_setup.py`**: Only responsible for creating and configuring a Selenium WebDriver.
- **`navigation.py`**: Only responsible for browser navigation actions.
- **`content_extractor.py`**: Only responsible for extracting and cleaning HTML content.
- **`storage.py`**: Only responsible for saving data to disk.

---

## 3. Standardized Tooling

### 3.1 Data Modeling (Pydantic)
**MANDATORY**: All complex data structures MUST be defined using Pydantic models. This provides type hints, validation, and serialization for free.

- **Benefit**: Self-documenting, type-safe, and reduces validation boilerplate.

```python
# wyrm/models.py
from pydantic import BaseModel, HttpUrl
from typing import List

class ScrapedItem(BaseModel):
    source_url: HttpUrl
    title: str
    content: str
    tags: List[str] = []
```

### 3.2 Command-Line Interfaces (Typer)
**MANDATORY**: All command-line interfaces MUST be built using `Typer`.

- **Benefit**: Creates clean, documented, and testable CLIs with automatic help generation.

```python
# main.py
import typer

app = typer.Typer()

@app.command()
def run(
    no_headless: bool = typer.Option(False, "--no-headless", help="Run in non-headless mode."),
    max_items: int = typer.Option(None, "--max-items", help="Maximum number of items to process.")
):
    """Run the Wyrm scraper."""
    # Thin command delegates to the orchestrator
    from wyrm.services import Orchestrator
    orchestrator = Orchestrator(no_headless=no_headless, max_items=max_items)
    orchestrator.run()

if __name__ == "__main__":
    app()
```

---

## 4. Documentation Requirements

### 4.1 Google-Style Docstrings (MANDATORY)
Every public module, function, class, and method MUST have a Google-style docstring.

```python
# wyrm/navigation.py
"""
This module contains all functions related to browser navigation using Selenium.
"""
from selenium.webdriver.remote.webdriver import WebDriver

def click_sidebar_item(driver: WebDriver, node_id: str) -> bool:
    """Clicks a specific item in the sidebar by its node ID.

    Args:
        driver: The Selenium WebDriver instance.
        node_id: The unique ID of the node to click.

    Returns:
        True if the item was clicked successfully, False otherwise.

    Raises:
        NoSuchElementException: If the element with the given ID is not found.
    """
    # ... implementation ...
```

---

## 5. Development Workflow

### 5.1 Pre-Development Checklist
Before writing a new feature:

1.  **Plan the Architecture**: Identify responsibilities. Which new service classes are needed? Which existing ones will be used?
2.  **Define the Data Models**: Create or update Pydantic models first.
3.  **Estimate Line Counts**: Ensure your plan fits within the size limits.
4.  **Write Logic in Services First**: Implement the core logic inside service classes.
5.  **Connect to Entrypoint Last**: Wire up the services in your "thin" `main.py` or other entrypoint.

### 5.2 Code Review Requirements
Every Pull Request MUST be reviewed for:
- **Compliance with size limits**.
- **Adherence to the thin entrypoint / fat service model**.
- **Proper use of Pydantic models**.
- **Complete and correct docstrings**.

---

## 6. Conclusion

**These standards are non-negotiable.** They are the direct result of understanding the long-term costs of monolithic code. Following these rules prevents technical debt and ensures our project is built on a foundation of clean, testable, and scalable code.

**Every developer** MUST follow these standards. **Every code review** MUST verify them. This discipline allows us to move faster and build more reliable software.
