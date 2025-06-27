# Wyrm - Modular Architecture Refactoring Plan

This document outlines the phased plan to refactor the Wyrm codebase to align with the mandatory standards defined in `plan/python_modular_design.md`. Each phase represents a significant step towards a more robust, maintainable, and scalable architecture.

## Versioning Strategy

We will follow semantic versioning. The current version is assumed to be `1.0.0`. Each phase will result in a version bump.

- **Phase 1**: `v1.0.1` (Build/tooling changes)
- **Phase 2**: `v1.1.0` (Significant refactoring)
- **Phase 3**: `v1.2.0` (Significant refactoring)
- **Phase 4**: `v1.3.0` (New features/models)
- **Phase 5**: `v1.3.1` (Patch/documentation)
- **Phase 6**: `v1.4.0` (Structured logging)
- **Phase 7**: `v1.5.0` (Parallel processing)

We will create a `VERSION` file at the root of the project to track the current version.

## Refactoring Phases

*   [x] **Phase 1: Setup & Tooling (`v1.0.1`)** ✅ **COMPLETE**
    *   **Objective**: Establish the development environment and automated enforcement of our new standards.
    *   **Details**: [Phase 1 Plan](./refactoring_phases/01_setup_and_tooling.md)

*   [ ] **Phase 2: The "Thin" Entrypoint (`v1.1.0`)**
    *   **Objective**: Refactor the main entrypoint (`main.py`) to be a thin orchestrator, moving all business logic into a new `Orchestrator` service.
    *   **Details**: [Phase 2 Plan](./refactoring_phases/02_thin_entrypoint.md)

*   [ ] **Phase 3: Service-Oriented Refactoring (`v1.2.0`)**
    *   **Objective**: Convert existing functional modules (`navigation.py`, `storage.py`, etc.) into proper service classes to encapsulate logic and state.
    *   **Details**: [Phase 3 Plan](./refactoring_phases/03_service_refactoring.md)

*   [ ] **Phase 4: Data Modeling with Pydantic (`v1.3.0`)**
    *   **Objective**: Introduce strong data contracts by defining and integrating Pydantic models for all data structures.
    *   **Details**: [Phase 4 Plan](./refactoring_phases/04_pydantic_models.md)

*   [ ] **Phase 5: Documentation & Final Compliance (`v1.3.1`)**
    *   **Objective**: Ensure 100% compliance with the new standards, focusing on comprehensive docstrings and a final code review.
    *   **Details**: [Phase 5 Plan](./refactoring_phases/05_documentation_and_review.md)

*   [ ] **Phase 6: Structured Logging (`v1.4.0`)**
    *   **Objective**: Implement structured JSON logging for comprehensive, machine-readable output.
    *   **Details**: [Phase 6 Plan](./refactoring_phases/06_structured_logging.md)

*   [ ] **Phase 7: Parallel Processing (`v1.5.0`)**
    *   **Objective**: Significantly improve performance by scraping multiple items concurrently.
    *   **Details**: [Phase 7 Plan](./refactoring_phases/07_parallel_processing.md)
