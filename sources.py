from dataclasses import dataclass

import yaml


@dataclass
class Source:
    name: str
    type: str  # "rss" | "scrape"
    url: str
    enabled: bool = True


def load_sources(config_path: str = "config.yaml") -> list[Source]:
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    sources = [Source(**raw) for raw in config.get("sources", [])]
    return [s for s in sources if s.enabled]


def load_profile(config_path: str = "config.yaml") -> dict:
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config.get("profile", {})
