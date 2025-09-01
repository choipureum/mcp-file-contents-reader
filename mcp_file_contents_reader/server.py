#!/usr/bin/env python3

import asyncio
import json
import logging
import base64
import tempfile
import uuid
import os
import glob
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import aiofiles
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.server.lowlevel import NotificationOptions
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    Resource,
    ListResourcesRequest,
    ListResourcesResult,
    ReadResourceRequest,
    ReadResourceResult,
)
from pydantic import BaseModel

from .file_handlers import (
    ExcelHandler,
    PDFHandler,
    PPTHandler,
    WordHandler,
    FileHandlerError
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileReaderServer:
    def __init__(self):
        self.server = Server("mcp-file-reader")
        self.handlers = {
            'xlsx': ExcelHandler(),
            'xls': ExcelHandler(),
            'pdf': PDFHandler(),
            'pptx': PPTHandler(),
            'ppt': PPTHandler(),
            'docx': WordHandler(),
            'doc': WordHandler(),
        }
        self.temp_dir = Path(tempfile.gettempdir()) / "mcp-file-reader"
        self.temp_dir.mkdir(exist_ok=True)
        self.uploaded_files: Dict[str, Dict[str, Any]] = {}
        self._setup_handlers()
    
    def _setup_handlers(self):
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            # Return list of tools directly, not ListToolsResult
            return [
                Tool(
                    name="read_file",
                    description="Read Excel, PDF, PPT, Word files and return content as text.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file to read"
                            },
                            "sheet_name": {
                                "type": "string",
                                "description": "Sheet name for Excel files (optional)"
                            },
                            "page_range": {
                                "type": "string",
                                "description": "Page range for PDF files (e.g., '1-5' or '1,3,5') (optional)"
                            }
                        },
                        "required": ["file_path"]
                    }
                ),
                Tool(
                    name="list_supported_formats",
                    description="Return list of supported file formats.",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="get_file_info",
                    description="Return basic information about a file.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file to get information about"
                            }
                        },
                        "required": ["file_path"]
                    }
                ),
                Tool(
                    name="upload_file",
                    description="Upload and temporarily store Base64 encoded file data.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_data": {
                                "type": "string",
                                "description": "Base64 encoded file data"
                            },
                            "filename": {
                                "type": "string",
                                "description": "Filename with extension"
                            }
                        },
                        "required": ["file_data", "filename"]
                    }
                ),
                Tool(
                    name="read_uploaded_file",
                    description="Read uploaded file and return content.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_id": {
                                "type": "string",
                                "description": "ID of the uploaded file"
                            },
                            "sheet_name": {
                                "type": "string",
                                "description": "Sheet name for Excel files (optional)"
                            },
                            "page_range": {
                                "type": "string",
                                "description": "Page range for PDF files (e.g., '1-5' or '1,3,5') (optional)"
                            }
                        },
                        "required": ["file_id"]
                    }
                ),
                Tool(
                    name="list_uploaded_files",
                    description="Return list of uploaded files.",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="delete_uploaded_file",
                    description="Delete uploaded file.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_id": {
                                "type": "string",
                                "description": "ID of the file to delete"
                            }
                        },
                        "required": ["file_id"]
                    }
                ),
                Tool(
                    name="search_documents",
                    description="Search for specific content in Documents directory and analyze files.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "search_path": {
                                "type": "string",
                                "description": "Directory path to search (default: ~/Documents)",
                                "default": "~/Documents"
                            },
                            "keywords": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Keywords to search for in file content"
                            },
                            "file_types": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "File types to search (pdf, docx, xlsx, pptx, etc.)",
                                "default": ["pdf", "docx", "xlsx", "pptx", "doc", "xls", "ppt"]
                            }
                        },
                        "required": ["keywords"]
                    }
                ),
                Tool(
                    name="analyze_file_content",
                    description="Analyze specific file content in detail and extract structured information.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file to analyze"
                            },
                            "extract_patterns": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Specific patterns or information types to extract (optional)"
                            }
                        },
                        "required": ["file_path"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            try:
                if name == "read_file":
                    return await self._handle_read_file(arguments)
                elif name == "list_supported_formats":
                    return await self._handle_list_formats()
                elif name == "get_file_info":
                    return await self._handle_get_file_info(arguments)
                elif name == "upload_file":
                    return await self._handle_upload_file(arguments)
                elif name == "read_uploaded_file":
                    return await self._handle_read_uploaded_file(arguments)
                elif name == "list_uploaded_files":
                    return await self._handle_list_uploaded_files()
                elif name == "delete_uploaded_file":
                    return await self._handle_delete_uploaded_file(arguments)
                elif name == "search_documents":
                    return await self._handle_search_documents(arguments)
                elif name == "analyze_file_content":
                    return await self._handle_analyze_file_content(arguments)
                else:
                    return CallToolResult(
                        content=[TextContent(type="text", text=f"Unknown tool: {name}")]
                    )
            except Exception as e:
                logger.error(f"Error executing tool: {e}")
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")]
                )
    
    async def _handle_read_file(self, arguments: Dict[str, Any]) -> CallToolResult:
        file_path = arguments.get("file_path")
        if not file_path:
            return CallToolResult(
                content=[TextContent(type="text", text="File path is required.")]
            )
        
        file_path = Path(file_path)
        if not file_path.exists():
            return CallToolResult(
                content=[TextContent(type="text", text=f"File not found: {file_path}")]
            )
        
        extension = file_path.suffix.lower().lstrip('.')
        if extension not in self.handlers:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unsupported file format: {extension}")]
            )
        
        try:
            handler = self.handlers[extension]
            content = await handler.read_file(
                file_path,
                sheet_name=arguments.get("sheet_name"),
                page_range=arguments.get("page_range")
            )
            
            return CallToolResult(
                content=[TextContent(type="text", text=content)]
            )
        except FileHandlerError as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"File reading error: {str(e)}")]
            )
    
    async def _handle_list_formats(self) -> CallToolResult:
        formats = {
            "Excel": [".xlsx", ".xls"],
            "PDF": [".pdf"],
            "PowerPoint": [".pptx", ".ppt"],
            "Word": [".docx", ".doc"]
        }
        
        format_text = "Supported file formats:\n\n"
        for format_name, extensions in formats.items():
            format_text += f"• {format_name}: {', '.join(extensions)}\n"
        
        return CallToolResult(
            content=[TextContent(type="text", text=format_text)]
        )
    
    async def _handle_get_file_info(self, arguments: Dict[str, Any]) -> CallToolResult:
        file_path = arguments.get("file_path")
        if not file_path:
            return CallToolResult(
                content=[TextContent(type="text", text="File path is required.")]
            )
        
        file_path = Path(file_path)
        if not file_path.exists():
            return CallToolResult(
                content=[TextContent(type="text", text=f"File not found: {file_path}")]
            )
        
        try:
            stat = file_path.stat()
            info = {
                "Filename": file_path.name,
                "Path": str(file_path.absolute()),
                "Size": f"{stat.st_size:,} bytes",
                "Modified": stat.st_mtime,
                "Extension": file_path.suffix,
                "Supported": file_path.suffix.lower().lstrip('.') in self.handlers
            }
            
            info_text = "File information:\n\n"
            for key, value in info.items():
                info_text += f"• {key}: {value}\n"
            
            return CallToolResult(
                content=[TextContent(type="text", text=info_text)]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"File info error: {str(e)}")]
            )
    
    async def _handle_upload_file(self, arguments: Dict[str, Any]) -> CallToolResult:
        file_data = arguments.get("file_data")
        filename = arguments.get("filename")
        
        if not file_data or not filename:
            return CallToolResult(
                content=[TextContent(type="text", text="file_data and filename are required.")]
            )
        
        try:
            file_bytes = base64.b64decode(file_data)
            
            file_id = str(uuid.uuid4())
            
            temp_file_path = self.temp_dir / f"{file_id}_{filename}"
            async with aiofiles.open(temp_file_path, 'wb') as f:
                await f.write(file_bytes)
            
            file_info = {
                "file_id": file_id,
                "filename": filename,
                "file_path": str(temp_file_path),
                "file_size": len(file_bytes),
                "upload_time": asyncio.get_event_loop().time()
            }
            self.uploaded_files[file_id] = file_info
            
            result_text = f"File upload successful!\n"
            result_text += f"• File ID: {file_id}\n"
            result_text += f"• Filename: {filename}\n"
            result_text += f"• File size: {len(file_bytes):,} bytes\n"
            result_text += f"• Supported: {filename.split('.')[-1].lower() in self.handlers}"
            
            return CallToolResult(
                content=[TextContent(type="text", text=result_text)]
            )
            
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"File upload error: {str(e)}")]
            )
    
    async def _handle_read_uploaded_file(self, arguments: Dict[str, Any]) -> CallToolResult:
        file_id = arguments.get("file_id")
        if not file_id:
            return CallToolResult(
                content=[TextContent(type="text", text="file_id is required.")]
            )
        
        if file_id not in self.uploaded_files:
            return CallToolResult(
                content=[TextContent(type="text", text=f"File ID not found: {file_id}")]
            )
        
        try:
            file_info = self.uploaded_files[file_id]
            file_path = Path(file_info["file_path"])
            filename = file_info["filename"]
            
            extension = file_path.suffix.lower().lstrip('.')
            if extension not in self.handlers:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Unsupported file format: {extension}")]
                )
            
            handler = self.handlers[extension]
            content = await handler.read_file(
                file_path,
                sheet_name=arguments.get("sheet_name"),
                page_range=arguments.get("page_range")
            )
            
            result_text = f"Uploaded file read successful!\n"
            result_text += f"• Filename: {filename}\n"
            result_text += f"• Content length: {len(content)} characters\n\n"
            result_text += "File content:\n"
            result_text += content
            
            return CallToolResult(
                content=[TextContent(type="text", text=result_text)]
            )
            
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Uploaded file read error: {str(e)}")]
            )
    
    async def _handle_list_uploaded_files(self) -> CallToolResult:
        if not self.uploaded_files:
            return CallToolResult(
                content=[TextContent(type="text", text="No uploaded files.")]
            )
        
        result_text = "Uploaded files list:\n\n"
        for file_id, file_info in self.uploaded_files.items():
            result_text += f"• File ID: {file_id}\n"
            result_text += f"  - Filename: {file_info['filename']}\n"
            result_text += f"  - Size: {file_info['file_size']:,} bytes\n"
            result_text += f"  - Upload time: {file_info['upload_time']:.2f}\n\n"
        
        return CallToolResult(
            content=[TextContent(type="text", text=result_text)]
        )
    
    async def _handle_delete_uploaded_file(self, arguments: Dict[str, Any]) -> CallToolResult:
        file_id = arguments.get("file_id")
        if not file_id:
            return CallToolResult(
                content=[TextContent(type="text", text="file_id is required.")]
            )
        
        if file_id not in self.uploaded_files:
            return CallToolResult(
                content=[TextContent(type="text", text=f"File ID not found: {file_id}")]
            )
        
        try:
            file_info = self.uploaded_files[file_id]
            file_path = Path(file_info["file_path"])
            
            if file_path.exists():
                file_path.unlink()
            
            del self.uploaded_files[file_id]
            
            return CallToolResult(
                content=[TextContent(type="text", text=f"File deleted successfully: {file_info['filename']}")]
            )
            
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"File deletion error: {str(e)}")]
            )
    
    async def _handle_search_documents(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Search for specific content in Documents directory"""
        search_path = arguments.get("search_path", "~/Documents")
        keywords = arguments.get("keywords", [])
        file_types = arguments.get("file_types", ["pdf", "docx", "xlsx", "pptx", "doc", "xls", "ppt"])
        
        if not keywords:
            return CallToolResult(
                content=[TextContent(type="text", text="Keywords are required for search.")]
            )
        
        try:
            # Expand tilde in path
            search_path = os.path.expanduser(search_path)
            search_path = Path(search_path)
            
            if not search_path.exists():
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Search path does not exist: {search_path}")]
                )
            
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
                    upload_result = await self._handle_upload_file({
                        "file_data": file_data,
                        "filename": file_path.name
                    })
                    
                    if upload_result.content and len(upload_result.content) > 0:
                        # Extract file ID from upload result
                        result_text_upload = upload_result.content[0].text
                        if "File ID:" in result_text_upload:
                            file_id = result_text_upload.split("File ID:")[1].split("\n")[0].strip()
                            
                            # Read file content
                            read_result = await self._handle_read_uploaded_file({
                                "file_id": file_id
                            })
                            
                            if read_result.content and len(read_result.content) > 0:
                                content = read_result.content[0].text
                                
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
                                await self._handle_delete_uploaded_file({"file_id": file_id})
                                
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
            
            return CallToolResult(
                content=[TextContent(type="text", text=result_text)]
            )
            
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Search error: {str(e)}")]
            )
    
    async def _handle_analyze_file_content(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Analyze specific file content in detail"""
        file_path = arguments.get("file_path")
        extract_patterns = arguments.get("extract_patterns", [])
        
        if not file_path:
            return CallToolResult(
                content=[TextContent(type="text", text="File path is required.")]
            )
        
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                return CallToolResult(
                    content=[TextContent(type="text", text=f"File not found: {file_path}")]
                )
            
            # Read file content
            with open(file_path, 'rb') as f:
                file_bytes = f.read()
            file_data = base64.b64encode(file_bytes).decode('utf-8')
            
            # Upload file to server
            upload_result = await self._handle_upload_file({
                "file_data": file_data,
                "filename": file_path_obj.name
            })
            
            if upload_result.content and len(upload_result.content) > 0:
                # Extract file ID from upload result
                result_text_upload = upload_result.content[0].text
                if "File ID:" in result_text_upload:
                    file_id = result_text_upload.split("File ID:")[1].split("\n")[0].strip()
                    
                    # Read file content
                    read_result = await self._handle_read_uploaded_file({
                        "file_id": file_id
                    })
                    
                    if read_result.content and len(read_result.content) > 0:
                        content = read_result.content[0].text
                        
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
                        await self._handle_delete_uploaded_file({"file_id": file_id})
                        
                        return CallToolResult(
                            content=[TextContent(type="text", text=result_text)]
                        )
            
            return CallToolResult(
                content=[TextContent(type="text", text="Failed to process file.")]
            )
            
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Analysis error: {str(e)}")]
            )
    
    async def run(self):
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="mcp-file-reader",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={}
                    ),
                ),
            )

async def main():
    server = FileReaderServer()
    await server.run()

def cli_main():
    """Entry point for the command line interface."""
    asyncio.run(main())

if __name__ == "__main__":
    cli_main()
