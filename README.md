# MCP File Contents Reader

A Model Context Protocol (MCP) server for reading and analyzing various file formats including <b>PDF, Excel, Word, and PowerPoint documents</b>.

## Features

- **Multi-format Support**: Read PDF, Excel (.xlsx, .xls), Word (.docx, .doc), and PowerPoint (.pptx, .ppt) files
- **Content Analysis**: Extract and analyze file contents with structured information extraction
- **Document Search**: Search for specific content across multiple documents
- **File Upload**: Support for temporary file upload and processing
- **MCP Integration**: Full Model Context Protocol compliance

## Installation

### Using uvx (Recommended)

```bash
uvx mcp-file-contents-reader
```

### Using pip

```bash
pip install mcp-file-contents-reader
```

### From Source

```bash
git clone https://github.com/yourusername/mcp-file-contents-reader.git
cd mcp-file-contents-reader
pip install -e .
```

## Usage

### MCP Configuration

Add the following to your `mcp.json` configuration file:

```json
{
  "mcpServers": {
    "file-reader": {
      "command": "uvx",
      "args": ["mcp-file-contents-reader"]
    }
  }
}
```

Or if installed via pip:

```json
{
  "mcpServers": {
    "file-reader": {
      "command": "mcp-file-contents-reader"
    }
  }
}
```

### Available Tools

#### 1. `read_file`

Read Excel, PDF, PPT, Word files and return content as text.

**Parameters:**

- `file_path` (required): Path to the file to read
- `sheet_name` (optional): Sheet name for Excel files
- `page_range` (optional): Page range for PDF files (e.g., '1-5' or '1,3,5')

#### 2. `search_documents`

Search for specific content in Documents directory and analyze files.

**Parameters:**

- `keywords` (required): Keywords to search for in file content
- `search_path` (optional): Directory path to search (default: ~/Documents)
- `file_types` (optional): File types to search (default: ["pdf", "docx", "xlsx", "pptx", "doc", "xls", "ppt"])

#### 3. `analyze_file_content`

Analyze specific file content in detail and extract structured information.

**Parameters:**

- `file_path` (required): Path to the file to analyze
- `extract_patterns` (optional): Specific patterns or information types to extract

#### 4. `upload_file`

Upload and temporarily store Base64 encoded file data.

**Parameters:**

- `file_data` (required): Base64 encoded file data
- `filename` (required): Filename with extension

#### 5. `read_uploaded_file`

Read uploaded file and return content.

**Parameters:**

- `file_id` (required): ID of the uploaded file

#### 6. `list_uploaded_files`

Return list of uploaded files.

#### 7. `delete_uploaded_file`

Delete uploaded file.

**Parameters:**

- `file_id` (required): ID of the file to delete

#### 8. `get_file_info`

Return basic information about a file.

**Parameters:**

- `file_path` (required): Path to the file to get information about

#### 9. `list_supported_formats`

Return list of supported file formats.

## Supported File Formats

- **Excel**: .xlsx, .xls
- **PDF**: .pdf
- **PowerPoint**: .pptx, .ppt
- **Word**: .docx, .doc

## Example Usage

### Search for donation receipts

```json
{
  "tool": "search_documents",
  "arguments": {
    "keywords": ["donation", "receipt", "charity", "fund"],
    "search_path": "/Users/username/Documents",
    "file_types": ["pdf", "docx", "xlsx"]
  }
}
```

### Analyze a specific file

```json
{
  "tool": "analyze_file_content",
  "arguments": {
    "file_path": "/Users/username/Documents/receipt.pdf",
    "extract_patterns": ["donor", "amount", "organization", "date"]
  }
}
```

## Development

### Setup Development Environment

```bash
git clone https://github.com/yourusername/mcp-file-contents-reader.git
cd mcp-file-contents-reader
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black mcp_file_reader/
```

### Type Checking

```bash
mypy mcp_file_reader/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for your changes
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Changelog

### 1.0.0

- Initial release
- Support for PDF, Excel, Word, and PowerPoint files
- MCP server implementation
- Document search and analysis capabilities
