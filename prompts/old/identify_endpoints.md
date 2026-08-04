# Explore the codebase and identify all url paths
Use the 'identify-url-paths' skill whenever you need a routing inventory.

```json
[
  {
    "framework": "django | rails | express",
    "method": "GET | POST | PUT | DELETE | ...",
    "path": "/example/path",
    "handler": "controller#action | view function | express handler",
    "source_file": "path/to/file"
  }
]
```