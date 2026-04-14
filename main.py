"""Pixiv MCP Server - Supports illustration search, trending, download, and AI-generated content filtering"""

import os
import pathlib
import time

from dotenv import load_dotenv

load_dotenv()

from mcp.server.fastmcp import FastMCP
from pixivpy3 import AppPixivAPI

mcp = FastMCP(
    "pixiv-artwork",
    host=os.environ.get("MCP_HOST", "127.0.0.1"),
    port=int(os.environ.get("MCP_PORT", "8000")),
)

# --- Pixiv API client ---

_api: AppPixivAPI | None = None


def _get_api() -> AppPixivAPI:
    global _api
    if _api is None:
        token = os.environ.get("PIXIV_REFRESH_TOKEN", "")
        if not token:
            raise RuntimeError(
                "PIXIV_REFRESH_TOKEN is not set. "
                "Please obtain it via gppt or the PKCE OAuth flow."
            )
        _api = AppPixivAPI()
        _api.auth(refresh_token=token)
    return _api


def _download_dir() -> pathlib.Path:
    d = pathlib.Path(os.environ.get("PIXIV_DOWNLOAD_DIR", "./downloads"))
    d.mkdir(parents=True, exist_ok=True)
    return d


# --- helpers ---

AI_TYPE_LABEL = {0: "unset", 1: "non-AI", 2: "AI-generated"}

AI_TAG_KEYWORDS = {"AI-generated", "AI生成", "AIイラスト", "AI", "NovelAI", "StableDiffusion", "Midjourney", "nijijourney"}


def _has_ai_tag(illust: dict) -> bool:
    """Check whether the tags contain any AI-related keyword"""
    tags = {t.get("name", "") for t in illust.get("tags", [])}
    return bool(tags & AI_TAG_KEYWORDS)


def _format_illust(illust: dict) -> dict:
    """Format and return illustration information"""
    ai_type = illust.get("illust_ai_type", 0)
    tags = [t.get("name", "") for t in illust.get("tags", [])]
    return {
        "id": illust["id"],
        "title": illust["title"],
        "author": illust.get("user", {}).get("name", "unknown"),
        "author_id": illust.get("user", {}).get("id"),
        "caption": (illust.get("caption") or "")[:200],
        "tags": tags,
        "create_date": illust.get("create_date", ""),
        "page_count": illust.get("page_count", 1),
        "width": illust.get("width"),
        "height": illust.get("height"),
        "total_view": illust.get("total_view", 0),
        "total_bookmarks": illust.get("total_bookmarks", 0),
        "ai_type": AI_TYPE_LABEL.get(ai_type, f"unknown({ai_type})"),
        "has_ai_tag": _has_ai_tag(illust),
        "is_ai_generated": ai_type >= 2 or _has_ai_tag(illust),
        "r18": any(t.get("name", "") in ("R-18", "R-18G") for t in illust.get("tags", [])),
        "image_urls": {
            "square_medium": illust.get("image_urls", {}).get("square_medium", ""),
            "medium": illust.get("image_urls", {}).get("medium", ""),
            "large": illust.get("image_urls", {}).get("large", ""),
            "original": (
                illust.get("meta_single_page", {}).get("original_image_url", "")
                or (
                    illust.get("meta_pages", [{}])[0]
                    .get("image_urls", {})
                    .get("original", "")
                    if illust.get("meta_pages")
                    else ""
                )
            ),
        },
    }


def _filter_illusts(
    illusts: list[dict],
    *,
    exclude_ai: bool = False,
    only_ai: bool = False,
    allow_r18: bool = False,
) -> list[dict]:
    """Apply AI-generated and R18 filters"""
    result = []
    for illust in illusts:
        ai_type = illust.get("illust_ai_type", 0)
        is_r18 = any(
            t.get("name", "") in ("R-18", "R-18G") for t in illust.get("tags", [])
        )

        has_ai = ai_type >= 2 or _has_ai_tag(illust)
        if exclude_ai and has_ai:
            continue
        if only_ai and not has_ai:
            continue
        if not allow_r18 and is_r18:
            continue

        result.append(illust)
    return result


MAX_RESULTS = 100
PAGE_SLEEP_SEC = 1.5


def _collect_illusts_with_pagination(
    first_result: dict,
    api: AppPixivAPI,
    *,
    exclude_ai: bool = False,
    only_ai: bool = False,
    allow_r18: bool = False,
    limit: int = MAX_RESULTS,
) -> tuple[list[dict], int]:
    """Collect illustrations from the initial result via pagination.

    Returns:
        (list of filtered illustrations (up to `limit` items), total number of filtered items)
    """
    limit = min(limit, MAX_RESULTS)
    all_illusts: list[dict] = []
    total_filtered = 0
    result = first_result

    while True:
        illusts = result.get("illusts", [])
        if not illusts:
            break

        filtered = _filter_illusts(
            illusts, exclude_ai=exclude_ai, only_ai=only_ai, allow_r18=allow_r18
        )
        total_filtered += len(filtered)

        remaining = limit - len(all_illusts)
        all_illusts.extend(filtered[:remaining])

        if len(all_illusts) >= limit:
            break

        next_url = result.get("next_url")
        if not next_url:
            break

        next_qs = api.parse_qs(next_url)
        if not next_qs:
            break

        time.sleep(PAGE_SLEEP_SEC)
        result = api.search_illust(**next_qs)

    return all_illusts, total_filtered


# --- MCP Tools ---


@mcp.tool()
def search_illusts(
    word: str,
    search_target: str = "partial_match_for_tags",
    sort: str = "date_desc",
    duration: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    exclude_ai: bool = False,
    only_ai: bool = False,
    allow_r18: bool = False,
    limit: int = 30,
) -> dict:
    """Search for illustrations on Pixiv by keyword or tag.

    Args:
        word: Search keyword or tag
        search_target: Search mode - "partial_match_for_tags" (partial tag match),
            "exact_match_for_tags" (exact tag match), "title_and_caption" (title/caption)
        sort: Sort order - "date_desc" (newest first), "date_asc" (oldest first), "popular_desc" (by popularity, Premium only)
        duration: Period - "within_last_day", "within_last_week", "within_last_month" (optional)
        start_date: Start date YYYY-MM-DD (optional)
        end_date: End date YYYY-MM-DD (optional)
        exclude_ai: If True, exclude AI-generated works
        only_ai: If True, show only AI-generated works
        allow_r18: If True, include R-18 works (excluded by default)
        limit: Number of results to fetch (max 100)
    """
    api = _get_api()
    limit = min(limit, MAX_RESULTS)

    kwargs: dict = {
        "word": word,
        "search_target": search_target,
        "sort": sort,
        "filter": "" if allow_r18 else "for_ios",
    }
    if duration:
        kwargs["duration"] = duration
    if start_date:
        kwargs["start_date"] = start_date
    if end_date:
        kwargs["end_date"] = end_date

    first_result = api.search_illust(**kwargs)
    illusts, total_filtered = _collect_illusts_with_pagination(
        first_result,
        api,
        exclude_ai=exclude_ai,
        only_ai=only_ai,
        allow_r18=allow_r18,
        limit=limit,
    )

    resp: dict = {
        "count": len(illusts),
        "query": word,
        "illusts": [_format_illust(i) for i in illusts],
    }
    if total_filtered > limit:
        resp["note"] = f"There are {total_filtered}+ matching works, but results are limited to {limit}."

    return resp


@mcp.tool()
def search_by_hashtag(
    tag: str,
    sort: str = "date_desc",
    exclude_ai: bool = False,
    only_ai: bool = False,
    allow_r18: bool = False,
    limit: int = 30,
) -> dict:
    """Search for illustrations by exact hashtag match.

    Args:
        tag: Hashtag to search for (without '#'. e.g., "初音ミク", "原神")
        sort: Sort order - "date_desc" (newest first), "date_asc" (oldest first), "popular_desc" (by popularity)
        exclude_ai: If True, exclude AI-generated works
        only_ai: If True, show only AI-generated works
        allow_r18: If True, include R-18 works
        limit: Number of results to fetch (max 100)
    """
    api = _get_api()
    limit = min(limit, MAX_RESULTS)

    first_result = api.search_illust(
        word=tag,
        search_target="exact_match_for_tags",
        sort=sort,
        filter="" if allow_r18 else "for_ios",
    )
    illusts, total_filtered = _collect_illusts_with_pagination(
        first_result,
        api,
        exclude_ai=exclude_ai,
        only_ai=only_ai,
        allow_r18=allow_r18,
        limit=limit,
    )

    resp: dict = {
        "count": len(illusts),
        "tag": tag,
        "illusts": [_format_illust(i) for i in illusts],
    }
    if total_filtered > limit:
        resp["note"] = f"There are {total_filtered}+ matching works, but results are limited to {limit}."

    return resp


@mcp.tool()
def get_trending(
    mode: str = "day",
    date: str | None = None,
    exclude_ai: bool = False,
    only_ai: bool = False,
    allow_r18: bool = False,
    limit: int = 30,
) -> dict:
    """Get the Pixiv ranking (trending).

    Args:
        mode: Ranking mode
              Normal: "day", "week", "month", "day_male", "day_female", "week_original", "week_rookie"
              R18: "day_r18", "day_male_r18", "day_female_r18", "week_r18", "week_r18g"
        date: Date YYYY-MM-DD (optional; defaults to latest if omitted)
        exclude_ai: If True, exclude AI-generated works
        only_ai: If True, show only AI-generated works
        allow_r18: If True, include R-18 works (automatically enabled when mode is an R18 variant)
        limit: Number of results to fetch (max 50)
    """
    api = _get_api()
    limit = min(limit, 50)

    if "r18" in mode:
        allow_r18 = True

    kwargs: dict = {"mode": mode, "filter": "" if allow_r18 else "for_ios"}
    if date:
        kwargs["date"] = date

    result = api.illust_ranking(**kwargs)
    illusts = result.get("illusts", [])
    illusts = _filter_illusts(
        illusts, exclude_ai=exclude_ai, only_ai=only_ai, allow_r18=allow_r18
    )[:limit]

    return {
        "count": len(illusts),
        "mode": mode,
        "date": date or "latest",
        "illusts": [_format_illust(i) for i in illusts],
    }


@mcp.tool()
def get_trending_tags() -> dict:
    """Get the list of currently trending tags on Pixiv."""
    api = _get_api()
    result = api.trending_tags_illust()
    tags = result.get("trend_tags", [])

    return {
        "count": len(tags),
        "tags": [
            {
                "tag": t.get("tag", ""),
                "translated_name": t.get("translated_name", ""),
                "illust": _format_illust(t["illust"]) if t.get("illust") else None,
            }
            for t in tags
        ],
    }


@mcp.tool()
def get_user_illusts(
    user_id: int,
    illust_type: str = "illust",
    exclude_ai: bool = False,
    only_ai: bool = False,
    allow_r18: bool = False,
    limit: int = 30,
) -> dict:
    """Get the list of illustrations for a specific user.

    Args:
        user_id: Pixiv user ID
        illust_type: Work type - "illust" (illustration), "manga" (manga)
        exclude_ai: If True, exclude AI-generated works
        only_ai: If True, show only AI-generated works
        allow_r18: If True, include R-18 works
        limit: Number of results to fetch (max 50)
    """
    api = _get_api()
    limit = min(limit, 50)

    result = api.user_illusts(user_id, type=illust_type, filter="" if allow_r18 else "for_ios")
    illusts = result.get("illusts", [])
    illusts = _filter_illusts(
        illusts, exclude_ai=exclude_ai, only_ai=only_ai, allow_r18=allow_r18
    )[:limit]

    user_info = illusts[0].get("user", {}) if illusts else {}

    return {
        "count": len(illusts),
        "user_id": user_id,
        "user_name": user_info.get("name", "unknown"),
        "illusts": [_format_illust(i) for i in illusts],
    }


@mcp.tool()
def get_illust_detail(illust_id: int) -> dict:
    """Get detailed information for an illustration.

    Args:
        illust_id: Illustration ID
    """
    api = _get_api()
    result = api.illust_detail(illust_id)
    illust = result.get("illust")
    if not illust:
        return {"error": f"Illustration {illust_id} not found"}

    detail = _format_illust(illust)
    detail["caption_full"] = illust.get("caption", "")
    detail["tools"] = illust.get("tools", [])
    detail["series"] = illust.get("series")

    if illust.get("meta_pages"):
        detail["all_pages"] = [
            {
                "page": idx,
                "original": p.get("image_urls", {}).get("original", ""),
                "large": p.get("image_urls", {}).get("large", ""),
            }
            for idx, p in enumerate(illust["meta_pages"])
        ]

    return detail


@mcp.tool()
def search_users(
    word: str,
    limit: int = 10,
) -> dict:
    """Search for Pixiv users (authors).

    Args:
        word: Search keyword (e.g., user name)
        limit: Number of results to fetch (max 30)
    """
    api = _get_api()
    limit = min(limit, 30)

    result = api.search_user(word)
    previews = result.get("user_previews", [])[:limit]

    users = []
    for p in previews:
        user = p.get("user", {})
        users.append(
            {
                "id": user.get("id"),
                "name": user.get("name", ""),
                "account": user.get("account", ""),
                "profile_image": user.get("profile_image_urls", {}).get("medium", ""),
                "is_followed": user.get("is_followed", False),
                "sample_illusts": [
                    _format_illust(i) for i in (p.get("illusts") or [])[:3]
                ],
            }
        )

    return {"count": len(users), "query": word, "users": users}


@mcp.tool()
def get_recommended(
    exclude_ai: bool = False,
    only_ai: bool = False,
    allow_r18: bool = False,
    limit: int = 30,
) -> dict:
    """Get recommended illustrations (recommendations based on the authenticated user).

    Args:
        exclude_ai: If True, exclude AI-generated works
        only_ai: If True, show only AI-generated works
        allow_r18: If True, include R-18 works
        limit: Number of results to fetch (max 50)
    """
    api = _get_api()
    limit = min(limit, 50)

    result = api.illust_recommended(filter="" if allow_r18 else "for_ios")
    illusts = result.get("illusts", [])
    illusts = _filter_illusts(
        illusts, exclude_ai=exclude_ai, only_ai=only_ai, allow_r18=allow_r18
    )[:limit]

    return {
        "count": len(illusts),
        "illusts": [_format_illust(i) for i in illusts],
    }


@mcp.tool()
def download_illust(
    illust_id: int,
    page: int = 0,
    size: str = "original",
) -> dict:
    """Download an illustration.

    Args:
        illust_id: Illustration ID
        page: Page number (for multi-page works; 0-based)
        size: Size - "original", "large", "medium"
    """
    api = _get_api()
    result = api.illust_detail(illust_id)
    illust = result.get("illust")
    if not illust:
        return {"error": f"Illustration {illust_id} not found"}

    url = ""
    if illust.get("meta_pages") and page < len(illust["meta_pages"]):
        urls = illust["meta_pages"][page].get("image_urls", {})
        url = urls.get(size, urls.get("original", ""))
    elif page == 0:
        if size == "original":
            url = illust.get("meta_single_page", {}).get("original_image_url", "")
        if not url:
            url = illust.get("image_urls", {}).get(size, "")

    if not url:
        return {"error": f"Could not retrieve image URL (page={page}, size={size})"}

    save_dir = _download_dir()
    fname = url.split("/")[-1]
    save_path = save_dir / fname

    api.download(url, path=str(save_dir), fname=fname)

    return {
        "success": True,
        "illust_id": illust_id,
        "title": illust.get("title", ""),
        "author": illust.get("user", {}).get("name", ""),
        "page": page,
        "size": size,
        "file_path": str(save_path),
        "file_name": fname,
    }


@mcp.tool()
def batch_download(
    illust_ids: list[int],
    size: str = "original",
    all_pages: bool = False,
) -> dict:
    """Download multiple illustrations in bulk.

    Args:
        illust_ids: List of illustration IDs to download
        size: Size - "original", "large", "medium"
        all_pages: If True, download all pages of multi-page works
    """
    api = _get_api()
    save_dir = _download_dir()
    results = []

    for illust_id in illust_ids:
        try:
            detail = api.illust_detail(illust_id)
            illust = detail.get("illust")
            if not illust:
                results.append({"illust_id": illust_id, "success": False, "error": "not found"})
                continue

            pages_to_dl = []
            if illust.get("meta_pages") and all_pages:
                for idx, p in enumerate(illust["meta_pages"]):
                    urls = p.get("image_urls", {})
                    url = urls.get(size, urls.get("original", ""))
                    if url:
                        pages_to_dl.append((idx, url))
            else:
                url = ""
                if size == "original":
                    url = illust.get("meta_single_page", {}).get("original_image_url", "")
                if not url:
                    if illust.get("meta_pages"):
                        url = (
                            illust["meta_pages"][0]
                            .get("image_urls", {})
                            .get(size, "")
                        )
                    else:
                        url = illust.get("image_urls", {}).get(size, "")
                if url:
                    pages_to_dl.append((0, url))

            downloaded = []
            for page_idx, dl_url in pages_to_dl:
                fname = dl_url.split("/")[-1]
                api.download(dl_url, path=str(save_dir), fname=fname)
                downloaded.append({"page": page_idx, "file": fname})

            results.append(
                {
                    "illust_id": illust_id,
                    "title": illust.get("title", ""),
                    "author": illust.get("user", {}).get("name", ""),
                    "success": True,
                    "files": downloaded,
                }
            )
        except Exception as e:
            results.append({"illust_id": illust_id, "success": False, "error": str(e)})

    return {
        "download_dir": str(save_dir),
        "total": len(results),
        "succeeded": sum(1 for r in results if r.get("success")),
        "results": results,
    }


if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    mcp.run(transport=transport)
