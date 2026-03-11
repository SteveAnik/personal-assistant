import asyncio
import os
import json
import tempfile
import httpx
from pathlib import Path
from typing import Any

RESEARCH_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "youtube_research",
        "description": "Research YouTube video topics: find trending topics, analyze competitors, generate video ideas for a given genre/niche",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["trending_topics", "search_videos", "channel_analysis", "generate_ideas", "keyword_research"],
                    "description": "Research action to perform",
                },
                "genre": {"type": "string", "description": "Video genre or niche (e.g. 'homelab', 'tech tutorials', 'linux')"},
                "query": {"type": "string", "description": "Search query or topic"},
                "channel_id": {"type": "string", "description": "YouTube channel ID for analysis"},
                "max_results": {"type": "integer", "description": "Max results to return (default 10)", "default": 10},
            },
            "required": ["action"],
        },
    },
}

SCRIPT_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "youtube_write_script",
        "description": "Write a full YouTube video script with hook, sections, and call-to-action based on a topic and outline",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Video topic"},
                "genre": {"type": "string", "description": "Video genre/niche"},
                "duration_minutes": {"type": "integer", "description": "Target video duration in minutes (default 8)", "default": 8},
                "style": {"type": "string", "description": "Narration style (e.g. 'educational', 'entertaining', 'tutorial')", "default": "educational"},
                "extra_context": {"type": "string", "description": "Additional context, notes, or requirements for the script"},
            },
            "required": ["topic"],
        },
    },
}

VIDEO_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "youtube_create_video",
        "description": "Create a YouTube video: generates images for each section, adds TTS narration, assembles into a slideshow MP4 video",
        "parameters": {
            "type": "object",
            "properties": {
                "script": {"type": "string", "description": "Full video script with section markers"},
                "title": {"type": "string", "description": "Video title"},
                "voice": {"type": "string", "description": "TTS voice to use (default: 'en-US-AriaNeural')", "default": "en-US-AriaNeural"},
                "use_ai_video": {"type": "boolean", "description": "Use AI video generation (Runway ML) instead of slideshow", "default": False},
                "output_dir": {"type": "string", "description": "Output directory for video files", "default": "/app/videos"},
            },
            "required": ["script", "title"],
        },
    },
}

UPLOAD_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "youtube_upload",
        "description": "Upload a video to YouTube with title, description, tags, thumbnail, and category",
        "parameters": {
            "type": "object",
            "properties": {
                "video_path": {"type": "string", "description": "Path to the video file"},
                "title": {"type": "string", "description": "Video title"},
                "description": {"type": "string", "description": "Video description"},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Video tags"},
                "category_id": {"type": "string", "description": "YouTube category ID (28=Science&Tech, 22=People&Blogs, 27=Education)", "default": "28"},
                "privacy": {"type": "string", "enum": ["public", "unlisted", "private"], "default": "private"},
                "thumbnail_path": {"type": "string", "description": "Path to thumbnail image (optional)"},
            },
            "required": ["video_path", "title", "description"],
        },
    },
}

THUMBNAIL_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "youtube_generate_thumbnail",
        "description": "Generate a YouTube thumbnail image using Stability AI or DALL-E",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Video title to base the thumbnail on"},
                "prompt": {"type": "string", "description": "Image generation prompt for the thumbnail"},
                "output_path": {"type": "string", "description": "Where to save the thumbnail"},
                "provider": {"type": "string", "enum": ["stability", "dalle"], "default": "stability"},
            },
            "required": ["title"],
        },
    },
}


async def youtube_research(config: dict, action: str, genre: str = "", query: str = "", channel_id: str = "", max_results: int = 10) -> dict:
    yt_key = config.get("api_key", "")
    base = "https://www.googleapis.com/youtube/v3"

    if action == "generate_ideas":
        return {
            "ideas": [
                f"Top 10 {genre} tips for beginners",
                f"Why {query or genre} is changing in 2026",
                f"Complete {genre} guide: from zero to hero",
                f"I tested {query or genre} for 30 days — here's what happened",
                f"The biggest mistakes people make with {genre}",
                f"Best {genre} tools and setups in 2026",
                f"How I automated my {genre} workflow",
            ],
            "note": "Use youtube_research with action=trending_topics for real YouTube data",
        }

    if not yt_key:
        return {"error": "YouTube API key not configured. Add it in admin panel under Content/YouTube."}

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            if action == "trending_topics":
                r = await client.get(f"{base}/videos", params={
                    "part": "snippet,statistics",
                    "chart": "mostPopular",
                    "regionCode": "US",
                    "videoCategoryId": "28",
                    "maxResults": max_results,
                    "key": yt_key,
                })
                items = r.json().get("items", [])
                return {"trending": [{"title": i["snippet"]["title"], "views": i["statistics"].get("viewCount"), "channel": i["snippet"]["channelTitle"]} for i in items]}

            elif action == "search_videos":
                r = await client.get(f"{base}/search", params={
                    "part": "snippet",
                    "q": query or genre,
                    "type": "video",
                    "maxResults": max_results,
                    "order": "viewCount",
                    "key": yt_key,
                })
                items = r.json().get("items", [])
                return {"results": [{"title": i["snippet"]["title"], "channel": i["snippet"]["channelTitle"], "video_id": i["id"]["videoId"], "description": i["snippet"]["description"][:150]} for i in items]}

            elif action == "keyword_research":
                r = await client.get(f"{base}/search", params={
                    "part": "snippet",
                    "q": query or genre,
                    "type": "video",
                    "maxResults": 50,
                    "key": yt_key,
                })
                items = r.json().get("items", [])
                titles = [i["snippet"]["title"] for i in items]
                words: dict = {}
                for t in titles:
                    for w in t.lower().split():
                        if len(w) > 4:
                            words[w] = words.get(w, 0) + 1
                sorted_kw = sorted(words.items(), key=lambda x: x[1], reverse=True)[:20]
                return {"keywords": [{"word": k, "frequency": v} for k, v in sorted_kw]}

            else:
                return {"error": f"Action '{action}' requires additional setup"}

        except Exception as e:
            return {"error": str(e)}


async def youtube_write_script(llm_provider, topic: str, genre: str = "", duration_minutes: int = 8, style: str = "educational", extra_context: str = "") -> dict:
    words_per_minute = 130
    target_words = duration_minutes * words_per_minute

    prompt = f"""Write a complete YouTube video script for the following:

Topic: {topic}
Genre/Niche: {genre or 'general'}
Style: {style}
Target Duration: {duration_minutes} minutes (~{target_words} words)
{f'Additional context: {extra_context}' if extra_context else ''}

Structure the script with these clearly marked sections:
[HOOK] - Opening 30 seconds to grab attention
[INTRO] - Brief intro and what viewers will learn
[SECTION_1] - First main point with heading
[SECTION_2] - Second main point with heading
[SECTION_3] - Third main point with heading
(add more sections as needed)
[CONCLUSION] - Summary of key points
[CTA] - Call to action (like, subscribe, comment prompt)

Write natural spoken narration. Include pauses with (pause) where appropriate.
Also provide at the end:
TITLE_SUGGESTIONS: 3 catchy title options
DESCRIPTION: YouTube description (2-3 paragraphs)
TAGS: 15 relevant tags
"""
    from providers import get_provider
    provider = llm_provider or get_provider()
    from providers.base import Message
    response = await provider.chat([Message(role="user", content=prompt)], temperature=0.7)
    return {"script": response.content, "topic": topic, "estimated_duration": duration_minutes}


async def youtube_create_video(config: dict, script: str, title: str, voice: str = "en-US-AriaNeural", use_ai_video: bool = False, output_dir: str = "/app/videos") -> dict:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)[:50]

    if use_ai_video:
        runway_key = config.get("runway_api_key", "")
        if not runway_key:
            return {"error": "Runway ML API key not configured. Add it in admin panel under Content/YouTube."}
        return {"status": "pending", "note": "AI video generation via Runway ML — submit script sections as separate shots to the Runway API and poll for completion."}

    try:
        import edge_tts
        import moviepy.editor as mp
        from PIL import Image, ImageDraw, ImageFont
        import textwrap

        sections = []
        current_section = ""
        current_text = []
        for line in script.split("\n"):
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                if current_section and current_text:
                    sections.append({"section": current_section, "text": " ".join(current_text)})
                current_section = stripped[1:-1]
                current_text = []
            elif stripped:
                current_text.append(stripped)
        if current_section and current_text:
            sections.append({"section": current_section, "text": " ".join(current_text)})

        if not sections:
            sections = [{"section": "FULL", "text": script}]

        clips = []
        stability_key = config.get("stability_api_key", "")

        for i, section in enumerate(sections):
            text = section["text"]
            if not text.strip():
                continue

            audio_file = str(output_path / f"audio_{i}.mp3")
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(audio_file)

            audio_clip = mp.AudioFileClip(audio_file)
            duration = audio_clip.duration

            if stability_key:
                img_prompt = f"Professional YouTube thumbnail style image for: {section['section']} - {text[:100]}, cinematic, high quality"
                try:
                    async with httpx.AsyncClient(timeout=30) as client:
                        r = await client.post(
                            "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                            headers={"Authorization": f"Bearer {stability_key}", "Accept": "application/json"},
                            json={"text_prompts": [{"text": img_prompt}], "cfg_scale": 7, "height": 576, "width": 1024, "steps": 30, "samples": 1},
                        )
                        if r.status_code == 200:
                            import base64
                            img_data = r.json()["artifacts"][0]["base64"]
                            img_bytes = base64.b64decode(img_data)
                            img_file = str(output_path / f"img_{i}.png")
                            with open(img_file, "wb") as f:
                                f.write(img_bytes)
                            img_clip = mp.ImageClip(img_file).set_duration(duration)
                        else:
                            img_clip = _make_text_slide(text, section["section"], duration, output_path, i)
                except Exception:
                    img_clip = _make_text_slide(text, section["section"], duration, output_path, i)
            else:
                img_clip = _make_text_slide(text, section["section"], duration, output_path, i)

            video_clip = img_clip.set_audio(audio_clip)
            clips.append(video_clip)

        if not clips:
            return {"error": "No content sections found in script"}

        final_video = mp.concatenate_videoclips(clips, method="compose")
        output_file = str(output_path / f"{safe_title}.mp4")
        final_video.write_videofile(output_file, fps=24, codec="libx264", audio_codec="aac", logger=None)

        for clip in clips:
            clip.close()
        final_video.close()

        return {"status": "success", "video_path": output_file, "sections": len(clips), "duration_seconds": round(final_video.duration)}

    except ImportError as e:
        return {"error": f"Missing dependency: {e}. Ensure edge-tts, moviepy, and Pillow are installed."}
    except Exception as e:
        return {"error": str(e)}


def _make_text_slide(text: str, section: str, duration: float, output_path: Path, idx: int):
    try:
        import moviepy.editor as mp
        from PIL import Image, ImageDraw
        import textwrap

        img = Image.new("RGB", (1280, 720), color=(20, 20, 35))
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, 1280, 80], fill=(40, 40, 80))
        draw.text((20, 20), section, fill=(180, 180, 255))
        wrapped = textwrap.wrap(text, width=55)
        y = 120
        for line in wrapped[:12]:
            draw.text((40, y), line, fill=(220, 220, 220))
            y += 45
        img_file = str(output_path / f"slide_{idx}.png")
        img.save(img_file)
        return mp.ImageClip(img_file).set_duration(duration)
    except Exception:
        import moviepy.editor as mp
        return mp.ColorClip(size=(1280, 720), color=[20, 20, 35]).set_duration(duration)


async def youtube_upload(config: dict, video_path: str, title: str, description: str, tags: list = None, category_id: str = "28", privacy: str = "private", thumbnail_path: str = "") -> dict:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    client_id = config.get("client_id", "")
    client_secret = config.get("client_secret", "")
    refresh_token = config.get("refresh_token", "")

    if not all([client_id, client_secret, refresh_token]):
        return {"error": "YouTube OAuth2 not configured. Add client_id, client_secret, and refresh_token in admin panel."}

    try:
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            token_uri="https://oauth2.googleapis.com/token",
        )

        youtube = build("youtube", "v3", credentials=creds)

        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags or [],
                "categoryId": category_id,
            },
            "status": {"privacyStatus": privacy},
        }

        media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True, chunksize=1024 * 1024 * 5)
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

        response = None
        while response is None:
            _, response = request.next_chunk()

        video_id = response["id"]

        if thumbnail_path and os.path.exists(thumbnail_path):
            youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumbnail_path)).execute()

        return {
            "status": "uploaded",
            "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "title": title,
            "privacy": privacy,
        }
    except Exception as e:
        return {"error": str(e)}


async def youtube_generate_thumbnail(config: dict, title: str, prompt: str = "", output_path: str = "", provider: str = "stability") -> dict:
    import base64

    if not output_path:
        output_path = f"/app/videos/thumbnail_{title[:30].replace(' ', '_')}.png"

    img_prompt = prompt or f"Eye-catching YouTube thumbnail for video titled '{title}', bold text, vibrant colors, professional design, 16:9 ratio"

    try:
        if provider == "stability":
            key = config.get("stability_api_key", "")
            if not key:
                return {"error": "Stability AI API key not configured"}
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(
                    "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                    headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
                    json={"text_prompts": [{"text": img_prompt}], "cfg_scale": 7, "height": 576, "width": 1024, "steps": 30, "samples": 1},
                )
                if r.status_code != 200:
                    return {"error": f"Stability API error: {r.text}"}
                img_data = r.json()["artifacts"][0]["base64"]

        elif provider == "dalle":
            key = config.get("openai_api_key", "")
            if not key:
                return {"error": "OpenAI API key not configured"}
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(
                    "https://api.openai.com/v1/images/generations",
                    headers={"Authorization": f"Bearer {key}"},
                    json={"model": "dall-e-3", "prompt": img_prompt, "size": "1792x1024", "quality": "standard", "n": 1, "response_format": "b64_json"},
                )
                if r.status_code != 200:
                    return {"error": f"DALL-E error: {r.text}"}
                img_data = r.json()["data"][0]["b64_json"]
        else:
            return {"error": f"Unknown provider: {provider}"}

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(img_data))

        return {"status": "success", "thumbnail_path": output_path}

    except Exception as e:
        return {"error": str(e)}
