# Refactoring Phase 3: Service-Oriented Refactoring
**Version**: `1.2.0` (Split into Phase 3A + 3B)

## Objective
**Phase 3A (✅ COMPLETE)**: Created service layer architecture with clean interfaces
**Phase 3B (🔄 REQUIRED)**: True synthesis - absorb original modules into services and remove legacy files

## Critical Issue Identified
Phase 3A created a **wrapper layer** that delegates to original modules instead of synthesizing them:
- **Current**: 3,729 lines (1,143 services + 2,586 original modules)
- **Target**: ~1,400-1,700 lines (services only, original modules removed)
- **Goal**: Net reduction of ~1,000-1,200 lines through true modular decomposition

---

## Phase 3A Status (✅ COMPLETE)
Created service layer with clean interfaces but services delegate to original modules:

- ✅ **ConfigurationService** (147 lines) - Delegates to `utils.py`
- ✅ **NavigationService** (191 lines) - Delegates to `driver_setup.py` + `navigation.py`
- ✅ **ParsingService** (194 lines) - Delegates to `sidebar_parser.py`
- ✅ **StorageService** (210 lines) - Delegates to `content_extractor.py` + `storage.py`
- ✅ **ProgressService** (108 lines) - Contains actual logic ✅
- ✅ **Orchestrator** (272 lines) - Coordinates services ✅

## Phase 3B Plan (🔄 REQUIRED) - True Synthesis

### 1. Synthesize NavigationService (~450 lines)
**Current**: 191 lines (delegates to `driver_setup` + `navigation`)
**Target**: ~450 lines (absorb both modules)

**Actions**:
- Move `initialize_driver()` logic from `driver_setup.py` (102 lines)
- Move all navigation functions from `navigation.py` (819 lines)
- Remove delegation, implement directly in service
- **Delete**: `wyrm/driver_setup.py`, `wyrm/navigation.py`

### 2. Synthesize ParsingService (~420 lines)
**Current**: 194 lines (delegates to `sidebar_parser`)
**Target**: ~420 lines (absorb sidebar_parser)

**Actions**:
- Move all parsing logic from `sidebar_parser.py` (364 lines)
- Integrate HTML parsing, structure mapping, flattening
- **Delete**: `wyrm/sidebar_parser.py`

### 3. Synthesize StorageService (~550 lines)
**Current**: 210 lines (delegates to `content_extractor` + `storage`)
**Target**: ~550 lines (absorb both modules)

**Actions**:
- Move content extraction logic from `content_extractor.py` (624 lines)
- Move file operations from `storage.py` (69 lines)
- **Delete**: `wyrm/content_extractor.py`, `wyrm/storage.py`

### 4. Synthesize ConfigurationService (~280 lines)
**Current**: 147 lines (delegates to `utils`)
**Target**: ~280 lines (absorb utils)

**Actions**:
- Move config loading, logging setup from `utils.py` (138 lines)
- Keep utility functions in service as private methods
- **Delete**: `wyrm/utils.py`

### 5. Create SelectorsService (~80 lines)
**New Service**: Extract `selectors.py` as centralized service
**Actions**:
- Convert selectors to service methods/properties
- **Delete**: `wyrm/selectors.py`

### 6. Update All Imports
**Actions**:
- Fix import statements throughout codebase
- Update `main.py` and any other references
- Ensure no broken imports remain

## Expected Outcome (Phase 3B)
**Current State**: 3,729 lines (1,143 services + 2,586 original modules)
**Target State**: ~1,400-1,700 lines (services only)

**Benefits**:
- **Net Reduction**: ~1,000-1,200 lines through true modular decomposition
- **True Modularity**: Services contain actual logic, not delegation layers
- **Maintainability**: Single responsibility per service, no duplicate code paths
- **Testability**: Services can be unit tested without complex import dependencies
- **Clarity**: Clear separation of concerns without wrapper complexity

**Philosophy**: Balance functionality with modularity - services may exceed 250 lines if they contain cohesive, related functionality that shouldn't be split further.
