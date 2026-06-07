from __future__ import annotations
import os


class FileOps:
    """
    File system operations.
    Optimized to safeguard the background runtime thread against heavy directory traversal.
    """

    def read(self, path: str) -> dict:
        """Read a file safely up to a maximum size limit."""
        path = os.path.expanduser(path)
        try:
            if not os.path.exists(path):
                return {"success": False, "error": "File does not exist.", "path": path}
                
   
            file_size = os.path.getsize(path)
            if file_size > 5 * 1024 * 1024:
                return {"success": False, "error": "File size exceeds local 5MB processing safe limit.", "path": path}

            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return {
                "success": True,
                "path": path,
                "content": content,
                "size": len(content),
            }
        except Exception as e:
            return {"success": False, "error": str(e), "path": path}

    def write(self, path: str, content: str) -> dict:
        """Write content safely to a local file path."""
        path = os.path.expanduser(path)
        try:
            target_dir = os.path.dirname(os.path.abspath(path))
            if target_dir:
                os.makedirs(target_dir, exist_ok=True)
                
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return {"success": True, "path": path, "bytes_written": len(content)}
        except Exception as e:
            return {"success": False, "error": str(e), "path": path}

    def list_dir(self, path: str) -> dict:
        """List directory contents with explicit safe boundaries for item scaling."""
        path = os.path.expanduser(path)
        try:
            if not os.path.isdir(path):
                return {"success": False, "error": "Target path is not a valid directory.", "path": path}

            entries = []
            count = 0
            for entry in os.scandir(path):
                if count >= 150:  
                    break
                try:
                    is_directory = entry.is_dir()
                    entries.append({
                        "name": entry.name,
                        "type": "dir" if is_directory else "file",
                        "size": entry.stat().st_size if not is_directory else None,
                    })
                    count += 1
                except (PermissionError, FileNotFoundError):
                    continue  

            entries.sort(key=lambda x: (x["type"] == "file", x["name"]))
            return {
                "success": True, 
                "path": path, 
                "entries": entries,
                "truncated": count >= 150
            }
        except Exception as e:
            return {"success": False, "error": str(e), "path": path}
