---
name: identify-url-paths
description: "Use this skill to discover all URL paths/endpoints in the target repository using filesystem tools."
license: MIT
metadata:
  author: absoluteappsec
  version: "1.0"
---

# Identify URL Paths Skill

## Overview
This skill guides you in discovering all URL paths/endpoints in a code repository by using the filesystem tools provided by the FilesystemBackend (e.g., listing directories, reading files).

## Instructions

When using this skill, you should:

### 1. Discover Routing Files

Use filesystem tools to recursively explore the repository:

- List directories and files under the repo root.
- Identify likely routing files:
  - **Django:** `urls.py` files across the project
  - **Rails:** `config/routes.rb`
  - **Express:** `.js` files containing route definitions such as:
    - `app.get('/path', handler)`
    - `app.post('/path', handler)`
    - `router.get('/path', handler)`
    - `app.use('/prefix', router)`

### 2. Read and Analyze Routing Files

For each candidate routing file:

- Use filesystem tools to read the file contents.
- Extract:
  - **HTTP method** (if applicable): GET, POST, PUT, DELETE, PATCH, or ANY
  - **URL path or pattern**: e.g., `/users/<id>/`, `/api/data`
  - **Handler**:
    - Django: view function or class
    - Rails: `controller#action`
    - Express: handler function or router

### 3. Normalize Endpoints

Normalize the discovered endpoints into a consistent structure:

- **framework**: `django`, `rails`, or `express`
- **method**: HTTP verb or `ANY`
- **path**: URL path or pattern
- **handler**: view/controller/handler reference
- **source_file**: full path to the file where the route is defined

### 4. Be Systematic

- Ensure you cover all subdirectories, not just top-level files.
- For Express, pay attention to:
  - Mounted routers via `app.use('/prefix', router)`
  - Route definitions spread across multiple files.

## Output Format

Produce a structured inventory of endpoints, for example:

```json
[
  {
    "framework": "django",
    "method": "ANY",
    "path": "/users/<int:id>/",
    "handler": "views.user_detail",
    "source_file": "project/app/urls.py"
  },
  {
    "framework": "express",
    "method": "GET",
    "path": "/api/data",
    "handler": "getDataHandler",
    "source_file": "src/app.js"
  }
]
