import httpx
from controllers.base import BaseController

TIMEOUT = 30.0
SHORT_TIMEOUT = 15.0


class SystemController(BaseController):
    def __init__(self, url: str, api_key: str):
        super().__init__(url, api_key)

    def _gql_headers(self) -> dict:
        return {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

    async def _graphql(self, query: str, timeout: float = SHORT_TIMEOUT) -> dict:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, verify=False) as client:
            resp = await client.post(
                f"{self.base_url}/graphql",
                headers=self._gql_headers(),
                json={"query": query}
            )
            resp.raise_for_status()
            return resp.json()

    async def get_system_status(self) -> dict:
        query = """
        {
          info {
            os { uptime }
            cpu { brand cores }
            memory { layout { size } }
          }
          array {
            state
            capacity {
              kilobytes { free used total }
            }
          }
        }
        """
        data = await self._graphql(query)
        info = data.get("data", {}).get("info", {})
        array_data = data.get("data", {}).get("array", {})

        # Total installed RAM from memory layout
        layout = info.get("memory", {}).get("layout", [])
        ram_total_bytes = sum(slot.get("size", 0) for slot in layout)
        ram_total_gb = round(ram_total_bytes / (1024 ** 3), 1) if ram_total_bytes else 0

        array_state = array_data.get("state", "Unknown")
        capacity = array_data.get("capacity", {}).get("kilobytes", {})

        def kb_to_tb(kb):
            try:
                return round(int(kb) / (1024 ** 3), 2)
            except (TypeError, ValueError):
                return 0

        return {
            "cpu": info.get("cpu", {}).get("brand", ""),
            "cpu_cores": info.get("cpu", {}).get("cores", 0),
            "ram_total_gb": ram_total_gb,
            "array_state": array_state,
            "array_used_tb": kb_to_tb(capacity.get("used", 0)),
            "array_free_tb": kb_to_tb(capacity.get("free", 0)),
            "array_total_tb": kb_to_tb(capacity.get("total", 0)),
            "uptime_since": info.get("os", {}).get("uptime", "")
        }

    async def get_live_metrics(self) -> dict:
        query = "{ metrics { cpu { percentTotal } memory { total used percentTotal } } }"
        data = await self._graphql(query, timeout=10.0)
        metrics = data.get("data", {}).get("metrics", {})
        cpu = metrics.get("cpu", {})
        mem = metrics.get("memory", {})
        ram_total = mem.get("total", 0) or 0
        ram_used = mem.get("used", 0) or 0
        return {
            "cpu_pct": round(float(cpu.get("percentTotal", 0)), 1),
            "ram_pct": round(float(mem.get("percentTotal", 0)), 1),
            "ram_used_gb": round(ram_used / (1024 ** 3), 1) if ram_used else 0,
            "ram_total_gb": round(ram_total / (1024 ** 3), 1) if ram_total else 0,
        }

    async def get_notifications(self) -> list[dict]:
        query = """{ notifications { warningsAndAlerts {
            id title description importance timestamp
        } } }"""
        data = await self._graphql(query)
        alerts = data.get("data", {}).get("notifications", {}).get("warningsAndAlerts", [])
        return [
            {
                "id": a.get("id", ""),
                "title": a.get("title", ""),
                "description": a.get("description", ""),
                "importance": a.get("importance", "NOTICE"),
                "timestamp": a.get("timestamp", "")[:10] if a.get("timestamp") else "",
            }
            for a in alerts
        ]

    async def get_shares(self) -> list[dict]:
        # Note: Unraid GraphQL API returns size=0 for all shares (not calculated server-side).
        # Only free space on the underlying disk/pool is available.
        query = "{ shares { name free } }"
        data = await self._graphql(query)
        shares = data.get("data", {}).get("shares", [])
        result = []
        for s in shares:
            try:
                free = int(s.get("free") or 0)
            except (TypeError, ValueError):
                free = 0
            result.append({
                "name": s.get("name", ""),
                "free_gb": round(free / (1024 ** 3), 1) if free else 0,
            })
        return sorted(result, key=lambda x: x["name"].lower())

    async def get_parity_history(self) -> list[dict]:
        query = "{ parityHistory { date duration speed status } }"
        data = await self._graphql(query)
        history = data.get("data", {}).get("parityHistory", [])
        return [
            {
                "date": h.get("date", "")[:10] if h.get("date") else "",
                "duration": h.get("duration", ""),
                "speed": h.get("speed", ""),
                "status": h.get("status", ""),
            }
            for h in history[:10]
        ]

    async def reboot(self) -> bool:
        data = await self._graphql("mutation { reboot }", timeout=10.0)
        return data.get("data", {}).get("reboot", False)

    async def shutdown(self) -> bool:
        data = await self._graphql("mutation { shutdown }", timeout=10.0)
        return data.get("data", {}).get("shutdown", False)

    async def get_disk_health(self) -> list[dict]:
        query = """
        {
          disks {
            name
            size
            temperature
            smartStatus
          }
        }
        """
        data = await self._graphql(query, timeout=TIMEOUT)
        disks = data.get("data", {}).get("disks", [])

        result = []
        for disk in disks:
            size_bytes = disk.get("size", 0)
            size_tb = round(size_bytes / (1024 ** 4), 2) if size_bytes else 0
            result.append({
                "name": disk.get("name", ""),
                "size_tb": size_tb,
                "temperature": disk.get("temperature"),
                "smart_status": disk.get("smartStatus", "Unknown")
            })
        return result
