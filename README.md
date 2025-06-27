# Wyrm - Developer API Documentation Scraper

A powerful Python tool for extracting comprehensive API documentation from complex web interfaces. Wyrm specializes in navigating dynamic web documentation sites and converting them into well-structured Markdown files.

## 🚀 Features

- **Multi-Response Extraction**: Captures all API response codes (200, 400, 401, 403, 404, 500+) per endpoint
- **Professional Schema Documentation**: Hierarchical structure with proper indentation and data types
- **Comprehensive Content**: Extracts API endpoints, parameters, responses, schemas, and descriptions
- **Robust Navigation**: Handles complex dynamic web interfaces with intelligent waiting and error recovery
- **Progress Tracking**: Real-time progress bar with detailed status updates
- **Smart Resume**: Automatically skips existing files and resumes where you left off
- **Flexible Output**: Organized directory structure with clean Markdown formatting
- **Debug Support**: Extensive logging and HTML capture for troubleshooting

## 📋 Requirements

- Python 3.8+
- Microsoft Edge browser (for WebDriver)
- Internet connection

## 🛠️ Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/doubletap-dave/developer-api-scraper.git
   cd developer-api-scraper
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## ⚙️ Configuration

The scraper uses a `config.yaml` file for configuration. The default configuration works for Dell PowerFlex Block API documentation:

```yaml
target_url: "https://developer.dell.com/apis/4008/versions/4.6.1/docs"
output_directory: "output"
log_file: "logs/wyrm.log"
log_level: "INFO"

webdriver:
  browser: "edge"
  headless: true

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

behavior:
  max_expand_attempts: 10

debug_settings:
  output_directory: "output/debug"
  save_structure_filename: "structure_debug.json"
  save_html_filename: "sidebar_debug.html"
  non_headless_pause_seconds: 10
```

## 🚀 Usage

### Basic Usage

Extract all API documentation:
```bash
python main.py
```

### Common Options

**Force overwrite existing files:**
```bash
python main.py --force
```

**Debug mode (non-headless, detailed logging):**
```bash
python main.py --debug
```

**Limit number of items to process:**
```bash
python main.py --max-items 10
```

**Run in non-headless mode:**
```bash
python main.py --no-headless
```

**Custom configuration file:**
```bash
python main.py --config my-config.yaml
```

### Advanced Usage

**Process specific item (for testing):**
```bash
python main.py --test-item-id docs-node-7145406 --debug --force
```

**Custom log level:**
```bash
python main.py --log-level DEBUG
```

**Check resume status:**
```bash
python main.py --resume-info
```

**Save structure and HTML for debugging:**
```bash
python main.py --save-structure --save-html --debug
```

## 📁 Output Structure

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
    └── structure_debug.json
```

## 📄 Output Format

Each API endpoint is extracted as a comprehensive Markdown file:

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

### 200
/api/instances/System::{id}

### application/json

### Schema
| Property | Type | Description |
|----------|------|-------------|
| System | object | System objects |
|   id | string |  |
|   name | string |  |
|   systemVersionName | string |  |
|   mdmManagementPort | integer |  |
|   capacityAlertHighThresholdPercent | number | Default value for newly created storage pool |
|   ...

### 400
Bad Request response...

### 401
Unauthorized response...

### 403
Forbidden response...

### 404
Not Found response...

### 500
Internal Server Error response...
```

## 🔧 Command Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `--config` | Path to configuration file | `--config my-config.yaml` |
| `--headless` / `--no-headless` | Run browser in headless mode | `--no-headless` |
| `--log-level` | Set logging level | `--log-level DEBUG` |
| `--debug` | Enable debug mode | `--debug` |
| `--force` | Overwrite existing files | `--force` |
| `--max-items` | Limit items to process | `--max-items 5` |
| `--test-item-id` | Process specific item (deprecated) | `--test-item-id docs-node-123` |
| `--resume-info` | Show resume status and exit | `--resume-info` |
| `--save-structure` | Save sidebar structure | `--save-structure` |
| `--save-html` | Save raw HTML | `--save-html` |

## 🐛 Troubleshooting

### Common Issues

**Site loading timeout:**
```bash
# Try non-headless mode to see what's happening
python main.py --no-headless --debug

# Or increase timeout in config.yaml
delays:
  navigation: 30
  sidebar_wait: 30
```

**Missing content:**
```bash
# Enable debug mode to capture HTML
python main.py --debug --save-html

# Check debug files in output/debug/
```

**Progress bar not updating:**
- This has been fixed in v1.0.0+
- Ensure you're using the latest version

**Resume after interruption:**
```bash
# Check what's been processed vs what's left
python main.py --resume-info

# Resume processing (automatically skips existing files)
python main.py

# Force re-process everything
python main.py --force
```

### Debug Mode

Debug mode provides extensive troubleshooting information:
- Non-headless browser (you can see what's happening)
- Detailed DEBUG-level logging
- HTML content capture for each page
- Structure files for analysis

```bash
python main.py --debug --max-items 1
```

## 🔄 Resume Functionality

Wyrm automatically handles interrupted scraping sessions:

### Automatic Resume
- **Smart Detection**: Automatically detects existing files and skips them
- **Fast Resume**: No need to re-navigate to already processed pages
- **Progress Preservation**: Maintains progress across sessions

### Resume Commands
```bash
# Check resume status
python main.py --resume-info

# Resume where you left off (default behavior)
python main.py

# Force re-process all files
python main.py --force
```

### Resume Information Output
```
📊 Resume Information:
  Total items in structure: 1596
  ✅ Already processed: 63
  🔄 Need processing: 1533
  📁 Output directory: output

✅ Existing files (63):
    PowerFlex -> output/introduction/powerflex.md
    Authentication -> output/getting-started/powerapi/authentication.md
    ...

🔄 Need processing (1533):
    Query System's Protection Domains (ID: docs-node-7145407)
    Query System's SDCs (ID: docs-node-7145408)
    ...

💡 To resume processing: python main.py
💡 To force re-process all: python main.py --force
```

## 📊 Performance

- **Extraction Speed**: ~2-5 seconds per API endpoint
- **Content Quality**: 6-8 response codes per endpoint
- **Coverage**: 40% more content than basic extraction
- **Memory Usage**: Optimized for large documentation sites

## 🏗️ Architecture

Wyrm is built with a modular architecture:

- **`main.py`**: Entry point and orchestration
- **`wyrm/navigation.py`**: Web navigation and element interaction
- **`wyrm/content_extractor.py`**: Content extraction and conversion
- **`wyrm/sidebar_parser.py`**: Sidebar structure parsing
- **`wyrm/storage.py`**: File organization and saving
- **`wyrm/driver_setup.py`**: WebDriver configuration
- **`wyrm/utils.py`**: Utilities and configuration

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

This project is licensed under the BSD 3-Clause License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built for extracting Dell API documentation, just update the target
- Uses Selenium WebDriver for robust web navigation
- Rich library for beautiful progress bars and logging
