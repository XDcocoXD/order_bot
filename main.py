import asyncio
import os
import re
from datetime import timedelta
from httpx import post
from dotenv import load_dotenv
from telegram.request import HTTPXRequest
from telegram import Bot

load_dotenv(".env")
request = HTTPXRequest(connect_timeout=30, read_timeout=30)
bot = Bot(token=os.getenv("TELEGRAM_TOKEN"), request=request)


def add_order(text, date, username, title):
    notion_post = post(
        "https://api.notion.com/v1/pages",
        headers={
            "Authorization": f"Bearer {os.environ['NOTION_TOKEN']}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
        timeout=30,
        json={
            "parent": {"database_id": os.environ["NOTION_DATABASE_ID"]},
            "properties": {
                "Замовлення": {"rich_text": [{"text": {"content": text}}]},
                "Дата замовлення": {"date": {"start": date.isoformat()}},
                "Дата До": {"date": {"start": (date + timedelta(days=3)).isoformat()}},
                "Замовник": {"rich_text": [{"text": {"content": username or ""}}]},
                "Точка замовлення": {"title": [{"text": {"content": title or ""}}]},
            },
        },
    )
    print(notion_post.status_code)
    return notion_post.status_code == 200


chat_names = ["Константинівська", "Хорива", "Speak🅣🅘🅢🅗🅝🅐"]


def find_title(title):
    if not title:
        return ""
    for chat_name in chat_names:
        if chat_name.lower() in title.lower():
            return chat_name
    return "Невідомий чат"


def remove_tag(text, tag):
    cleaned = re.sub(re.escape(tag), "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    return cleaned.strip()


async def main():
    async with bot:
        me = await bot.get_me()
        print("Бот підключено:", me.username)
        tag = f"@{me.username}".lower()
        updates = await bot.get_updates(timeout=0)
        print("Нових оновлень:", len(updates))

        for update in updates:
            msg = update.message
            if not msg or not msg.entities or not msg.text:
                continue
            for e in msg.entities:
                if e.type == "mention" and msg.parse_entity(e).lower() == tag:
                    ok = add_order(
                        remove_tag(msg.text, tag),
                        msg.date,
                        msg.from_user.username or msg.from_user.first_name,
                        find_title(msg.chat.title),
                    )
                    if ok:
                        deadline = msg.date + timedelta(days=3)
                        await msg.reply_text(
                            f'Замовлення: \n {msg.text}\n  Буде доставлене Максимом до {deadline.strftime("%d.%m")} включно'
                        )
                    else:
                        await msg.reply_text("Не працює база, зверніться будь ласка до Максима")
                    break

        if updates:
            await bot.get_updates(offset=updates[-1].update_id + 1, timeout=0)


asyncio.run(main())


asyncio.run(main())
