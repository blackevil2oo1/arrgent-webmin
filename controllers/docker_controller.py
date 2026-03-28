import docker
from docker.errors import DockerException, NotFound


class DockerController:
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            self._client = docker.from_env()
        return self._client

    def get_containers(self) -> list[dict]:
        client = self._get_client()
        containers = client.containers.list(all=True)
        result = []
        for c in containers:
            result.append({
                "name": c.name,
                "status": c.status,
                "image": c.image.tags[0] if c.image.tags else c.image.short_id,
                "running": c.status == "running"
            })
        # Sort: running first, then by name
        result.sort(key=lambda x: (0 if x["running"] else 1, x["name"].lower()))
        return result

    def start_container(self, name: str) -> dict:
        client = self._get_client()
        try:
            container = client.containers.get(name)
            container.start()
            return {"success": True, "message": f"Container '{name}' started"}
        except NotFound:
            raise ValueError(f"Container '{name}' not found")

    def stop_container(self, name: str) -> dict:
        client = self._get_client()
        try:
            container = client.containers.get(name)
            container.stop(timeout=10)
            return {"success": True, "message": f"Container '{name}' stopped"}
        except NotFound:
            raise ValueError(f"Container '{name}' not found")

    def restart_container(self, name: str) -> dict:
        client = self._get_client()
        try:
            container = client.containers.get(name)
            container.restart(timeout=10)
            return {"success": True, "message": f"Container '{name}' restarted"}
        except NotFound:
            raise ValueError(f"Container '{name}' not found")
