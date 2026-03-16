"""
fb_poster.py
Posts image + caption to Facebook Page, adds article URL as first comment.
Requires in .env: FB_PAGE_ID, FB_ACCESS_TOKEN
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

FB_PAGE_ID      = os.getenv("FB_PAGE_ID", "")
FB_ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN", "")
GRAPH_API_URL   = "https://graph.facebook.com/v19.0"


def post_to_facebook(image_path: str, caption: str, article_url: str = "") -> bool:
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        print("  ❌ FB_PAGE_ID or FB_ACCESS_TOKEN not set in .env")
        return False

    try:
        # Step 1: Upload photo unpublished
        print("  📤 Uploading image to Facebook...")
        with open(image_path, "rb") as f:
            upload_resp = requests.post(
                f"{GRAPH_API_URL}/{FB_PAGE_ID}/photos",
                data={"access_token": FB_ACCESS_TOKEN, "published": "false"},
                files={"source": f},
                timeout=60,
            )
        upload_data = upload_resp.json()
        if "id" not in upload_data:
            print(f"  ❌ Upload failed: {upload_data}")
            return False
        photo_id = upload_data["id"]
        print(f"  ✅ Photo uploaded (id: {photo_id})")

        # Step 2: Publish post
        print("  📢 Publishing post...")
        post_resp = requests.post(
            f"{GRAPH_API_URL}/{FB_PAGE_ID}/feed",
            data={
                "access_token":      FB_ACCESS_TOKEN,
                "message":           caption,
                "attached_media[0]": f'{{"media_fbid":"{photo_id}"}}',
            },
            timeout=30,
        )
        post_data = post_resp.json()
        if "id" not in post_data:
            print(f"  ❌ Post failed: {post_data}")
            return False
        post_id = post_data["id"]
        print(f"  ✅ Post published! Post ID: {post_id}")

        # Step 3: Add article URL as first comment
        if article_url:
            print("  💬 Adding article URL as first comment...")
            comment_resp = requests.post(
                f"{GRAPH_API_URL}/{post_id}/comments",
                data={
                    "access_token": FB_ACCESS_TOKEN,
                    "message":      f"🔗 Read the full article here: {article_url}",
                },
                timeout=15,
            )
            comment_data = comment_resp.json()
            if "id" in comment_data:
                print("  ✅ Comment added!")
            else:
                print(f"  ⚠️  Comment failed: {comment_data}")

        return True

    except Exception as e:
        print(f"  ❌ Facebook post exception: {e}")
        return False


if __name__ == "__main__":
    print("FB_PAGE_ID set     :", bool(FB_PAGE_ID))
    print("FB_ACCESS_TOKEN set:", bool(FB_ACCESS_TOKEN))
