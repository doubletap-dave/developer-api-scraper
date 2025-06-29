# Wyrm - Developer API Documentation Scraper

A powerful, modular Python application for intelligently scraping developer API documentation from websites with complex navigation structures. Wyrm specializes in navigating dynamic web documentation sites and converting them into well-structured Markdown files.

[![Version](https://img.shields.io/badge/version-1.4.1-blue.svg)](https://github.com/doubletap-dave/wyrm/releases/tag/v1.4.1)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-BSD%203--Clause-blue.svg)](LICENSE)
[![Production Ready](https://img.shields.io/badge/status-production%20ready-brightgreen.svg)](https://github.com/doubletap-dave/wyrm)

## 🚀 Features

### **Core Capabilities**
- **Multi-Response Extraction**: Captures all API response codes (200, 400, 401, 403, 404, 500+) per endpoint
- **Professional Schema Documentation**: Hierarchical structure with proper indentation and data types
- **Comprehensive Content**: Extracts API endpoints, parameters, responses, schemas, and descriptions
- **Intelligent Navigation**: Handles complex dynamic web interfaces with smart waiting and error recovery
- **Resume Capability**: Automatically detects and resumes interrupted scraping sessions

### **Modern Architecture (v1.4.1)**
- **🏗️ Modular Design**: Clean service-based architecture with single responsibility principle
- **🔒 Type Safety**: Full Pydantic model integration for configuration and data validation
- **📚 Comprehensive Documentation**: Google-style docstrings throughout the entire codebase
- **🛡️ Robust Error Handling**: Comprehensive exception management and recovery
- **📊 Rich Progress Reporting**: Real-time progress bars with detailed statistics
- **⚙️ Flexible Configuration**: Type-safe YAML configuration with CLI overrides

### **Developer Experience**
- **Smart Resume**: Automatically skips existing files and resumes where you left off
- **Debug Support**: Extensive logging, HTML capture, and structure analysis
- **CLI Interface**: Full-featured command-line interface with comprehensive help
- **Testing Ready**: Modular architecture supports easy testing and validation

## 📋 Requirements

- **Python**: 3.8+ (recommended: 3.11+)
- **Browser**: Microsoft Edge (WebDriver automatically managed)
- **System**: macOS, Linux, or Windows
- **Network**: Internet connection for target documentation sites

## 🛠️ Installation

### **Quick Start**
```bash
# Clone the repository
git clone https://github.com/doubletap-dave/wyrm.git
cd wyrm

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run with default configuration
python main.py --help
```

### **Development Setup**
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Run linting
flake8 .

# Install pre-commit hooks
pre-commit install
```

## ⚙️ Configuration

Wyrm uses a type-safe YAML configuration system with Pydantic validation. The default `config.yaml` works for Dell PowerFlex API documentation:

```yaml
# Scraping Configuration
scraping:
  base_url: "https://developer.dell.com/apis/4008/versions/4.6.1/docs"
  target_url: "https://developer.dell.com/apis/4008/versions/4.6.1/docs"

# WebDriver Settings
webdriver:
  browser: "edge"
  headless: true
  window_width: 1920
  window_height: 1080

# Timing Configuration
delays:
  navigation: 10
  sidebar_wait: 15
  expand_menu: 0.5
  post_expand_settle: 1.0
  content_wait: 20

  # Non-headless mode overrides (for debugging)
  navigation_noheadless: 15
  sidebar_wait_noheadless: 20
  expand_menu_noheadless: 0.7
  post_expand_settle_noheadless: 2.0
  post_click_noheadless: 0.7
  content_wait_noheadless: 15

# Application Behavior
behavior:
  output_dir: "output"
  max_expand_attempts: 10
  force_overwrite: false

# Logging Configuration
logging:
  level: "INFO"
  file: "logs/wyrm.log"
  console_level: "INFO"

# Debug Settings
debug:
  output_dir: "output/debug"
  save_structure_filename: "structure_debug.json"
  save_html_filename: "sidebar_debug.html"
  non_headless_pause_seconds: 10
```

## 🚀 Usage

### **Basic Commands**

**Extract all API documentation:**
```bash
python main.py
```

**Check what's available to process:**
```bash
python main.py --resume-info
```

**Debug mode (non-headless, detailed logging):**
```bash
python main.py --debug
```

### **Common Workflows**

**Development and Testing:**
```bash
# Test with limited items in debug mode
python main.py --debug --max-items 5 --no-headless

# Save structure for analysis
python main.py --save-structure --save-html

# Force re-process specific content
python main.py --force --max-items 10
```

**Production Scraping:**
```bash
# Full headless scraping with progress
python main.py --headless

# Resume interrupted session
python main.py  # Automatically resumes

# Custom configuration
python main.py --config production-config.yaml
```

**Troubleshooting:**
```bash
# Detailed debugging with structure analysis
python main.py --debug --save-structure --save-html --max-items 1

# Check configuration and resume status
python main.py --resume-info --log-level DEBUG
```

## 📁 Architecture & Output

### **Modular Architecture (v1.4.1)**

Wyrm follows a clean, modular architecture with clear separation of concerns:

```
wyrm/
├── models/                    # Pydantic data models
│   ├── config.py             # Configuration models with validation
│   └── scrape.py             # Scraping data models
├── services/                  # Business logic services
│   ├── configuration_service.py  # Config loading & validation
│   ├── orchestrator.py          # Main workflow coordination
│   ├── progress_service.py      # Progress tracking & reporting
│   ├── selectors_service.py     # CSS selector management
│   ├── navigation/              # Browser automation services
│   │   ├── driver_manager.py   # WebDriver lifecycle management
│   │   ├── menu_expander.py    # Menu expansion logic
│   │   └── content_navigator.py # Content navigation
│   ├── parsing/                 # HTML parsing & structure services
│   │   ├── structure_parser.py # Sidebar structure parsing
│   │   ├── item_validator.py   # Item validation logic
│   │   ├── debug_manager.py    # Debug output management
│   │   └── file_manager.py     # File handling utilities
│   └── storage/                 # File operations & content services
│       ├── content_extractor.py # Content extraction & conversion
│       ├── file_operations.py  # File I/O operations
│       └── resume_manager.py   # Resume capability management
└── tests/                     # Comprehensive test suite
```

### **Output Structure**

The scraper organizes extracted documentation into a clean directory structure:

```
output/
├── powerflex-block-api/
│   ├── system/
│   │   ├── query-system-object.md
│   │   ├── approve-sdc.md
│   │   └── ...
│   ├── storage-pool/
│   │   └── ...
│   └── ...
├── structure_developer_dell_com.json  # Sidebar structure cache
└── debug/                             # Debug files (if enabled)
    ├── page_content_*.html
    ├── structure_debug.json
    └── sidebar_debug.html
```

## 📄 Output Format

Each API endpoint is extracted as a comprehensive Markdown file with full response coverage:

```markdown
### GET Query System Object Try It

```
/api/instances/System::{id}
```

Retrieve the object associated with the System ID

#### Servers
| URL | Description |
| --- | --- |
| <https://[ip-address]/api> | NA |

#### Path Parameters
| Name | Type | Description | Required | Example |
| --- | --- | --- | --- | --- |
| id | string | System ID | Required |  |

## Responses

### 200 - Success
**Content-Type:** application/json

**Schema:**
| Property | Type | Description |
|----------|------|-------------|
| System | object | System objects |
|   id | string | System identifier |
|   name | string | System name |
|   systemVersionName | string | Version information |
|   mdmManagementPort | integer | Management port |
|   capacityAlertHighThresholdPercent | number | Alert threshold |

### 400 - Bad Request
Invalid request parameters or malformed request body.

### 401 - Unauthorized
Authentication credentials missing or invalid.

### 403 - Forbidden
Insufficient permissions to access this resource.

### 404 - Not Found
The specified System ID does not exist.

### 500 - Internal Server Error
An unexpected error occurred on the server.
```

## 🔧 Command Line Reference

### **Core Options**
| Option | Description | Example |
|--------|-------------|---------|
| `--config` `-c` | Path to configuration file | `--config my-config.yaml` |
| `--headless` / `--no-headless` | Browser headless mode | `--no-headless` |
| `--log-level` `-l` | Set logging level | `--log-level DEBUG` |

### **Processing Control**
| Option | Description | Example |
|--------|-------------|--------|
| `--force` | Overwrite existing files | `--force` |
| `--max-items` | Limit items to process | `--max-items 10` |
| `--max-expand-attempts` | Menu expansion limit | `--max-expand-attempts 5` |
| `--force-full-expansion` | Force full menu expansion even with cache | `--force-full-expansion` |

### **Debug & Analysis**
| Option | Description | Example |
|--------|-------------|---------|
| `--debug` | Enable comprehensive debug mode | `--debug` |
| `--save-structure` | Save sidebar structure | `--save-structure debug.json` |
| `--save-html` | Save raw HTML | `--save-html sidebar.html` |
| `--resume-info` | Show resume status and exit | `--resume-info` |

### **Legacy Options**
| Option | Description | Status |
|--------|-------------|--------|
| `--test-item-id` | Process specific item | ⚠️ Deprecated (use `--max-items=1`) |

## 🔄 Resume Functionality

Wyrm provides intelligent resume capabilities for interrupted scraping sessions:

### **Automatic Resume**
- **Smart Detection**: Automatically detects existing files and skips them
- **Fast Resume**: No need to re-navigate to already processed pages
- **Progress Preservation**: Maintains progress across sessions
- **Validation**: Ensures existing files are complete and valid

### **Resume Commands**
```bash
# Check detailed resume status
python main.py --resume-info

# Resume where you left off (default behavior)
python main.py

# Force re-process all files
python main.py --force

# Resume with different settings
python main.py --headless --log-level INFO
```

### **Resume Information Output**
```
📊 Resume Information for: https://developer.dell.com/...
═══════════════════════════════════════════════════════

📁 Output Directory: output
📊 Total items in structure: 1,596

✅ Already processed: 63 files
🔄 Need processing: 1,533 files
📈 Progress: 3.9% complete

✅ Recently processed files:
  • PowerFlex -> output/introduction/powerflex.md
  • Authentication -> output/getting-started/powerapi/authentication.md
  • Error Handling -> output/getting-started/powerapi/error-handling.md

🔄 Next items to process:
  • Query System's Protection Domains (ID: docs-node-7145407)
  • Query System's SDCs (ID: docs-node-7145408)
  • Create Storage Pool (ID: docs-node-7145409)

💡 Commands:
  • Resume processing: python main.py
  • Force re-process: python main.py --force
  • Debug mode: python main.py --debug --max-items 5
```

## 🐛 Troubleshooting

### **Common Issues & Solutions**

**Site loading timeout:**
```bash
# Try non-headless mode to see what's happening
python main.py --no-headless --debug --max-items 1

# Increase timeouts in config.yaml
delays:
  navigation: 30
  sidebar_wait: 30
  content_wait: 30
```

**Missing or incomplete content:**
```bash
# Enable debug mode to capture HTML and structure
python main.py --debug --save-html --save-structure --max-items 3

# Check debug files in output/debug/
ls -la output/debug/
```

**Configuration issues:**
```bash
# Validate configuration with debug logging
python main.py --log-level DEBUG --max-items 0

# Test with minimal configuration
python main.py --debug --max-items 1 --no-headless
```

**Resume problems:**
```bash
# Check resume status in detail
python main.py --resume-info --log-level DEBUG

# Force clean restart
python main.py --force --max-items 5
```

### **Debug Mode Features**

Debug mode provides comprehensive troubleshooting capabilities:

```bash
python main.py --debug --max-items 1
```

**Debug mode includes:**
- **Visual Browser**: Non-headless mode so you can see navigation
- **Detailed Logging**: DEBUG-level logging to console and file
- **HTML Capture**: Saves page HTML for analysis
- **Structure Export**: Saves sidebar structure as JSON
- **Extended Timeouts**: Longer waits for manual inspection
- **Error Screenshots**: Captures browser state on errors

## 📊 Performance & Scalability

### **Performance Metrics**
- **Extraction Speed**: 2-5 seconds per API endpoint (headless mode)
- **Content Quality**: 6-8 response codes captured per endpoint
- **Coverage**: 40% more comprehensive than basic extraction tools
- **Memory Usage**: Optimized for large documentation sites (1000+ pages)
- **Resume Speed**: Near-instant resume with smart file detection

### **🚀 Caching Optimization (New in v1.4.1+)**

Wyrm now includes intelligent sidebar structure caching that provides dramatic performance improvements for subsequent runs:

**Performance Benchmark Results:**
- **Fresh run** (no cache): ~23.4 seconds - full website parsing and menu expansion
- **Cached run** (optimal): ~0.39 seconds - loading from pre-parsed structure
- **Performance improvement**: **99% faster** with **60x speedup**

**How Caching Works:**
1. **First Run**: Wyrm navigates the site, expands all menus, and saves the complete sidebar structure to `logs/sidebar_structure.json`
2. **Subsequent Runs**: Wyrm loads the cached structure instantly and skips expensive navigation/expansion
3. **Smart Validation**: Cached structures are validated for completeness and automatically refreshed if needed
4. **Cache Control**: Use `--force-full-expansion` flag to bypass cache when debugging menu expansion issues

**Cache Management:**
```bash
# Normal operation (uses cache when available)
python main.py

# Force fresh parsing (ignores cache)
python main.py --force-full-expansion

# View cache information
ls -la logs/sidebar_structure.json

# Clear cache to force full re-parsing
rm logs/sidebar_structure.json
```

**When Cache is Used:**
- ✅ Valid cached structure exists with sufficient items (10+ valid items)
- ✅ Cache file integrity check passes
- ✅ No `--force-full-expansion` flag specified

**When Fresh Parsing Occurs:**
- 🔄 No cached structure exists
- 🔄 Cached structure has insufficient valid items
- 🔄 Cache validation fails
- 🔄 `--force-full-expansion` flag is used

### **Scalability Features**
- **Modular Architecture**: Easy to extend and customize
- **Type Safety**: Pydantic models prevent runtime errors
- **Error Recovery**: Robust handling of network issues and site changes
- **Progress Tracking**: Detailed statistics and ETA calculations
- **Resource Management**: Proper cleanup of browser resources

## 🏗️ Development

### **Contributing**
1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Make** your changes following the modular architecture
4. **Add** tests for new functionality
5. **Ensure** all tests pass: `pytest tests/`
6. **Run** linting: `flake8 .`
7. **Submit** a pull request

### **Development Setup**
```bash
# Clone and setup development environment
git clone https://github.com/doubletap-dave/wyrm.git
cd wyrm

# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests
pytest tests/ -v

# Run linting
flake8 . --count --statistics
```

### **Architecture Guidelines**
- **Modular Design**: Each service has a single responsibility
- **Type Safety**: All data structures use Pydantic models
- **Documentation**: Google-style docstrings for all public methods
- **Error Handling**: Comprehensive exception management
- **Testing**: Unit tests for all major functionality

## 📝 License

This project is licensed under the **BSD 3-Clause License** - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Target**: Originally built for Dell API documentation extraction
- **WebDriver**: Uses Selenium WebDriver for robust web navigation
- **UI**: Rich library for beautiful progress bars and console output
- **Validation**: Pydantic for type-safe configuration and data models
- **Architecture**: Inspired by clean architecture and SOLID principles

## 📚 Additional Resources

- **[Release Notes](https://github.com/doubletap-dave/wyrm/releases)**: Detailed changelog and version history
- **[Issues](https://github.com/doubletap-dave/wyrm/issues)**: Bug reports and feature requests
- **[Discussions](https://github.com/doubletap-dave/wyrm/discussions)**: Community support and questions

---

**🚀 Ready to extract comprehensive API documentation? Get started with Wyrm today!**
