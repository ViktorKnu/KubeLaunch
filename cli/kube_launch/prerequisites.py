"""Checks for command-line tools required by KubeLaunch."""

from dataclasses import dataclass
from shutil import which

REQUIRED_TOOLS = ("kubectl", "k3d", "helm")


@dataclass(frozen=True)
class ToolStatus:
    """Availability information for a required executable."""

    name: str
    path: str | None

    @property
    def available(self) -> bool:
        return self.path is not None


def check_tools(tool_names: tuple[str, ...] = REQUIRED_TOOLS) -> list[ToolStatus]:
    """Return the current PATH status for each requested tool."""
    return [ToolStatus(name=name, path=which(name)) for name in tool_names]
