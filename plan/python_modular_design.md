# Wyrm - Python Modular Development Standards
*Version 1.0 - Mandatory for All Development*

## 🚨 CRITICAL: The Principle of Maintainable Modularity

**The Problem**: Large, monolithic Python files and classes are a significant source of technical debt. They are difficult to read, hard to test, and expensive to refactor. A single file trying to manage data fetching, processing, and output is a bug-prone and unscalable pattern.

**The Solution**: These standards are **MANDATORY** for all future Python development on this project. They are designed to enforce a modular-first architecture from day one, ensuring our codebase remains clean, testable, and maintainable.

---

## 1. Mandatory File & Code Size Limits

### 1.1 Target Guidelines (Strong Preferences, Not Hard Limits)
- **Python Modules (`.py` files)**: Target ~250 lines (acceptable up to ~300 for complex but cohesive functionality)
- **Python Classes**: Target ~150 lines (acceptable up to ~200 for well-structured classes)
- **Python Functions/Methods**: Target ~40 lines (acceptable up to ~60 for complex but atomic operations)

### 1.2 Philosophy: Function Over Form
- **Primary Goal**: Maintainable, readable, and robust code
- **Secondary Goal**: Hitting target line counts
- **Balance**: Strive hard for the targets, but don't sacrifice functionality, error handling, or clarity
- **Quality Indicators**: Clear separation of concerns, comprehensive error handling, good documentation

### 1.3 Enforcement
- Code reviews MUST verify modular design principles and separation of concerns
- Line counts are guidelines to encourage decomposition, not rigid rules
- If exceeding targets, justify with clear reasoning (complex but cohesive functionality, comprehensive error handling, etc.)

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

### 2.3 Sub-Module Decomposition for Large Services (MANDATORY)
When a service exceeds ~300 lines, it MUST be broken down into sub-modules using service packages:

#### Service Package Pattern (MANDATORY for Sub-Module Decomposition)
**All sub-modules MUST be organized in dedicated service folders**, not as loose files in the services directory.

```python
# wyrm/services/storage/
#   __init__.py          # Main service class that composes sub-modules
#   content_extractor.py # Content extraction logic (~250 lines)
#   file_operations.py   # File saving/loading operations (~200 lines)
#   resume_manager.py    # Resume and status management (~150 lines)

# wyrm/services/storage/__init__.py
from .content_extractor import ContentExtractor
from .file_operations import FileOperations
from .resume_manager import ResumeManager

class StorageService:
    """Main storage service that delegates to specialized sub-modules."""

    def __init__(self):
        self.content_extractor = ContentExtractor()
        self.file_operations = FileOperations()
        self.resume_manager = ResumeManager()

    async def save_content_for_item(self, item, driver, config_values):
        # Thin coordinator method
        content = await self.content_extractor.extract_content(driver)
        return await self.file_operations.save_markdown(content, item, config_values)
```

```python
# wyrm/services/navigation/
#   __init__.py          # Main service class that composes sub-modules
#   driver_manager.py    # Driver setup/cleanup (~150 lines)
#   menu_expander.py     # Menu expansion logic (~200 lines)
#   content_navigator.py # Item clicking and waiting (~150 lines)

# wyrm/services/navigation/__init__.py
from .driver_manager import DriverManager
from .menu_expander import MenuExpander
from .content_navigator import ContentNavigator

class NavigationService:
    """Main navigation service coordinating specialized components."""

    def __init__(self):
        self.driver_manager = DriverManager()
        self.menu_expander = None  # Initialized when driver is ready
        self.content_navigator = None  # Initialized when driver is ready

    async def initialize_driver(self, config):
        await self.driver_manager.initialize_driver(config)
        driver = self.driver_manager.get_driver()
        if driver:
            self.menu_expander = MenuExpander(driver)
            self.content_navigator = ContentNavigator(driver)
```

#### Key Requirements for Service Packages:
1. **Folder Organization**: Create `wyrm/services/{service_name}/` directory
2. **Main Coordinator**: `__init__.py` contains the main service class (~150 lines max)
3. **Sub-Modules**: Individual `.py` files for each responsibility (~250 lines max each)
4. **Backward Compatibility**: Main service maintains the same public interface
5. **Import Structure**: Use relative imports within package, absolute imports from outside

### 2.4 Class and Function Decomposition (MANDATORY)
Break down classes and modules based on the Single Responsibility Principle.

**Original Pattern (Before Sub-Modules):**
- **`driver_setup.py`**: Only responsible for creating and configuring a Selenium WebDriver.
- **`navigation.py`**: Only responsible for browser navigation actions.
- **`content_extractor.py`**: Only responsible for extracting and cleaning HTML content.
- **`storage.py`**: Only responsible for saving data to disk.

**Enhanced Pattern (With Sub-Modules):**
- **Service packages** handle complex domains with multiple sub-responsibilities
- **Each sub-module** maintains single responsibility within its domain
- **Main service classes** act as thin coordinators that delegate to sub-modules

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

### 5.2 Sub-Module Refactoring Process
When a service exceeds ~300 lines, follow this process:

1. **Identify Responsibilities**: Analyze the service's methods and group them by responsibility
2. **Create Service Package**: Create `wyrm/services/{service_name}/` directory
3. **Extract Sub-Modules**: Move related methods to new `.py` files in the service directory, maintaining their signatures
4. **Create Main Coordinator**: Convert main service to a thin coordinator in `__init__.py` that delegates to sub-modules
5. **Update Imports**: Ensure all existing imports continue to work (backward compatibility)
6. **Test Thoroughly**: Verify that all functionality remains intact after refactoring

#### Refactoring Checklist:
- [ ] Service directory created: `wyrm/services/{service_name}/`
- [ ] Sub-modules extracted with clear single responsibilities
- [ ] Main coordinator in `__init__.py` (≤150 lines)
- [ ] All sub-modules within guidelines (≤250 lines each)
- [ ] Backward compatibility maintained
- [ ] All imports updated
- [ ] Application functionality verified

### 5.3 Code Review Requirements
Every Pull Request MUST be reviewed for:
- **Compliance with size limits**.
- **Adherence to the thin entrypoint / fat service model**.
- **Proper sub-module decomposition for services >300 lines**.
- **Proper use of Pydantic models**.
- **Complete and correct docstrings**.

---

## 6. Conclusion

**These standards are non-negotiable.** They are the direct result of understanding the long-term costs of monolithic code. Following these rules prevents technical debt and ensures our project is built on a foundation of clean, testable, and scalable code.

**Every developer** MUST follow these standards. **Every code review** MUST verify them. This discipline allows us to move faster and build more reliable software.
