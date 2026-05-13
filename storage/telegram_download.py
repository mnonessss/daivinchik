import os

import aiohttp


async def download_telegram_photo(telegram_file_id: str) -> tuple[bytes, str, str]:
    """
    Download a file from Telegram Bot API by file_id.
    Returns (body_bytes, content_type, file_extension_without_dot).
    """
    token = os.getenv("TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TOKEN or TELEGRAM_BOT_TOKEN must be set for photo download")

    base = f"https://api.telegram.org/bot{token}"
    timeout = aiohttp.ClientTimeout(total=60)

    async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
        async with session.get(f"{base}/getFile", params={"file_id": telegram_file_id}) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"getFile failed: {resp.status} {text[:200]}")
            payload = await resp.json()
        if not payload.get("ok"):
            raise RuntimeError(f"getFile not ok: {payload}")
        result = payload["result"]
        file_path = result["file_path"]

        from storage.s3_storage import guess_content_type

        content_type = guess_content_type(file_path)
        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else "jpg"

        file_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
        async with session.get(file_url) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"download file failed: {resp.status} {text[:200]}")
            body = await resp.read()

    return body, content_type, ext
