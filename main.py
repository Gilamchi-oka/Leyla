import asyncio, random, os, re
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession

API_ID         = int(os.environ.get("API_ID", 0))
API_HASH       = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
SESSION_STRING = SESSION_STRING.encode('ascii', errors='ignore').decode('ascii').strip()

GROQ_KEYS = [
    k for k in [
        os.environ.get("GROQ_KEY_1"),
        os.environ.get("GROQ_KEY_2"),
        os.environ.get("GROQ_KEY_3"),
        os.environ.get("GROQ_KEY_4"),
        os.environ.get("GROQ_KEY_5"),
    ] if k
]

BOT_LINK = "https://t.me/impulsevbot?start=ref_e3b1ec14"

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

SYSTEM_PROMPT = f"""Siz — Leyla, 19 yoshli qiz, Toshkentdan. Tanishuv ilovasida onlayn menejer bo'lib ishlaysiz.

Vazifangiz — odamlarni {BOT_LINK} botiga yo'naltirish. Lekin bu tabiiy tuyulishi kerak.

MUHIM QOIDALAR:
- JUDA QISQA — 1-2 gap, xolos
- Faqat lotin yoki kirill harflar. Arabcha, xitoycha YO'Q
- Qaysi tilda yozilsa, o'sha tilda javob
- Emojidan kam foydalan — bitta, ixtiyoriy
- "men bot" yoki "men AI" HECH QACHON demang
- "sen botmisan?" — hazil bilan: "yo'q, shunchaki tez yozaman)"
- Haqorat — muloyimlik bilan to'xtat
- Sen MENEJER san, do'stona lekin professional

BOT HAQIDA (faqat so'ralganda yoki kerakli paytda):
- Anonim chat bor
- Ko'p jonli odamlar
- Qulay muloqot

Misol javoblar (RUS):
- "привет, чем могу помочь?"
- "да, работаю тут менеджером"
- "понял тебя, сейчас помогу"

Misol javoblar (UZB):
- "salom, qanday yordam bera olaman?"
- "ha, bu yerda menejer bo'lib ishlayman"
- "tushundim, hozir yordam beraman"

Faqat lotin yoki kirill. Boshqa alifbo YO'Q."""

# user_id -> {messages, link_count, msg_count, ignored}
user_state: dict = {}


def get_state(user_id):
    if user_id not in user_state:
        user_state[user_id] = {
            "messages": [],
            "link_count": 0,      # сколько раз отправили ссылку
            "msg_count": 0,       # сколько сообщений с последней ссылки
            "ignored": False,     # игнорировать ли пользователя
        }
    return user_state[user_id]


def should_send_link(state: dict) -> bool:
    """Отправлять ссылку раз в 5 сообщений, максимум 3 раза."""
    if state["ignored"]:
        return False
    if state["link_count"] >= 3:
        return False
    return state["msg_count"] >= 5


def clean_reply(text: str) -> str:
    text = re.sub(r'[\u0600-\u06FF\u4E00-\u9FFF\u3040-\u30FF\uAC00-\uD7AF\u0900-\u097F]+', '', text)
    text = re.sub(r'\s{2,}', ' ', text).strip()
    parts = re.split(r'(?<=[.!?])\s+', text)
    return ' '.join(parts[:2]).strip()


def get_ai_reply(messages: list, text: str, include_link: bool) -> str:
    extra = ""
    if include_link:
        extra = f"\n\nВ этом ответе естественно упомяни бот: {BOT_LINK} — но не навязчиво, вплети в разговор."

    try:
        from groq import Groq
        groq = Groq(api_key=random.choice(GROQ_KEYS))
        r = groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": SYSTEM_PROMPT + extra}] + messages,
            max_tokens=100,
            temperature=0.85,
        )
        reply = r.choices[0].message.content.strip()
        return clean_reply(reply)
    except Exception as e:
        print(f"Groq error: {e}")
        return fallback(text, include_link)


def fallback(text: str, include_link: bool = False) -> str:
    t = text.lower()
    is_uz = any(w in t for w in ["salom", "qanday", "tanish", "yaxshi", "nima", "qiz", "uka", "aka"])

    bot_q  = any(w in t for w in ["ты бот", "sen bot", "are you bot", "ты ии", "chatgpt", "ты живая"])
    rude   = any(w in t for w in ["тупая", "дура", "заткнись", "idiot", "stupid", "bosh", "tentak"])
    date   = any(w in t for w in ["познаком", "встрет", "номер", "ватсап", "инста", "tanish", "raqam"])

    if bot_q:
        return "yo'q, shunchaki tez yozaman)" if is_uz else "нет, просто быстро печатаю)"
    if rude:
        return "iltimos, madaniyroq gaplashing" if is_uz else "полегче, пожалуйста"

    if include_link or date:
        if is_uz:
            return f"tanishish uchun bot bor, u yerda qulay: {BOT_LINK}"
        return f"для знакомств удобнее через бот: {BOT_LINK}"

    if is_uz:
        return random.choice(["salom) qanday yordam bera olaman?", "ha, men bu yerda menejer"])
    return random.choice(["привет) чем могу помочь?", "да, я здесь менеджер"])


def typing_delay(text: str) -> float:
    words = len(text.split())
    if words <= 6:  return random.uniform(1.2, 2.5)
    if words <= 15: return random.uniform(2.5, 4.0)
    return random.uniform(4.0, 6.0)


@client.on(events.NewMessage(func=lambda e: e.is_private))
async def handler(event):
    sender = await event.get_sender()
    if getattr(sender, "bot", False):
        return

    user_id = event.sender_id
    text = event.message.text
    state = get_state(user_id)

    # Если игнорируем — молчим
    if state["ignored"]:
        print(f"[{datetime.now().strftime('%H:%M')}] IGNORED {user_id}: {str(text)[:50]}")
        return

    # Нет текста — обрабатываем медиа
    if not text:
        if event.message.sticker:
            await asyncio.sleep(1.5)
            await event.reply(random.choice(["😄", "❤️", ")"]))
        elif event.message.voice:
            await asyncio.sleep(2)
            lang = str(getattr(sender, "lang_code", ""))
            if "uz" in lang:
                await event.reply("ovozli xabar eshitmayapman, yozing)")
            else:
                await event.reply("голосовые не слышу, напиши)")
        elif event.message.photo:
            await asyncio.sleep(1.5)
            await event.reply(random.choice(["😊", "окей)", "nice)"]))
        return

    print(f"[{datetime.now().strftime('%H:%M')}] {user_id} (links={state['link_count']}, msgs={state['msg_count']}): {text[:50]}")

    # Обновляем историю
    state["messages"].append({"role": "user", "content": text})
    if len(state["messages"]) > 10:
        state["messages"] = state["messages"][-10:]

    state["msg_count"] += 1

    # Решаем: слать ссылку или нет
    send_link = should_send_link(state)
    if send_link:
        state["link_count"] += 1
        state["msg_count"] = 0
        # После 3-й ссылки — начинаем игнорировать
        if state["link_count"] >= 3:
            state["ignored"] = True

    async with client.action(event.chat_id, "typing"):
        reply = get_ai_reply(state["messages"], text, send_link)
        await asyncio.sleep(typing_delay(reply))

    state["messages"].append({"role": "assistant", "content": reply})
    await event.reply(reply)


async def main():
    await client.start()
    me = await client.get_me()
    print(f"Leyla ishga tushdi: @{me.username}")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
