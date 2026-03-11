import re
from fastapi import FastAPI
from pydantic import BaseModel
from playwright.async_api import async_playwright

app = FastAPI(title="Playwright Browser Service")


class BrowseRequest(BaseModel):
    url: str
    extract: str = "markdown"


def html_to_markdown(html: str) -> str:
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<nav[^>]*>.*?</nav>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<footer[^>]*>.*?</footer>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<h([1-6])[^>]*>(.*?)</h\1>", lambda m: "#" * int(m.group(1)) + " " + m.group(2) + "\n", html, flags=re.DOTALL)
    html = re.sub(r"<a[^>]*href=['\"]([^'\"]+)['\"][^>]*>(.*?)</a>", r"[\2](\1)", html, flags=re.DOTALL)
    html = re.sub(r"<(strong|b)[^>]*>(.*?)</\1>", r"**\2**", html, flags=re.DOTALL)
    html = re.sub(r"<(em|i)[^>]*>(.*?)</\1>", r"*\2*", html, flags=re.DOTALL)
    html = re.sub(r"<li[^>]*>(.*?)</li>", r"- \1\n", html, flags=re.DOTALL)
    html = re.sub(r"<p[^>]*>(.*?)</p>", r"\1\n\n", html, flags=re.DOTALL)
    html = re.sub(r"<br\s*/?>", "\n", html)
    html = re.sub(r"<[^>]+>", "", html)
    html = re.sub(r"&nbsp;", " ", html)
    html = re.sub(r"&amp;", "&", html)
    html = re.sub(r"&lt;", "<", html)
    html = re.sub(r"&gt;", ">", html)
    html = re.sub(r"&quot;", '"', html)
    html = re.sub(r"\n{3,}", "\n\n", html)
    return html.strip()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/browse")
async def browse(req: BrowseRequest):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = await browser.new_page()
        try:
            await page.goto(req.url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(1500)

            if req.extract == "links":
                links = await page.eval_on_selector_all("a[href]", "els => els.map(e => ({text: e.innerText.trim(), href: e.href}))")
                content = "\n".join(f"[{l['text']}]({l['href']})" for l in links if l["text"] and l["href"])
            elif req.extract == "text":
                content = await page.inner_text("body")
                content = re.sub(r"\n{3,}", "\n\n", content).strip()
            else:
                html = await page.content()
                content = html_to_markdown(html)

            return {"url": req.url, "content": content[:8000]}
        except Exception as e:
            return {"url": req.url, "content": f"Error: {e}", "error": True}
        finally:
            await browser.close()


@app.post("/screenshot")
async def screenshot(req: BrowseRequest):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        try:
            await page.goto(req.url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(1500)
            img_bytes = await page.screenshot(type="png", full_page=False)
            import base64
            return {"url": req.url, "image_base64": base64.b64encode(img_bytes).decode()}
        except Exception as e:
            return {"url": req.url, "error": str(e)}
        finally:
            await browser.close()
