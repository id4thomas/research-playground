from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import httpx


@dataclass
class Author:
    name: str
    user_id: Optional[str] = None
    username: Optional[str] = None
    fullname: Optional[str] = None
    is_pro: bool = False
    avatar_url: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Author":
        user = data.get("user") or {}
        return cls(
            name=data.get("name", ""),
            user_id=user.get("_id"),
            username=user.get("user"),
            fullname=user.get("fullname"),
            is_pro=user.get("isPro", False),
            avatar_url=user.get("avatarUrl"),
        )


@dataclass
class Paper:
    id: str
    title: str
    summary: str
    published_at: datetime
    upvotes: int
    authors: list[Author] = field(default_factory=list)
    ai_summary: Optional[str] = None
    ai_keywords: list[str] = field(default_factory=list)
    thumbnail: Optional[str] = None
    github_url: Optional[str] = None
    num_comments: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> "Paper":
        paper = data.get("paper") or data

        raw_date = paper.get("publishedAt") or data.get("publishedAt", "")
        try:
            published_at = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            published_at = datetime.min

        github_url = cls._extract_github_url(paper.get("summary", ""))

        return cls(
            id=paper.get("id", ""),
            title=paper.get("title", "").replace("\n", " ").strip(),
            summary=paper.get("summary", "").strip(),
            published_at=published_at,
            upvotes=paper.get("upvotes", 0),
            authors=[Author.from_dict(a) for a in paper.get("authors", [])],
            ai_summary=paper.get("ai_summary"),
            ai_keywords=paper.get("ai_keywords", []),
            thumbnail=data.get("thumbnail") or paper.get("thumbnail"),
            github_url=github_url,
            num_comments=data.get("numComments", 0),
        )

    @staticmethod
    def _extract_github_url(text: str) -> Optional[str]:
        match = re.search(r"https://github\.com/\S+", text)
        return match.group(0) if match else None

    def __repr__(self) -> str:
        return (
            f"Paper(id={self.id!r}, title={self.title[:50]!r}, "
            f"upvotes={self.upvotes}, authors={len(self.authors)})"
        )


class HuggingfacePapersClient:
    BASE_URL = "https://huggingface.co/api/papers"

    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )

    async def _get(self, path: str, params: Optional[dict] = None) -> dict | list:
        response = await self._client.get(f"/{path}", params=params)
        response.raise_for_status()
        return response.json()
    
    async def search(self, query: str, limit: Optional[int] = None) -> list[Paper]:
        """Search papers by keyword. Returns up to *limit* results."""
        data = await self._get("search", params={"q": query})
        papers = [Paper.from_dict(item) for item in data]
        return papers[:limit] if limit else papers

    async def get_paper(self, paper_id: str) -> Paper:
        """Fetch a single paper by its arXiv-style ID (e.g. '2408.04187')."""
        data = await self._get(paper_id)
        return Paper.from_dict(data)

    async def get_papers(self, paper_ids: list[str]) -> list[Paper]:
        """Fetch multiple papers concurrently."""
        return await asyncio.gather(*[self.get_paper(pid) for pid in paper_ids])
