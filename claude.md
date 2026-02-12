# Claude Rules
## Rule 1

PowerShell v5 syntax - use semicolons (;) not double-ampersand (&&) for command chaining

## Rule 2

Use mcp-ondemand.ps1 for dynamic MCP server loading - verify servers with mcps command and run mcp-on or mcp-off to use the mcps that you need for the tasks

## Rule 3

always read all md files in the folder!

## Rule 4

100% autonomous operation - background tasks auto-run without prompts, complete tasks fully with test verification

## Rule 5

Fix root causes, not symptoms - trace dependencies before edits, never suppress errors with as any or @ts-ignore

## Rule 6

Prefer editing existing files over creating new ones - never write new files unless explicitly requested

## Rule 7

Run lsp_diagnostics on all changed files before completion

## Rule 8

Verify with tests before marking any task complete - ensure all tests pass

## Rule 9

Real-time progress updates - mark [x] on completion of each step

## Rule 10

Log all errors to .claude/learned.md for future reference

## Rule 11

Clean up after operations - purge non-essential files, cancel background tasks before final answer

## Rule 12

Document all changes and fixes - update/create agents.md or architecture.md on infrastructure changes

## Rule 13

Create clear, descriptive commit messages when explicitly requested

## Rule 14

STOP HOOK: Smart hook that only blocks when there are uncommitted changes AND build/test failures. Allows stop freely for Q&A, research, and clean projects. Override with: `New-Item -Path "$env:TEMP\claude_task_complete" -Force`


