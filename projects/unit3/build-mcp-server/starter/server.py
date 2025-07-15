#!/usr/bin/env python3
"""
Module 1: Basic MCP Server - Starter Code
TODO: Implement tools for analyzing git changes and suggesting PR templates
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP, Context



# Initialize the FastMCP server
mcp = FastMCP("pr-agent", transport = "stdio")

# File where webhook server stores events
EVENTS_FILE = Path(__file__).parent / "github_events.json"

# PR template directory (shared across all modules)
TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"

# Default PR templates
DEFAULT_TEMPLATES = {
    "bug.md": "Bug Fix",
    "feature.md": "Feature",
    "docs.md": "Documentation",
    "refactor.md": "Refactor",
    "test.md": "Test",
    "performance.md": "Performance",
    "security.md": "Security"
}

# Type mapping for PR templates
TYPE_MAPPING = {
    "bug": "bug.md",
    "fix": "bug.md",
    "feature": "feature.md",
    "enhancement": "feature.md",
    "docs": "docs.md",
    "documentation": "docs.md",
    "refactor": "refactor.md",
    "cleanup": "refactor.md",
    "test": "test.md",
    "testing": "test.md",
    "performance": "performance.md",
    "optimization": "performance.md",
    "security": "security.md"
}


# TODO: Implement tool functions here
# Example structure for a tool:
# @mcp.tool()
# async def analyze_file_changes(base_branch: str = "main", include_diff: bool = True) -> str:
#     """Get the full diff and list of changed files in the current git repository.
#     
#     Args:
#         base_branch: Base branch to compare against (default: main)
#         include_diff: Include the full diff content (default: true)
#     """
#     # Your implementation here
#     pass

# Minimal stub implementations so the server runs
# TODO: Replace these with your actual implementations

# ===== Original Tools from Module 1 (with output limiting) =====

@mcp.tool()
async def analyze_file_changes(base_branch: str = "main", 
                              include_diff: bool = True,
                              max_diff_lines: int = 500,
                              working_directory: Optional[str] = None
                              ) -> str:
   
    """Analyze file changes with smart output limiting.
    
    Args:
        base_branch: Branch to compare against (default: main)
        include_diff: Whether to include the actual diff (default: ture)
        max_diff_lines: Maximum diff lines to include (default 500)
        working_directory: Directory to run it commands in (default: current directory)
    """
   
    try:
        # Try to get working directory from roots first
        if working_directory is None:
            try:
                context = mcp.get_context()
                roots_result = await context.session.list_roots()
                # Get the first root - Claude Code sets this to the CWD
                root = roots_result.roots[0]
                # FileUrl objects has a .path property that gives us the path directly
                working_directory = root.uri.path
            except Exception:
                # If we can't get roots, fall back to current directory
                pass
            
        # Use provided working directory or current directory
        cwd = working_directory if working_directory else os.getcwd()
        
        # Debug output
        debug_info = {
            "provided_working_directory": working_directory,
            "actual_cwd": cwd,
            "server_process_cwd": os.getcwd(),
            "server_file_location": str(Path(__file__).parent),
            "roots_check": None
        }
        
        
        # Add roots debug info
        try:
            context = mcp.get_context()
            roots_result = await context.session.list_roots()
            debug_info["roots_check"] = {
                "found": True,
                "count": len(roots_result.roots),
                "roots": [str(root.uri) for root in roots_result.roots]
            }
        except Exception as e:
            debug_info["roots_check"] = {
                "found": False,
                "error": str(e)
            }
            
        # Get list of changed files
        files_result = subprocess.run(
            ["git", "diff", "--name-status", f"{base_branch}...HEAD"],
            capture_output = True,
            text = True,
            check = True,
            cwd = cwd
        )
        
        # Get diff statistics
        stat_result = subprocess.run(
            ["git", "diff","--stat", f"{base_branch}...HEAD"],
            capture_output = True,
            text = True,
            cwd = cwd
        )
        
        # Get the actual diff if requested
        diff_content = ""
        truncated = False
        if include_diff:
            diff_result = subprocess.run(
                ["git", "diff", f"{base_branch}...HEAD"],
                capture_output = True,
                text = True,
                cwd = cwd
            )
            diff_lines = diff_result.stdout.split('\n')
            
            # Check if we need to truncate
            if len(diff_lines) > max_diff_lines:
                diff_content = '\n'.join(diff_lines[:max_diff_lines])
                diff_content += f"\n\n... Output truncated. Showing {max_diff_lines} of {len(diff_lines)} lines..."
                diff_content += "\n... Use max_diff_lines parameter to see more..."
                truncated = True
            else:
                diff_content = diff_result.stdout
                
        # Get commit message for context
        commits_result = subprocess.run(
            ["git", "log", "--oneline", f"{base_branch}...HEAD"],
            capture_output = True,
            text = True,
            cwd = cwd
        )
        
        
        analysis = {
            "base_branch": base_branch,
            "files_changed": files_result.stdout,
            "statistics": stat_result.stdout,
            "commits": commits_result.stdout,
            "diff": diff_content if include_diff else "Diff not included (set include_diff = True to see full diff)",
            "truncated": truncated,
            "total_diff_lines": len(diff_lines) if include_diff else 0,
            "_debug": debug_info
        }
        
        return json.dumps(analysis, indent = 2)

    
    except subprocess.CalledProcessError as e:
        return json.dumps({"error": f"Git error: {e.stderr}"})
    except Exception as e:
        return json.dumps({"error": str(e)})
    
    
        



@mcp.tool()
async def get_pr_templates() -> str:
    """List available PR templates with their content."""
    templates = [
        {
            "filename": filename,
            "type": template_type,
            "content": (TEMPLATES_DIR / filename).read_text()
        }
        for filename, template_type in DEFAULT_TEMPLATES.items()
    ]
    
    return json.dumps(templates, indent = 2)
    


@mcp.tool()
async def suggest_template(changes_summary: str, change_type: str) -> str:
    """Let Claude analyze the changes and suggest the most appropriate PR template.
    
    Args:
        changes_summary: Your analysis of what the changes do
        change_type: The type of change you've identified (bug, feature, docs, refactor, test, etc.)
    """
    # TODO: Implement this tool
    
    # Get available templates
    templates_response = await get_pr_templates()
    templates = json.loads(templates_response)
    
    # Find matching template
    template_file = TYPE_MAPPING.get(change_type.lower(), "feature.md")
    selected_template = next(
        (t for t in templates if t["filename"] == template_file),
        templates[0] # Default to first template if no match
    )
    
    suggestion = {
        "recommended_template": selected_template,
        "reasoning": f"Based on your analysis: '{changes_summary}', this appears to be a {change_type} change.",
        "template_content": selected_template["content"],
        "usage_hint": "Claude can help you fill out this template based on the specific changes in your PR."
    }
    
    return json.dumps(suggestion, indent = 2)

# ===== Module 2: New GitHub Actions Tools =====

@mcp.tool()
async def get_recent_actions_events(limit: int = 10) -> str:
    """Get recent GitHub Actions events received via webhook.
    
    Args:
        limit: Maximum number of events to return (default: 10)
    """
    # TODO: Implement this function
    # 1. Check if EVENTS_FILE exists
    if not EVENTS_FILE.exists():
        return json.dumps([])
    # 2. Read the JSON file
    with open(EVENTS_FILE, 'r') as f:
        events = json.load(f)
    # 3. Return the most recent events (up to limit)
    if limit > 0:
        events = events[-limit:]
    # 4. Return empty list if file doesn't exist
    return json.dumps(events, indent = 2)
    
    return json.dumps({"message": "TODO: Implement get_recent_actions_events"})


@mcp.tool()
async def get_workflow_status(workflow_name: Optional[str] = None) -> str:
    """Get the current status of GitHub Actions workflows.
    
    Args:
        workflow_name: Optional specific workflow name to filter by
    """
    # TODO: Implement this function
    # 1. Read events from EVENTS_FILE
    if not EVENTS_FILE.exists():
        return json.dumps({"message": "No GitHub Action events found."})
    
    with open(EVENTS_FILE, 'r') as f:
        events = json.load(f)
        
    if not events:
        return json.dumps({"message": "No GitHub Action events found."})
    # 2. Filter events for workflow_run events
    workflow_events = [
        event for event in events if event.get("workflow_run") is not None
    ]
    # 3. If workflow_name provided, filter by that name
    if workflow_name:
        workflow_events = [
            event for event in workflow_events
            if event["workflow_run"].get("name") == workflow_name
        ]
    # 4. Group by workflow and show latest status
    workflows = {}
    for event in workflow_events:
        run = event["workflow_run"]
        name = run["name"]
        if name not in workflows or run["updated_at"] > workflows[name]["updated_at"]:
            workflows[name] = {
                "name": name,
                "status": run["status"],
                "conclusion": run.get("conclusion"),
                "updated_at": run["updated_at"],
                "url": run["html_url"],
                "repository": event.get("repository", {}).get("full_name"),
                #"sender": event.get("sender", {}).get("login")
            }
    # 5. Return formatted workflow status information
    return json.dumps(
        list(workflows.values()), indent = 2
    )
    
    return json.dumps({"message": "TODO: Implement get_workflow_status"})


# ===== Module 2: MCP Prompts =====

@mcp.prompt()
async def analyze_ci_results():
    """Analyze recent CI/CD results and provide insights."""
    # TODO: Implement this prompt
     # Return a string with instructions for Claude to:
    # 1. Use get_recent_actions_events() 
    # 2. Use get_workflow_status()
    # 3. Analyze results and provide insights
    """Please analyze the recent CI/CD results from GitHub Actions.
    
    Use the following tools:
    1. First,get the recent CI/CD events using the get_recent_actions_events() tool.
    2. Then, use the get_workflow_status() tool to get current workflow statuses.
    3. Analyze the results and identify any failures and or issues that need attention.
    4. Based on the analysis, provide the steps neeeded to resolve any issues.
    
    Format your response as:
    ## CI/CD Status Report
    - **Overall Status**: [Good/Warning/Critical]
    - **Successful Workflows**: [List the recent successful workflows]
    - **Failed Workflows**: [List the failed workflows with links]
    - **Recommendations**: [Specific actions to take]
    - **Trends**: [Any patterns or trends observed]"""
   
    
    #return "TODO: Implement analyze_ci_results prompt"


@mcp.prompt()
async def create_deployment_summary():
    """Generate a deployment summary for team communication."""
    # TODO: Implement this prompt
    # Return a string that guides Claude to create a deployment summary
    return """Create a deployment summary for team communication:

1. Check the workflow status using the get_workflow_status() tool.
2. Look specifically for deployment-related workflows.
3. Note the deployment outcome, timimg, and any issues.

Format as a concise message suitable for Slack:

**Deployment Summary**
- **Status**: [Success/Failure/In Progress]
- **Environment**: [Production/Staging/Development]
- **Duration**: [Time if available]
- **Key Changes**: [Brief summary of changes if available]
- **Issues**: [Any issues encountered]
- **Next Steps**: [Required actions or follow-ups]

Summary should be clear, simple and informative for the team awareness."""
    
    
    return "TODO: Implement create_deployment_summary prompt"


@mcp.prompt()
async def generate_pr_status_report():
    """Generate a comprehensive PR status report including CI/CD results."""
    # TODO: Implement this prompt
    # Return a string that guides Claude to combine code changes with CI/CD status
    return """ Generate a comprehensive PR status report:
1. First, use the analyze_file_changes() tool to get identify what changes were made in the PR.
2. Next, use the get_workflow_status() tool to get the current status of the CI/CD workflows.
3. Then, use the suggest_template() tool to recommend the most appropriate PR template based on the changes.
4 Finally, summarize all the information into a report that includes:

## PR Status Report

### Code Changes
- **Files Modified**: [Count by file type - .py, .js, etc.]
- **Change Type**: [Feature/Bugfix/Refactor/Etc.]
- **Impact Assessment**: [High/Medium/Low with reasoning]
- **Key Changes**: [Bullet points of the main changes]

### CI/CD Status
- **All Checks**: [Passing/Failing/Running]
- **Test Results**: [Pass Rate, Failures if any]
- **Build Status**: [Success/Running/Failed with details]
- **Code Quality**: [Linting, coverage if available]

### Recommendations
- **PR Template**: [Suggested template based on changes]
- **Next Steps**: [What steps to take befor merging]
- **Reviewers**: [Suggested reviewers based on files changed]

### Risks & Considerations
- [Any deployment risks, potential issues, etc.]
- [Breaking changes]
- [Dependencies affected]"""
    
    return "TODO: Implement generate_pr_status_report prompt"


@mcp.prompt()
async def troubleshoot_workflow_failure():
    """Help troubleshoot a failing GitHub Actions workflow."""
    # TODO: Implement this prompt
    # Return a string that guides Claude through troubleshooting steps
    return """Help troubleshoot a failing GitHub Actions Workflow:

1. First, use the get_recent_actions_events() tool to find recent worflow event issues or failures.
2. Next, use the get_workflow_status() tool to identify failing workflows.
3. Then, analyze the failure patterns and timing.
4. Finally, provide systematic troubleshooting steps based on the findings.

Format your response as:

## Workflow Troubleshooting Guide

### Failed Worflow Details
- **Workflow Name**: [Name of the failing workflow]
- **Failure Type**: [Test/Build/Deployment/Linting]
- **Failure Occurrred At**: [When did the failing start]
- **Failure Rate**: [Intermittent or consistent]

### Diagnostic Information
- **Error Patterns**: [Common errors found in logs]
- **Recent Changes**: [What changes were made before the failure(s) occured]
- **Dependencies**: [External services or resources involved]

### Possible Causes (ordered by likelihood)
1. **[Most Likely]**: [Description and why]
2. **[Likely]**: [Description and why]
3. **[Possible]**: [Description and why]

### Suggested Fixes
**Immediate Actions:**
- [ ] [Wuick fix to try first]
- [ ] [Second quick fix]

**Incestigation Steps:**
- [ ] [How to gather more information]
- [ ] [Logs or data to check]

**Long-Term Solutions:**
- [ ] [Preventive measures to avoid future issues]
- [ ] [Similar issues or solutions]"""
    
    return "TODO: Implement troubleshoot_workflow_failure prompt"




if __name__ == "__main__":
    mcp.run(transport = "stdio")