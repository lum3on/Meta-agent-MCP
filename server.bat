@echo off
REM Meta Agent MCP Server startup script for Augment
REM This script starts the MCP server with stdio transport

REM Change to the project directory
cd /d "%~dp0"

REM Load environment variables from .env if it exists
if exist .env (
    for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
        if not "%%a"=="" if not "%%a:~0,1%"=="#" (
            set "%%a=%%b"
        )
    )
)

REM Run the MCP server
python -m meta_agent_mcp.server

