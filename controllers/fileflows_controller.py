import httpx

TIMEOUT = 15.0


class FileFlowsController:
    def __init__(self, url: str):
        self.base_url = url.rstrip("/")

    def get_status(self) -> dict:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(f"{self.base_url}/api/status")
            resp.raise_for_status()
            data = resp.json()
        return {
            "queue": data.get("queue", 0),
            "processing": data.get("processing", 0),
            "processed": data.get("processed", 0),
            "processing_files": data.get("processingFiles", []),
        }

    def get_savings(self) -> dict:
        """Return total bytes saved across all processed files."""
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(f"{self.base_url}/api/library-file", params={"status": 1})
            resp.raise_for_status()
            files = resp.json()

        if not isinstance(files, list):
            files = []

        total_original = 0
        total_final = 0
        for f in files:
            orig = f.get("OriginalSize") or f.get("originalSize") or 0
            final = f.get("FinalSize") or f.get("finalSize") or 0
            if orig and final and final > 0:
                total_original += orig
                total_final += final

        saved_bytes = max(0, total_original - total_final)
        saved_pct = round((saved_bytes / total_original) * 100, 1) if total_original > 0 else 0

        def to_gb(b):
            return round(b / (1024 ** 3), 2) if b else 0

        return {
            "original_gb": to_gb(total_original),
            "final_gb": to_gb(total_final),
            "saved_gb": to_gb(saved_bytes),
            "saved_pct": saved_pct,
            "file_count": len(files),
        }

    def get_nodes(self) -> list[dict]:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(f"{self.base_url}/api/node")
            resp.raise_for_status()
            nodes = resp.json()
        if not isinstance(nodes, list):
            nodes = [nodes] if nodes else []
        return [
            {
                "name": n.get("Name") or n.get("name", ""),
                "runners": n.get("FlowRunners") or n.get("flowRunners", 0),
                "version": n.get("Version") or n.get("version", ""),
            }
            for n in nodes
        ]
