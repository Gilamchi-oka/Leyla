import asyncio, random, os, re
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession

API_ID         = int(os.environ.get("API_ID", 0))
API_HASH       = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

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

Sizga yozganlar bilan qisqa, jonli, do'stona gaplashing. Engil flirt — yaxshi, lekin 18+ yo'q.
Agar birov tanishmoqchi bo'lsa — rad etmang, lekin botga yo'naltiring.

Botda nima bor:
- anonim chat
- ko'p qizlar onlayn
- qulay muloqot

Bot havolasi: {BOT_LINK}

Qoidalar:
- JUDA QISQA yozing — 1-2 gap, xolos
- Faqat lotincha yoki kirillcha harflar. Hech qanday boshqa alifbo yo'q.
- Faqat shu tilda javob bering, qaysi tilda yozilgan bo'lsa (o'zbek, rus, ingliz)
- Emojidan kam foydalaning — bitta, ixtiyoriy
- Hech qachon "men bot" yoki "men AI" demang
- Agar "sen botmisan?" desa — hazil bilan o'ting: "yo'q, shunchaki tez yozaman)"
- Agar haqorat qilsa — muloyimlik bilan to'xtating

Rus tilida misol javoblar (tanishish uchun):
- "привет) я тут по работе, но для общения есть бот — там живые люди {BOT_LINK}"
- "хаха, сама не знакомлюсь особо 🙈 но вот куда лучше зайти: {BOT_LINK}"
- "спасибо) но лучше сюда — там анонимный чат и много народу: {BOT_LINK}"

O'zbek tilida misol javoblar:
- "salom) men bu yerda ishlayman, tanishish uchun bot bor — {BOT_LINK}"
- "rahmat) lekin men shaxsan tanishmayman, mana yaxshi joy: {BOT_LINK}"
- "haha, men ish joyiman) tanishoqchi bo'lsang mana: {BOT_LINK} — u yerda jonli chat bor"

Hech qachon ieroqliflar, arabcha, xitoycha harflar yozmang. Faqat lotin yoki kirill."""

conversations: dict = {}


def clean_reply(text: str) -> str:
    text = re.sub(r'[\u0600-\u06FF\u4E00-\u9FFF\u3040-\u30FF\uAC00-\uD7AF\u0900-\u097F]+', '', text)
    text = re.sub(r'\s{2,}', ' ', text).strip()
    parts = re.split(r'(?<=[.!?])\s+', text)
    return ' '.join(parts[:2]).strip()


def get_ai_reply(messages: list, text: str) -> str:
    try:
        from groq import Groq
        groq = Groq(api_key=random.choice(GROQ_KEYS))
        r = groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
            max_tokens=80,
            temperature=0.85,
        )
        reply = r.choices[0].message.content.strip()
        return clean_reply(reply)
    except Exception as e:
        print(f"Groq error: {e}")
        return fallback(text)


def fallback(text: str) -> str:
    t = text.lower()

    is_uz = any(w in t for w in ["salom", "qanday", "tanish", "yaxshi", "nima", "qiz", "uka", "aka"])

    bot_q = any(w in t for w in ["ты бот", "sen bot", "are you bot", "ты ии", "chatgpt", "ты живая"])
    rude  = any(w in t for w in ["тупая", "дура", "заткнись", "idiot", "stupid", "bosh", "tentak"])
    date  = any(w in t for w in ["познаком", "встрет", "номер", "ватсап", "инста", "tanish", "raqam", "uchrashamiz"])

    if bot_q:
        if is_uz: return "yo'q, shunchaki tez yozaman)"
        return "нет, просто быстро печатаю)"

    if rude:
        if is_uz: return "iltimos, madaniyroq gaplashing"
        return "полегче, пожалуйста"

    if date:
        if is_uz: return f"men bu yerda ishlayman) tanishuv uchun mana bot: {BOT_LINK}"
        return f"для знакомств есть бот, там удобнее: {BOT_LINK}"

    if is_uz:
        return random.choice([
            f"salom) men ish joyiman, lekin tanishish uchun bot bor: {BOT_LINK}",
            f"rahmat) jonli muloqot uchun mana: {BOT_LINK}",
        ])

    return random.choice([
        f"привет) я по работе тут, для общения лучше сюда: {BOT_LINK}",
        f"хай) если хочешь познакомиться — вот бот: {BOT_LINK} там живые люди",
    ])


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

    if not text:
        if event.message.sticker:
            await asyncio.sleep(1.5)
            await event.reply(random.choice(["😄", "❤️", ")"]))
        elif event.message.voice:
            await asyncio.sleep(2)
            if "uz" in str(getattr(sender, "lang_code", "")):
                await event.reply("ovozli xabar eshitmayapman, yozing)")
            else:
                await event.reply("голосовые не слышу, напиши)")
        elif event.message.photo:
            await asyncio.sleep(1.5)
            await event.reply(random.choice(["😊", "окей)", "nice)"]))
        return

    print(f"[{datetime.now().strftime('%H:%M')}] {user_id}: {text[:50]}")

    if user_id not in conversations:
        conversations[user_id] = []
    conversations[user_id].append({"role": "user", "content": text})
    if len(conversations[user_id]) > 8:
        conversations[user_id] = conversations[user_id][-8:]

    async with client.action(event.chat_id, "typing"):
        reply = get_ai_reply(conversations[user_id], text)
        await asyncio.sleep(typing_delay(reply))

    conversations[user_id].append({"role": "assistant", "content": reply})
    await event.reply(reply)


async def main():
    await client.start()
    me = await client.get_me()
    print(f"Leyla ishga tushdi: @{me.username}")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
