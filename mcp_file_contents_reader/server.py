#!/usr/bin/env python3

import asyncio
import base64
import logging
import tempfile
import uuid
import os
import sys
import glob
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import aiofiles
from fastmcp import FastMCP
from .file_handlers import ExcelHandler, PDFHandler, PPTHandler, WordHandler, FileHandlerError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastMCP 인스턴스 생성
mcp = FastMCP(name="mcp-file-reader")

# 파일 핸들러 초기화
handlers = {
    'xlsx': ExcelHandler(),
    'xls': ExcelHandler(),
    'pdf': PDFHandler(),
    'pptx': PPTHandler(),
    'ppt': PPTHandler(),
    'docx': WordHandler(),
    'doc': WordHandler(),
}

# 임시 디렉토리 설정
temp_dir = Path(tempfile.gettempdir()) / "mcp-file-reader"
temp_dir.mkdir(exist_ok=True)
uploaded_files: Dict[str, Dict[str, Any]] = {}

@mcp.tool()
async def read_file(file_path: str, sheet_name: Optional[str] = None, page_range: Optional[str] = None) -> str:
    """Read Excel, PDF, PPT, Word files and return content as text."""
    try:
        file_path_obj = Path(file_path).expanduser()
        if not file_path_obj.exists():
            return f"File not found: {file_path_obj}"
        
        extension = file_path_obj.suffix.lower().lstrip('.')
        if extension not in handlers:
            return f"Unsupported file format: {extension}"
        
        handler = handlers[extension]
        content = await handler.read_file(
            file_path_obj,
            sheet_name=sheet_name,
            page_range=page_range
        )
        
        return content
    except FileHandlerError as e:
        return f"File reading error: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
async def list_supported_formats() -> str:
    """Return list of supported file formats."""
    formats = {
        "Excel": [".xlsx", ".xls"],
        "PDF": [".pdf"],
        "PowerPoint": [".pptx", ".ppt"],
        "Word": [".docx", ".doc"]
    }
    
    format_text = "Supported file formats:\n\n"
    for format_name, extensions in formats.items():
        format_text += f"• {format_name}: {', '.join(extensions)}\n"
    
    return format_text

@mcp.tool()
async def get_file_info(file_path: str) -> str:
    """Return basic information about a file."""
    try:
        file_path_obj = Path(file_path).expanduser()
        if not file_path_obj.exists():
            return f"File not found: {file_path_obj}"
        
        stat = file_path_obj.stat()
        info = {
            "Filename": file_path_obj.name,
            "Path": str(file_path_obj.absolute()),
            "Size": f"{stat.st_size:,} bytes",
            "Modified": stat.st_mtime,
            "Extension": file_path_obj.suffix,
            "Supported": file_path_obj.suffix.lower().lstrip('.') in handlers
        }
        
        info_text = "File information:\n\n"
        for key, value in info.items():
            info_text += f"• {key}: {value}\n"
        
        return info_text
    except Exception as e:
        return f"File info error: {str(e)}"

@mcp.tool()
async def upload_file(file_data: str, filename: str) -> str:
    """Upload and temporarily store Base64 encoded file data."""
    try:
        if not file_data or not filename:
            return "file_data and filename are required."
        
        file_bytes = base64.b64decode(file_data)
        
        file_id = str(uuid.uuid4())
        
        temp_file_path = temp_dir / f"{file_id}_{filename}"
        async with aiofiles.open(temp_file_path, 'wb') as f:
            await f.write(file_bytes)
        
        file_info = {
            "file_id": file_id,
            "filename": filename,
            "file_path": str(temp_file_path),
            "file_size": len(file_bytes),
            "upload_time": asyncio.get_event_loop().time()
        }
        uploaded_files[file_id] = file_info
        
        result_text = f"File upload successful!\n"
        result_text += f"• File ID: {file_id}\n"
        result_text += f"• Filename: {filename}\n"
        result_text += f"• File size: {len(file_bytes):,} bytes\n"
        result_text += f"• Supported: {filename.split('.')[-1].lower() in handlers}"
        
        return result_text
        
    except Exception as e:
        return f"File upload error: {str(e)}"

@mcp.tool()
async def read_uploaded_file(file_id: str, sheet_name: Optional[str] = None, page_range: Optional[str] = None) -> str:
    """Read uploaded file and return content."""
    try:
        if file_id not in uploaded_files:
            return f"File ID not found: {file_id}"
        
        file_info = uploaded_files[file_id]
        file_path = Path(file_info["file_path"])
        filename = file_info["filename"]
        
        extension = file_path.suffix.lower().lstrip('.')
        if extension not in handlers:
            return f"Unsupported file format: {extension}"
        
        handler = handlers[extension]
        content = await handler.read_file(
            file_path,
            sheet_name=sheet_name,
            page_range=page_range
        )
        
        result_text = f"Uploaded file read successful!\n"
        result_text += f"• Filename: {filename}\n"
        result_text += f"• Content length: {len(content)} characters\n\n"
        result_text += "File content:\n"
        result_text += content
        
        return result_text
        
    except Exception as e:
        return f"Uploaded file read error: {str(e)}"

@mcp.tool()
async def list_uploaded_files() -> str:
    """Return list of uploaded files."""
    if not uploaded_files:
        return "No uploaded files."
    
    result_text = "Uploaded files list:\n\n"
    for file_id, file_info in uploaded_files.items():
        result_text += f"• File ID: {file_id}\n"
        result_text += f"  - Filename: {file_info['filename']}\n"
        result_text += f"  - Size: {file_info['file_size']:,} bytes\n"
        result_text += f"  - Upload time: {file_info['upload_time']:.2f}\n\n"
    
    return result_text

@mcp.tool()
async def delete_uploaded_file(file_id: str) -> str:
    """Delete uploaded file."""
    try:
        if file_id not in uploaded_files:
            return f"File ID not found: {file_id}"
        
        file_info = uploaded_files[file_id]
        file_path = Path(file_info["file_path"])
        
        if file_path.exists():
            file_path.unlink()
        
        del uploaded_files[file_id]
        
        return f"File deleted successfully: {file_info['filename']}"
        
    except Exception as e:
        return f"File deletion error: {str(e)}"

@mcp.tool()
async def search_documents(keywords: List[str], search_path: str = "~/Documents", file_types: List[str] = None) -> str:
    """Search for specific content in Documents directory and analyze files."""
    if file_types is None:
        file_types = ["pdf", "docx", "xlsx", "pptx", "doc", "xls", "ppt"]
    
    if not keywords:
        return "Keywords are required for search."
    
    try:
        # Expand tilde in path
        search_path = os.path.expanduser(search_path)
        search_path = Path(search_path)
        
        if not search_path.exists():
            return f"Search path does not exist: {search_path}"
        
        # Find files with specified extensions
        found_files = []
        for file_type in file_types:
            pattern = f"**/*.{file_type}"
            files = list(search_path.glob(pattern))
            found_files.extend(files)
        
        # Remove duplicates and filter out node_modules
        found_files = list(set([f for f in found_files if "node_modules" not in str(f)]))
        
        result_text = f"🔍 Searching in: {search_path}\n"
        result_text += f"📝 Keywords: {', '.join(keywords)}\n"
        result_text += f"📁 Found {len(found_files)} files to analyze\n\n"
        
        matching_files = []
        
        for file_path in found_files[:20]:  # Limit to first 20 files
            try:
                # Read file content
                with open(file_path, 'rb') as f:
                    file_bytes = f.read()
                file_data = base64.b64encode(file_bytes).decode('utf-8')
                
                # Upload file to server
                upload_result = await upload_file(file_data, file_path.name)
                
                if "File ID:" in upload_result:
                    file_id = upload_result.split("File ID:")[1].split("\n")[0].strip()
                    
                    # Read file content
                    read_result = await read_uploaded_file(file_id)
                    
                    if "File content:" in read_result:
                        content = read_result.split("File content:")[1].strip()
                        
                        # Search for keywords
                        found_keywords = []
                        for keyword in keywords:
                            if keyword.lower() in content.lower():
                                found_keywords.append(keyword)
                        
                        if found_keywords:
                            matching_files.append({
                                'file': file_path.name,
                                'path': str(file_path),
                                'keywords': found_keywords,
                                'content_preview': content[:300] + "..." if len(content) > 300 else content
                            })
                        
                        # Clean up uploaded file
                        await delete_uploaded_file(file_id)
                        
            except Exception as e:
                continue
        
        # Format results
        if matching_files:
            result_text += f"🎯 Found {len(matching_files)} file(s) with matching content:\n\n"
            for i, file_info in enumerate(matching_files, 1):
                result_text += f"{i}. 📄 {file_info['file']}\n"
                result_text += f"   Path: {file_info['path']}\n"
                result_text += f"   Keywords: {', '.join(file_info['keywords'])}\n"
                result_text += f"   Preview: {file_info['content_preview']}\n\n"
        else:
            result_text += "❌ No files found with matching content.\n"
            result_text += "💡 Try different keywords or check if files exist in the search path."
        
        return result_text
        
    except Exception as e:
        return f"Search error: {str(e)}"

@mcp.tool()
async def analyze_file_content(file_path: str, extract_patterns: List[str] = None) -> str:
    """Analyze specific file content in detail and extract structured information."""
    if extract_patterns is None:
        extract_patterns = []
    
    try:
        file_path_obj = Path(file_path).expanduser()
        if not file_path_obj.exists():
            return f"File not found: {file_path}"
        
        # Read file content
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
        file_data = base64.b64encode(file_bytes).decode('utf-8')
        
        # Upload file to server
        upload_result = await upload_file(file_data, file_path_obj.name)
        
        if "File ID:" in upload_result:
            file_id = upload_result.split("File ID:")[1].split("\n")[0].strip()
            
            # Read file content
            read_result = await read_uploaded_file(file_id)
            
            if "File content:" in read_result:
                content = read_result.split("File content:")[1].strip()
                
                result_text = f"📋 Analyzing: {file_path_obj.name}\n"
                result_text += f"📁 Path: {file_path}\n"
                result_text += f"📊 Content length: {len(content)} characters\n\n"
                
                result_text += "📄 FULL CONTENT:\n"
                result_text += "=" * 60 + "\n"
                result_text += content + "\n"
                result_text += "=" * 60 + "\n\n"
                
                # Extract structured information if patterns provided
                if extract_patterns:
                    result_text += "🔍 EXTRACTED INFORMATION:\n"
                    result_text += "=" * 60 + "\n"
                    
                    lines = content.split('\n')
                    extracted_info = {}
                    
                    for pattern in extract_patterns:
                        extracted_info[pattern] = []
                        for line in lines:
                            line = line.strip()
                            if pattern.lower() in line.lower():
                                extracted_info[pattern].append(line)
                    
                    for pattern, matches in extracted_info.items():
                        if matches:
                            result_text += f"\n📌 {pattern.upper()}:\n"
                            for match in matches:
                                result_text += f"   • {match}\n"
                        else:
                            result_text += f"\n📌 {pattern.upper()}: No matches found\n"
                
                # Clean up uploaded file
                await delete_uploaded_file(file_id)
                
                return result_text
        
        return "Failed to process file."
        
    except Exception as e:
        return f"Analysis error: {str(e)}"

def cli_main():
    """Entry point for the command line interface."""
    try:
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"CLI error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    cli_main()