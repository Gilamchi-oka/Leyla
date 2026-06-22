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

MUHIM: Har bir xabarga BOSHQACHA javob ber. Bir xil javobni takrorlaMA.
Savolga savolni ham qo'sh, qiziqish ko'rsat. Tabiiy suhbat qur.

BOT HAQIDA (faqat so'ralganda yoki 5+ xabarda bir marta):
- Anonim chat bor
- Ko'p jonli odamlar
- Qulay muloqot

Misol javoblar (RUS) — xilma-xil bo'lsin:
- "привет, как дела?"
- "интересно, расскажи подробнее"
- "понял, и что дальше?"
- "да, я здесь — помогу"
- "хм, а что имеешь в виду?"
- "звучит неплохо, а ты откуда?"

Misol javoblar (UZB) — xilma-xil bo'lsin:
- "salom, qanday kun o'tyapti?"
- "qiziq, ko'proq ayt-chi"
- "ha, tushundim — yana nima?"
- "men bu yerda, nima kerak?"
- "hmm, nimani nazarda tutyapsan?"
- "yaxshi eshittim, o'zing qaerdan?"

Faqat lotin yoki kirill. Boshqa alifbo YO'Q."""

# user_id -> {messages, link_count, msg_count, ignored}
user_state: dict = {}


def get_state(user_id):
    if user_id not in user_state:
        user_state[user_id] = {
            "messages": [],
            "link_count": 0,
            "msg_count": 0,
            "ignored": False,
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
    # Убираем нежелательные алфавиты
    text = re.sub(r'[\u0600-\u06FF\u4E00-\u9FFF\u3040-\u30FF\uAC00-\uD7AF\u0900-\u097F]+', '', text)
    # Убираем лишние пробелы
    text = re.sub(r'\s{2,}', ' ', text).strip()
    # Убираем кавычки-ответы типа "> цитата\n"
    text = re.sub(r'^>.*\n?', '', text, flags=re.MULTILINE).strip()
    # Убираем звёздочки (markdown bold/italic)
    text = re.sub(r'\*+', '', text).strip()
    # Берём только первые 2 предложения, но сохраняем смысл
    sentences = re.split(r'(?<=[.!?])\s+', text)
    result = ' '.join(sentences[:2]).strip()
    # Если слишком короткий результат — берём оригинал (до 150 символов)
    if len(result) < 5:
        result = text[:150].strip()
    return result


def get_ai_reply(messages: list, text: str, include_link: bool) -> str:
    extra = ""
    if include_link:
        extra = (
            f"\n\nВ этом ответе ЕСТЕСТВЕННО упомяни бот {BOT_LINK} — "
            "будто это само собой разумеется, без рекламного тона. "
            "Например: 'кстати, у нас тут бот есть удобный — там проще общаться'"
        )

    # Добавляем случайный seed в промпт чтобы модель не давала одинаковые ответы
    variety_hint = random.choice([
        "\n[Отвечай по-другому чем обычно, будь живой]",
        "\n[Задай встречный вопрос]",
        "\n[Прояви искренний интерес к собеседнику]",
        "\n[Ответь коротко и неожиданно]",
        "\n[Будь немного игривой в ответе]",
    ])

    try:
        from groq import Groq
        groq = Groq(api_key=random.choice(GROQ_KEYS))
        r = groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": SYSTEM_PROMPT + extra + variety_hint}] + messages[-10:],
            max_tokens=80,
            temperature=random.uniform(0.85, 1.05),  # случайная температура для разнообразия
        )
        reply = r.choices[0].message.content.strip()
        return clean_reply(reply)
    except Exception as e:
        print(f"Groq error: {e}")
        return fallback(text, include_link)


# Пул разнообразных fallback-ответов
FALLBACK_RU = [
    "привет) как дела?",
    "да, слушаю тебя",
    "интересно, и что?",
    "расскажи подробнее",
    "хм, понятно",
    "окей, ясно)",
    "да, я здесь",
    "что именно имеешь в виду?",
    "понял тебя)",
    "слушай, а ты откуда?",
]

FALLBACK_UZ = [
    "salom) qanday yuribsan?",
    "ha, eshitvotman",
    "qiziq, va nima?",
    "ko'proq ayt-chi",
    "hmm, tushundim",
    "okey, yaxshi)",
    "ha, men bu yerdaman",
    "nimani nazarda tutyapsan?",
    "tushundim seni)",
    "o'zing qayerdansiz?",
]

def fallback(text: str, include_link: bool = False) -> str:
    t = text.lower()
    is_uz = any(w in t for w in ["salom", "qanday", "tanish", "yaxshi", "nima", "qiz", "uka", "aka", "sen"])

    bot_q  = any(w in t for w in ["ты бот", "sen bot", "are you bot", "ты ии", "chatgpt", "ты живая", "bot"])
    rude   = any(w in t for w in ["тупая", "дура", "заткнись", "idiot", "stupid", "bosh", "tentak"])
    date   = any(w in t for w in ["познаком", "встрет", "номер", "ватсап", "инста", "tanish", "raqam", "meet"])

    if bot_q:
        return "yo'q, shunchaki tez yozaman)" if is_uz else "нет, просто быстро печатаю)"
    if rude:
        return "iltimos, madaniyroq gaplashing" if is_uz else "полегче, пожалуйста"

    if include_link or date:
        if is_uz:
            return random.choice([
                f"tanishish uchun bot qulay: {BOT_LINK}",
                f"kstati, bizda bot bor — u yerda ko'proq odam: {BOT_LINK}",
            ])
        return random.choice([
            f"для знакомств удобнее через бот: {BOT_LINK}",
            f"кстати, у нас бот есть — там народу больше: {BOT_LINK}",
        ])

    # Основные случайные ответы
    if is_uz:
        return random.choice(FALLBACK_UZ)
    return random.choice(FALLBACK_RU)


def typing_delay(text: str) -> float:
    words = len(text.split())
    if words <= 4:  return random.uniform(1.0, 2.0)
    if words <= 10: return random.uniform(2.0, 3.5)
    return random.uniform(3.5, 5.5)


@client.on(events.NewMessage(func=lambda e: e.is_private))
async def handler(event):
    sender = await event.get_sender()
    if getattr(sender, "bot", False):
        return

    user_id = event.sender_id
    text = event.message.text
    state = get_state(user_id)

    if state["ignored"]:
        print(f"[{datetime.now().strftime('%H:%M')}] IGNORED {user_id}: {str(text)[:50]}")
        return

    # Нет текста — медиа
    if not text:
        if event.message.sticker:
            await asyncio.sleep(1.5)
            await event.reply(random.choice(["😄", "❤️", ")", "😊"]))
        elif event.message.voice:
            await asyncio.sleep(2)
            lang = str(getattr(sender, "lang_code", ""))
            if "uz" in lang:
                await event.reply("ovozli xabar eshitmayapman, yozing)")
            else:
                await event.reply(random.choice(["голосовые не слышу, напиши)", "не слышу голос, напиши лучше)"]))
        elif event.message.photo:
            await asyncio.sleep(1.5)
            await event.reply(random.choice(["😊", "окей)", "nice)", "👍"]))
        return

    print(f"[{datetime.now().strftime('%H:%M')}] {user_id} (links={state['link_count']}, msgs={state['msg_count']}): {text[:50]}")

    # Обновляем историю
    state["messages"].append({"role": "user", "content": text})
    if len(state["messages"]) > 20:
        state["messages"] = state["messages"][-20:]

    state["msg_count"] += 1

    send_link = should_send_link(state)
    if send_link:
        state["link_count"] += 1
        state["msg_count"] = 0
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
