# MCP File Reader - Deployment Guide

This document explains how to deploy MCP File Reader to PyPI and use it with `uvx`.

## 📦 PyPI Deployment

### 1. Development Environment Setup

```bash
# Navigate to project directory
cd /path/to/mcp-file-reader

# Activate virtual environment (optional)
source .venv/bin/activate

# Install build tools
pip install build twine
```

### 2. Package Build

```bash
# Build package
python -m build

# Check built files
ls -la dist/
```

### 3. PyPI Account Setup

```bash
# Create PyPI account (https://pypi.org/account/register/)
# Generate API token (https://pypi.org/manage/account/token/)

# Create ~/.pypirc file
cat > ~/.pypirc << EOF
[distutils]
index-servers = pypi

[pypi]
username = __token__
password = pypi-your-api-token-here
EOF
```

### 4. Test Deployment (TestPyPI)

```bash
# Upload to TestPyPI
python -m twine upload --repository testpypi dist/*

# Test installation from TestPyPI
uvx --index-url https://test.pypi.org/simple/ mcp-file-reader
```

### 5. Production Deployment (PyPI)

```bash
# Upload to PyPI
python -m twine upload dist/*

# Test installation
uvx mcp-file-reader
```

## 🔧 MCP Configuration

### Using uvx

```json
{
  "mcpServers": {
    "file-reader": {
      "command": "uvx",
      "args": ["mcp-file-reader"],
      "env": {
        "PYTHONUNBUFFERED": "1",
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

### Using pip installation

```json
{
  "mcpServers": {
    "file-reader": {
      "command": "mcp-file-reader",
      "env": {
        "PYTHONUNBUFFERED": "1",
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

## 🚀 Usage

### 1. Direct execution with uvx

```bash
# Run MCP server
uvx mcp-file-reader

# Run specific version
uvx "mcp-file-reader==1.0.0"
```

### 2. Install and run with pip

```bash
# Install
pip install mcp-file-reader

# Run
mcp-file-reader
```

### 3. Development mode installation

```bash
# Install from source
pip install -e .

# Run
mcp-file-reader
```

## 📋 Version Management

### Version Update

1. Update version number in `pyproject.toml`:

   ```toml
   version = "1.0.1"
   ```

2. Rebuild package:

   ```bash
   python -m build
   ```

3. Upload to PyPI:
   ```bash
   python -m twine upload dist/*
   ```

### Git Tag Creation

```bash
# Create version tag
git tag v1.0.0
git push origin v1.0.0
```

## 🔍 Testing

### Local Testing

```bash
# Test package installation
pip install dist/mcp_file_reader-1.0.0-py3-none-any.whl

# Test execution
mcp-file-reader --help
```

### MCP Connection Testing

```bash
# Test with MCP client
# (Use MCP client tools)
```

## 📝 Deployment Checklist

- [ ] Update version number in `pyproject.toml`
- [ ] Update `README.md`
- [ ] All tests pass
- [ ] Package builds successfully
- [ ] Test on TestPyPI
- [ ] Deploy to PyPI
- [ ] Test installation and execution
- [ ] Create Git tag

## 🐛 Troubleshooting

### Build Errors

```bash
# Clear build cache
rm -rf build/ dist/ *.egg-info/
python -m build
```

### Upload Errors

```bash
# Check API token
cat ~/.pypirc

# Check network connection
ping pypi.org
```

### Installation Errors

```bash
# Clear uvx cache
uvx --clear-cache

# Clear pip cache
pip cache purge
```

## 📚 Additional Resources

- [PyPI User Guide](https://packaging.python.org/tutorials/packaging-projects/)
- [uvx Documentation](https://github.com/astral-sh/uv)
- [MCP Protocol Documentation](https://modelcontextprotocol.io/)
