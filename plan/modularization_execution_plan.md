# Wyrm Modularization Execution Plan

## Overview
This plan systematically refactors the Wyrm codebase to comply with Python Modular Design Standards by breaking down large modules, classes, and functions into manageable, single-responsibility components.

## Current Violations Summary
**Total: 27 violations (was 31)** ✅ 4 violations eliminated!
- **2 Modules** over 300 lines (876, 449 lines) - ~~628~~ ✅
- **8 Classes** over 200 lines (up to 860 lines) - ~~orchestrator~~ ✅ 
- **17 Functions** over 60 lines (up to 163 lines) - ~~3 orchestrator funcs~~ ✅

---

## PHASE 1: Critical Module Decomposition (Days 1-5)

### Priority 1.1: Split `orchestrator.py` (628 → ~200 lines each)
**Status: [x] COMPLETED** ✅

**Target Structure:**
```
wyrm/services/orchestration/
├── __init__.py          # Main Orchestrator (thin coordinator) ~150 lines
├── workflow_manager.py  # run_scraping_workflow logic ~200 lines  
├── item_processor.py    # Item processing methods ~200 lines
└── structure_handler.py # Sidebar structure handling ~200 lines
```

**Action Steps:**
1. [x] Create `wyrm/services/orchestration/` directory ✅
2. [x] Extract `run_scraping_workflow()` → `workflow_manager.py` ✅
3. [x] Extract `_process_*` methods → `item_processor.py` ✅
4. [x] Extract `_handle_sidebar_structure()` → `structure_handler.py` ✅
5. [x] Create thin coordinator in `__init__.py` ✅
6. [x] Update imports and maintain backward compatibility ✅
7. [x] Run contract tests to verify API compatibility ✅
8. [x] Run line count checker to verify compliance ✅

**Methods to Extract:**
- `run_scraping_workflow()` → WorkflowManager
- `_process_items_from_structure()` → ItemProcessor
- `_process_items_hybrid_mode()` → ItemProcessor  
- `_process_single_item()` → ItemProcessor
- `_handle_sidebar_structure()` → StructureHandler

---

### Priority 1.2: Split `menu_expander.py` (876 → ~250 lines each)
**Status: [ ] TODO**

**Target Structure:**
```
wyrm/services/navigation/expansion/
├── __init__.py              # Main MenuExpander (thin coordinator) ~150 lines
├── discovery.py             # Menu discovery methods ~250 lines
├── powerflex_expander.py    # PowerFlex-specific logic ~250 lines
└── enhanced_expander.py     # Enhanced expansion methods ~250 lines
```

**Action Steps:**
1. [ ] Create `wyrm/services/navigation/expansion/` directory
2. [ ] Extract discovery methods → `discovery.py`
3. [ ] Extract PowerFlex methods → `powerflex_expander.py`
4. [ ] Extract enhanced methods → `enhanced_expander.py`
5. [ ] Create thin coordinator in `__init__.py`
6. [ ] Update imports in navigation service
7. [ ] Run contract tests to verify API compatibility
8. [ ] Run line count checker to verify compliance

**Methods to Extract:**
- `_discover_ancestor_menus()` → DiscoveryManager
- `_expand_powerflex_path_to_item()` → PowerFlexExpander
- `_expand_menus_powerflex_optimized()` → PowerFlexExpander
- `_expand_menus_enhanced()` → EnhancedExpander
- `_expand_menus_3x_enhanced()` → EnhancedExpander

---

### Priority 1.3: Split `structure_parser.py` (449 → ~200 lines each)
**Status: [ ] TODO**

**Target Structure:**
```
wyrm/services/parsing/structure/
├── __init__.py           # Main StructureParser ~150 lines
├── hierarchy_parser.py   # Hierarchical parsing logic ~200 lines
└── validation.py         # Structure validation methods ~150 lines
```

**Action Steps:**
1. [ ] Create `wyrm/services/parsing/structure/` directory
2. [ ] Extract `_parse_hierarchical_structure()` → `hierarchy_parser.py`
3. [ ] Extract validation methods → `validation.py`
4. [ ] Create thin coordinator in `__init__.py`
5. [ ] Update imports in parsing service
6. [ ] Run contract tests to verify API compatibility
7. [ ] Run line count checker to verify compliance

---

## PHASE 2: Class Decomposition (Days 6-10)

### Priority 2.1: ConfigurationService (277 lines → ~150 lines)
**Status: [ ] TODO**

**Action Steps:**
1. [ ] Extract validation logic into `ConfigurationValidator` class
2. [ ] Extract file operations into utility functions
3. [ ] Keep core configuration loading in main class
4. [ ] Verify line count compliance

### Priority 2.2: ParallelOrchestrator (226 lines → ~150 lines)
**Status: [ ] TODO**

**Action Steps:**
1. [ ] Extract worker coordination into `WorkerCoordinator` class
2. [ ] Extract task management into utility functions
3. [ ] Keep core parallel logic in main class
4. [ ] Verify line count compliance

### Priority 2.3: NavigationService (249 lines → ~150 lines)
**Status: [ ] TODO**

**Action Steps:**
1. [ ] Extract driver management logic (already separate)
2. [ ] Extract waiting/polling logic into utilities
3. [ ] Keep core navigation in main class
4. [ ] Verify line count compliance

### Priority 2.4: ContentExtractor (213 lines → ~150 lines)
**Status: [ ] TODO**

**Action Steps:**
1. [ ] Extract content processing into utility functions
2. [ ] Extract API endpoint logic into separate class
3. [ ] Keep core extraction in main class
4. [ ] Verify line count compliance

### Priority 2.5: FileOperations (233 lines → ~150 lines)
**Status: [ ] TODO**

**Action Steps:**
1. [ ] Extract file handling utilities into separate module
2. [ ] Extract path operations into utility functions
3. [ ] Keep core file ops in main class
4. [ ] Verify line count compliance

---

## PHASE 3: Function Decomposition (Days 11-15)

### Priority 3.1: Critical Functions (100+ lines)
**Status: [ ] TODO**

1. **`main.py:main()`** (103 lines)
   - [ ] Extract CLI setup into `setup_cli()`
   - [ ] Extract config loading into `load_configuration()`
   - [ ] Extract execution logic into `execute_workflow()`

2. **`setup_logging()`** (101 lines)
   - [ ] Extract formatter setup into `create_formatters()`
   - [ ] Extract handler config into `setup_handlers()`
   - [ ] Extract file setup into `setup_log_files()`

### Priority 3.2: PowerFlex Functions (160+ lines)
**Status: [ ] TODO**

1. **`_expand_powerflex_path_to_item()`** (163 lines)
   - [ ] Extract path traversal into `traverse_path()`
   - [ ] Extract menu finding into `find_menu_items()`
   - [ ] Extract expansion logic into `expand_path_segment()`

2. **`_expand_menus_enhanced()`** (114 lines)
   - [ ] Extract menu discovery into `discover_menus()`
   - [ ] Extract expansion attempts into `attempt_expansion()`
   - [ ] Extract verification into `verify_expansion()`

### Priority 3.3: Parsing Functions (130+ lines)
**Status: [ ] TODO**

1. **`_parse_hierarchical_structure()`** (136 lines)
   - [ ] Extract header parsing into `parse_headers()`
   - [ ] Extract item parsing into `parse_items()`
   - [ ] Extract structure building into `build_structure()`

### Priority 3.4: Moderate Functions (60-80 lines)
**Status: [ ] TODO**

**15 functions to refactor:**
- [ ] `run_benchmark_suite()` (74 lines)
- [ ] `process_item()` (65 lines)
- [ ] `process_items_parallel()` (92 lines)
- [ ] `run_scraping_workflow()` (76 lines)
- [ ] `_handle_sidebar_structure()` (81 lines)
- [ ] `_process_items_from_structure()` (76 lines)
- [ ] `_process_items_hybrid_mode()` (89 lines)
- [ ] `_process_single_item()` (97 lines)
- [ ] `expand_menu_for_item()` (81 lines)
- [ ] `_discover_ancestor_menus()` (63 lines)
- [ ] `_expand_specific_menu()` (77 lines)
- [ ] `_expand_menus_3x_enhanced()` (95 lines)
- [ ] `_expand_menus_powerflex_optimized()` (134 lines)
- [ ] `_wait_for_sidebar()` (64 lines)
- [ ] `_extract_api_endpoint_content()` (62 lines)

---

## Progress Tracking

### Completion Checklist
- [ ] **Phase 1 Complete**: All 3 critical modules split (1/3 complete) 🔄
- [ ] **Phase 2 Complete**: All 8 classes under 200 lines
- [ ] **Phase 3 Complete**: All 17 functions under 60 lines
- [ ] **Final Verification**: 0 violations in line count checker
- [x] **Contract Tests**: All API contracts still pass ✅
- [ ] **Functionality**: All existing tests pass

### Validation Commands
```bash
# Check line count compliance
python3 tools/line_count_checker.py --exclude "tests/,tools/"

# Verify API contracts
python3 -m pytest tests/test_api_contracts.py -v

# Run all tests
python3 -m pytest tests/ -v

# Check imports and basic functionality
python3 -c "from wyrm.services import Orchestrator; print('Import successful')"
```

### Success Metrics
- **Line Count**: 0 violations
- **Test Coverage**: ≥80% maintained
- **API Compatibility**: All contract tests pass
- **Functionality**: No regressions in existing features

---

## Notes
- Maintain backward compatibility at all times
- Update imports incrementally
- Test after each major extraction
- Document any API changes in CHANGELOG.md
- Keep public interfaces unchanged

**Last Updated**: 2025-06-29  
**Status**: Phase 1 Ready to Begin
