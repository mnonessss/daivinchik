import asyncio
import json
import os

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramNetworkError
from aiogram.filters import Command
from aiogram.filters import CommandStart
import aiohttp
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
API_URL = os.getenv("API_URL")
if not TOKEN or not API_URL:
    raise RuntimeError("TOKEN and API_URL must be set in environment or .env file")

bot = Bot(token=TOKEN)
dp = Dispatcher()
session_user_ids: dict[int, int] = {}
session_current_candidates: dict[int, int] = {}
profile_edit_drafts: dict[int, dict[str, str | int]] = {}
awaiting_profile_field: dict[int, str] = {}
uploading_profile_photos: set[int] = set()
pending_photo_delete_map: dict[int, dict[int, int]] = {}

feed_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔎 Следующая анкета")],
        [KeyboardButton(text="👤 Моя анкета")],
        [KeyboardButton(text="📷 Добавить фото")],
        [KeyboardButton(text="✏️ Редактировать анкету")],
        [KeyboardButton(text="🗑 Удалить анкету")],
    ],
    resize_keyboard=True,
)

candidate_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="❤️ Лайк"), KeyboardButton(text="⏭ Скип")],
        [KeyboardButton(text="🔎 Следующая анкета")],
        [KeyboardButton(text="👤 Моя анкета")],
        [KeyboardButton(text="📷 Добавить фото")],
        [KeyboardButton(text="✏️ Редактировать анкету")],
        [KeyboardButton(text="🗑 Удалить анкету")],
    ],
    resize_keyboard=True,
)

edit_profile_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Имя"), KeyboardButton(text="🎂 Возраст")],
        [KeyboardButton(text="🏙 Город"), KeyboardButton(text="📖 О себе")],
        [KeyboardButton(text="👫 Предпочтения")],
        [KeyboardButton(text="🖼 Удалить фото")],
        [KeyboardButton(text="✅ Сохранить"), KeyboardButton(text="❌ Отмена")],
    ],
    resize_keyboard=True,
)

preferences_edit_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎯 Мин. возраст"), KeyboardButton(text="🎯 Макс. возраст")],
        [KeyboardButton(text="🏙 Предпочтительный город"), KeyboardButton(text="⚧ Предпочтительный пол")],
        [KeyboardButton(text="↩️ Назад к редактированию")],
    ],
    resize_keyboard=True,
)

photo_upload_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✅ Готово с фото"), KeyboardButton(text="❌ Отмена загрузки фото")],
    ],
    resize_keyboard=True,
)


async def fetch_next_candidate(user_id):
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(f"{API_URL}/ranking/feed/next/{user_id}") as resp:
            if resp.status == 404:
                return None
            if resp.status != 200:
                return None
            try:
                return await resp.json(content_type=None)
            except (aiohttp.ContentTypeError, json.JSONDecodeError):
                return None


async def send_interaction(from_user, to_user, action):
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        await session.post(
            f"{API_URL}/interactions/",
            json={"from_user": from_user, "to_user": to_user, "action": action},
        )


async def check_match(user_a, user_b):
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(f"{API_URL}/interactions/match/{user_a}/{user_b}") as resp:
            if resp.status != 200:
                return False
            try:
                payload = await resp.json(content_type=None)
            except (aiohttp.ContentTypeError, json.JSONDecodeError):
                return False
            return bool(payload.get("matched"))


async def get_my_profile(user_id):
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(f"{API_URL}/profiles/by-user/{user_id}") as resp:
            if resp.status == 404:
                return None
            if resp.status != 200:
                return None
            return await resp.json(content_type=None)


async def get_profile_photos(profile_id):
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(f"{API_URL}/profiles/{profile_id}/photos") as resp:
            if resp.status == 404:
                return []
            if resp.status != 200:
                return []
            return await resp.json(content_type=None)


async def delete_my_profile(user_id):
    profile = await get_my_profile(user_id)
    if not profile:
        return False
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.delete(f"{API_URL}/profiles/{profile['id']}") as resp:
            return resp.status == 204


async def update_my_profile(user_id, payload):
    profile = await get_my_profile(user_id)
    if not profile:
        return False
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.put(f"{API_URL}/profiles/{profile['id']}", json=payload) as resp:
            return resp.status == 200


async def attach_profile_photo(user_id, telegram_file_id):
    try:
        profile = await get_my_profile(user_id)
    except Exception as exc:
        return False, f"get_my_profile failed: {type(exc).__name__}: {exc}"

    if not profile:
        return False, "Профиль не найден"

    endpoint = f"{API_URL}/profiles/{profile['id']}/photos"
    request_payload = {"telegram_file_id": telegram_file_id}
    timeout = aiohttp.ClientTimeout(total=10)

    for attempt in range(2):
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(endpoint, json=request_payload) as resp:
                    if 200 <= resp.status < 300:
                        return True, ""
                    body = await resp.text()
                    body_preview = body[:200] if body else "empty response"
                    return False, f"{endpoint} -> {resp.status} ({body_preview})"
        except aiohttp.ClientError as exc:
            if attempt == 1:
                return False, f"upload request failed: {type(exc).__name__}: {exc}"
            continue
        except Exception as exc:
            return False, f"upload request failed: {type(exc).__name__}: {exc}"

    return False, "Не удалось загрузить фото"


async def delete_profile_photo(user_id, photo_id):
    profile = await get_my_profile(user_id)
    if not profile:
        return False, "Профиль не найден"

    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.delete(f"{API_URL}/profiles/{profile['id']}/photos/{photo_id}") as resp:
            if resp.status == 204:
                return True, ""
            body = await resp.text()
            body_preview = body[:200] if body else "empty response"
            return False, f"{resp.status} ({body_preview})"


async def ensure_user_id(telegram_id: int):
    user_id = session_user_ids.get(telegram_id)
    if user_id:
        return user_id

    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(
            f"{API_URL}/users/register",
            json={"telegram_id": telegram_id},
        ) as resp:
            if resp.status != 200:
                return None
            try:
                payload = await resp.json(content_type=None)
            except (aiohttp.ContentTypeError, json.JSONDecodeError):
                return None

    user_id = payload.get("user_id")
    if not user_id:
        return None
    session_user_ids[telegram_id] = user_id
    return user_id


def start_edit_session(user_id):
    profile_edit_drafts[user_id] = {}
    awaiting_profile_field.pop(user_id, None)


def close_edit_session(user_id):
    profile_edit_drafts.pop(user_id, None)
    awaiting_profile_field.pop(user_id, None)
    pending_photo_delete_map.pop(user_id, None)


async def show_next_profile(message, user_id):
    candidate = await fetch_next_candidate(user_id)
    if not candidate:
        await message.answer("Подходящих анкет пока нет.", reply_markup=feed_keyboard)
        return

    session_current_candidates[user_id] = candidate["user_id"]
    card = (
        f"Имя: {candidate.get('name')}\n"
        f"Возраст: {candidate.get('age')}\n"
        f"Пол: {candidate.get('gender')}\n"
        f"Город: {candidate.get('city')}\n"
        f"О себе: {candidate.get('bio')}\n"
        f"Рейтинг: {candidate.get('final_score')}\n"
        "Действия: ❤️ Лайк или ⏭ Скип"
    )
    await message.answer(card, reply_markup=candidate_keyboard)


def render_profile_card(profile):
    def display_or_default(value, default="Не задано"):
        return value if value not in (None, "") else default

    preferred_age_min = display_or_default(profile.get("preferred_age_min"))
    preferred_age_max = display_or_default(profile.get("preferred_age_max"))
    preferred_city = display_or_default(profile.get("preferred_city"))
    preferred_gender = display_or_default(profile.get("preferred_gender"))

    return (
        "Твоя анкета:\n"
        f"Имя: {display_or_default(profile.get('name'))}\n"
        f"Возраст: {display_or_default(profile.get('age'))}\n"
        f"Пол: {display_or_default(profile.get('gender'))}\n"
        f"Город: {display_or_default(profile.get('city'))}\n"
        f"О себе: {display_or_default(profile.get('bio'))}\n"
        f"Фото: {display_or_default(profile.get('photos_count'), 0)}\n"
        "Предпочтения:\n"
        f"  - Возраст: {preferred_age_min} - {preferred_age_max}\n"
        f"  - Город: {preferred_city}\n"
        f"  - Пол: {preferred_gender}"
    )


@dp.message(CommandStart())
async def start_handler(message: Message):
    telegram_id = message.from_user.id
    welcome_text = "Добро пожаловать в Дайвинчик"

    payload = None
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f"{API_URL}/users/register",
                json={"telegram_id": telegram_id},
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    await message.answer(
                        f"Ошибка регистрации: API вернул {resp.status}.\n"
                        f"Ответ: {body[:200] or 'empty response'}"
                    )
                    return
                try:
                    payload = await resp.json(content_type=None)
                except (aiohttp.ContentTypeError, json.JSONDecodeError):
                    body = await resp.text()
                    await message.answer(
                        "Ошибка регистрации: API вернул не JSON.\n"
                        f"Ответ: {body[:200] or 'empty response'}"
                    )
                    return
    except (asyncio.TimeoutError, aiohttp.ServerTimeoutError):
        await message.answer(
            "Сервис регистрации не отвечает (таймаут). Попробуй еще раз через минуту."
        )
        return
    except aiohttp.ClientError:
        await message.answer(
            "Не удалось связаться с API. Проверьте, что backend запущен."
        )
        return

    user_id = payload["user_id"]
    session_user_ids[telegram_id] = user_id

    # Прогрев ленты не должен ломать успешную регистрацию.
    try:
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            await session.post(f"{API_URL}/ranking/feed/start/{user_id}")
    except (asyncio.TimeoutError, aiohttp.ClientError):
        pass

    if payload.get("already_registered") is True:
        await message.answer(
            "Вы уже зарегистрированы. Используй кнопки для просмотра ленты.",
            reply_markup=feed_keyboard,
        )
        return
    await message.answer(
        f"{welcome_text}\nНажми «Следующая анкета», чтобы начать.",
        reply_markup=feed_keyboard,
    )


@dp.message(Command("next"))
@dp.message(lambda message: message.text == "🔎 Следующая анкета")
async def next_handler(message):
    telegram_id = message.from_user.id
    user_id = await ensure_user_id(telegram_id)
    if not user_id:
        await message.answer("Сначала зарегистрируйся через /start")
        return

    try:
        await show_next_profile(message, user_id)
    except aiohttp.ClientError:
        await message.answer("Не удалось получить следующую анкету.")


@dp.message(lambda message: message.text == "❤️ Лайк")
async def like_handler(message: Message):
    telegram_id = message.from_user.id
    user_id = await ensure_user_id(telegram_id)
    candidate_user_id = session_current_candidates.get(user_id) if user_id else None
    if not user_id or not candidate_user_id:
        await message.answer("Сначала открой анкету через кнопку «Следующая анкета».")
        return

    try:
        await send_interaction(user_id, candidate_user_id, "like")
        await message.answer("Лайк отправлен.")
        if await check_match(user_id, candidate_user_id):
            candidate_profile = await get_my_profile(candidate_user_id)
            candidate_name = (
                candidate_profile.get("name")
                if candidate_profile and candidate_profile.get("name")
                else "этим пользователем"
            )
            await message.answer(f"🎉 У вас мэтч с {candidate_name}!")
        await show_next_profile(message, user_id)
    except aiohttp.ClientError:
        await message.answer("Не удалось отправить лайк.")


@dp.message(lambda message: message.text == "⏭ Скип")
async def skip_handler(message: Message):
    telegram_id = message.from_user.id
    user_id = await ensure_user_id(telegram_id)
    candidate_user_id = session_current_candidates.get(user_id) if user_id else None
    if not user_id or not candidate_user_id:
        await message.answer("Сначала открой анкету через кнопку «Следующая анкета».")
        return

    try:
        await send_interaction(user_id, candidate_user_id, "skip")
        await message.answer("Анкета пропущена.")
        await show_next_profile(message, user_id)
    except aiohttp.ClientError:
        await message.answer("Не удалось отправить скип.")


@dp.message(Command("edit_profile"))
@dp.message(
    lambda message: message.text in {"✏️ Редактировать анкету", "✏️ Редактировать профиль"}
)
async def edit_profile_handler(message: Message):
    telegram_id = message.from_user.id
    user_id = await ensure_user_id(telegram_id)
    if not user_id:
        await message.answer("Сначала зарегистрируйся через /start")
        return
    start_edit_session(user_id)
    await message.answer(
        "Открыто окно редактирования.\n"
        "Выбери поле кнопкой, введи значение, затем нажми «Сохранить». "
        "Можно изменить несколько полей за раз.",
        reply_markup=edit_profile_keyboard,
    )


@dp.message(Command("my_profile"))
@dp.message(lambda message: message.text == "👤 Моя анкета")
async def my_profile_handler(message: Message):
    telegram_id = message.from_user.id
    user_id = await ensure_user_id(telegram_id)
    if not user_id:
        await message.answer("Сначала зарегистрируйся через /start")
        return
    try:
        profile = await get_my_profile(user_id)
        if not profile:
            await message.answer("Анкета пока не создана.", reply_markup=feed_keyboard)
            return
        await message.answer(render_profile_card(profile), reply_markup=feed_keyboard)
        photos = await get_profile_photos(profile["id"])
        for photo in photos:
            telegram_file_id = photo.get("telegram_file_id")
            if telegram_file_id:
                await message.answer_photo(photo=telegram_file_id, reply_markup=feed_keyboard)
    except aiohttp.ClientError:
        await message.answer("Не удалось получить данные анкеты.")


@dp.message(Command("add_photo"))
@dp.message(lambda message: message.text == "📷 Добавить фото")
async def add_photo_mode_handler(message: Message):
    user_id = await ensure_user_id(message.from_user.id)
    if not user_id:
        await message.answer("Сначала зарегистрируйся через /start")
        return
    uploading_profile_photos.add(user_id)
    await message.answer(
        "Режим загрузки фото включен.\n"
        "Пришли одно или несколько фото отдельными сообщениями. "
        "Когда закончишь, нажми «Готово с фото».",
        reply_markup=photo_upload_keyboard,
    )


@dp.message(Command("delete_profile"))
@dp.message(lambda message: message.text in {"🗑 Удалить анкету", "🗑 Удалить профиль"})
async def delete_profile_handler(message: Message):
    telegram_id = message.from_user.id
    user_id = await ensure_user_id(telegram_id)
    if not user_id:
        await message.answer("Сначала зарегистрируйся через /start")
        return
    try:
        deleted = await delete_my_profile(user_id)
        if not deleted:
            await message.answer("Профиль не найден или не удалось удалить.")
            return
        await message.answer("Профиль удален.")
    except aiohttp.ClientError:
        await message.answer("Ошибка при удалении профиля.")


@dp.message(lambda message: message.text == "📝 Имя")
async def edit_name_prompt_handler(message: Message):
    user_id = session_user_ids.get(message.from_user.id)
    if not user_id or user_id not in profile_edit_drafts:
        return
    awaiting_profile_field[user_id] = "name"
    await message.answer("Введи новое имя:")


@dp.message(lambda message: message.text == "🎂 Возраст")
async def edit_age_prompt_handler(message: Message):
    user_id = session_user_ids.get(message.from_user.id)
    if not user_id or user_id not in profile_edit_drafts:
        return
    awaiting_profile_field[user_id] = "age"
    await message.answer("Введи возраст (число):")


@dp.message(lambda message: message.text == "🏙 Город")
async def edit_city_prompt_handler(message: Message):
    user_id = session_user_ids.get(message.from_user.id)
    if not user_id or user_id not in profile_edit_drafts:
        return
    awaiting_profile_field[user_id] = "city"
    await message.answer("Введи город:")


@dp.message(lambda message: message.text == "📖 О себе")
async def edit_bio_prompt_handler(message: Message):
    user_id = session_user_ids.get(message.from_user.id)
    if not user_id or user_id not in profile_edit_drafts:
        return
    awaiting_profile_field[user_id] = "bio"
    await message.answer("Введи текст для поля «О себе»:")


@dp.message(lambda message: message.text == "👫 Предпочтения")
async def edit_preferences_prompt_handler(message: Message):
    user_id = session_user_ids.get(message.from_user.id)
    if not user_id or user_id not in profile_edit_drafts:
        return
    await message.answer(
        "Открыто редактирование предпочтений.\n"
        "Выбери нужное поле кнопкой.",
        reply_markup=preferences_edit_keyboard,
    )


@dp.message(lambda message: message.text == "🎯 Мин. возраст")
async def edit_pref_age_min_prompt_handler(message: Message):
    user_id = session_user_ids.get(message.from_user.id)
    if not user_id or user_id not in profile_edit_drafts:
        return
    awaiting_profile_field[user_id] = "preferred_age_min"
    await message.answer("Введи минимальный предпочтительный возраст:")


@dp.message(lambda message: message.text == "🎯 Макс. возраст")
async def edit_pref_age_max_prompt_handler(message: Message):
    user_id = session_user_ids.get(message.from_user.id)
    if not user_id or user_id not in profile_edit_drafts:
        return
    awaiting_profile_field[user_id] = "preferred_age_max"
    await message.answer("Введи максимальный предпочтительный возраст:")


@dp.message(lambda message: message.text == "🏙 Предпочтительный город")
async def edit_pref_city_prompt_handler(message: Message):
    user_id = session_user_ids.get(message.from_user.id)
    if not user_id or user_id not in profile_edit_drafts:
        return
    awaiting_profile_field[user_id] = "preferred_city"
    await message.answer("Введи предпочитаемый город (или '-' чтобы очистить):")


@dp.message(lambda message: message.text == "⚧ Предпочтительный пол")
async def edit_pref_gender_prompt_handler(message: Message):
    user_id = session_user_ids.get(message.from_user.id)
    if not user_id or user_id not in profile_edit_drafts:
        return
    awaiting_profile_field[user_id] = "preferred_gender"
    await message.answer("Введи предпочитаемый пол (или '-' чтобы очистить):")


@dp.message(lambda message: message.text == "↩️ Назад к редактированию")
async def back_to_edit_profile_handler(message: Message):
    user_id = session_user_ids.get(message.from_user.id)
    if not user_id or user_id not in profile_edit_drafts:
        return
    awaiting_profile_field.pop(user_id, None)
    await message.answer("Возвращаю в общее редактирование анкеты.", reply_markup=edit_profile_keyboard)


@dp.message(lambda message: message.text == "🖼 Удалить фото")
async def edit_delete_photo_prompt_handler(message: Message):
    user_id = session_user_ids.get(message.from_user.id)
    if not user_id or user_id not in profile_edit_drafts:
        return

    profile = await get_my_profile(user_id)
    if not profile:
        await message.answer("Анкета не найдена.", reply_markup=edit_profile_keyboard)
        return

    photos = await get_profile_photos(profile["id"])
    if not photos:
        await message.answer("У тебя пока нет фото для удаления.", reply_markup=edit_profile_keyboard)
        return

    pending_photo_delete_map[user_id] = {}
    await message.answer("Выбери фото для удаления: отправь номер фото из списка.")
    for idx, photo in enumerate(photos, start=1):
        pending_photo_delete_map[user_id][idx] = photo["id"]
        file_id = photo.get("telegram_file_id")
        if file_id:
            await message.answer_photo(photo=file_id, caption=f"Фото #{idx}")

    awaiting_profile_field[user_id] = "delete_photo"


@dp.message(lambda message: message.text == "✅ Готово с фото")
async def finish_photo_upload_handler(message: Message):
    user_id = session_user_ids.get(message.from_user.id)
    if not user_id or user_id not in uploading_profile_photos:
        return
    uploading_profile_photos.discard(user_id)
    await message.answer("Загрузка фото завершена.", reply_markup=feed_keyboard)


@dp.message(lambda message: message.text == "❌ Отмена загрузки фото")
async def cancel_photo_upload_handler(message: Message):
    user_id = session_user_ids.get(message.from_user.id)
    if not user_id or user_id not in uploading_profile_photos:
        return
    uploading_profile_photos.discard(user_id)
    await message.answer("Загрузка фото отменена.", reply_markup=feed_keyboard)


@dp.message(lambda message: message.text == "✅ Сохранить")
async def save_profile_edit_handler(message: Message):
    user_id = session_user_ids.get(message.from_user.id)
    if not user_id or user_id not in profile_edit_drafts:
        return
    payload = profile_edit_drafts.get(user_id, {})
    if not payload:
        await message.answer("Нет изменений для сохранения.", reply_markup=edit_profile_keyboard)
        return

    try:
        updated = await update_my_profile(user_id, payload)
        if not updated:
            await message.answer("Профиль не найден или не удалось обновить.", reply_markup=feed_keyboard)
            close_edit_session(user_id)
            return
        close_edit_session(user_id)
        await message.answer("Профиль обновлен.", reply_markup=feed_keyboard)
    except aiohttp.ClientError:
        await message.answer("Ошибка при обновлении профиля.", reply_markup=edit_profile_keyboard)


@dp.message(lambda message: message.text == "❌ Отмена")
async def cancel_profile_edit_handler(message: Message):
    user_id = session_user_ids.get(message.from_user.id)
    if not user_id or user_id not in profile_edit_drafts:
        return
    close_edit_session(user_id)
    await message.answer("Редактирование отменено.", reply_markup=feed_keyboard)


@dp.message(lambda message: message.text is not None)
async def profile_edit_value_handler(message: Message):
    telegram_id = message.from_user.id
    user_id = session_user_ids.get(telegram_id)
    if not user_id or user_id not in profile_edit_drafts:
        return
    field = awaiting_profile_field.get(user_id)
    if not field:
        await message.answer(
            "Сначала выбери поле в окне редактирования, затем отправь значение.",
            reply_markup=edit_profile_keyboard,
        )
        return

    raw_value = (message.text or "").strip()
    draft = profile_edit_drafts[user_id]
    try:
        if field in {"age", "preferred_age_min", "preferred_age_max"}:
            draft[field] = int(raw_value)
        elif field == "delete_photo":
            if not raw_value.isdigit():
                await message.answer("Введи номер фото из списка (число).")
                return
            photo_key = int(raw_value)
            photo_id = pending_photo_delete_map.get(user_id, {}).get(photo_key)
            if not photo_id:
                await message.answer("Номер фото не найден. Отправь номер из списка.")
                return
            deleted, error_details = await delete_profile_photo(user_id, photo_id)
            if not deleted:
                await message.answer(f"Не удалось удалить фото. Детали API: {error_details}")
                return
            pending_photo_delete_map.pop(user_id, None)
            await message.answer("Фото удалено.")
        elif field in {"preferred_city", "preferred_gender"}:
            draft[field] = None if raw_value == "-" else raw_value
        else:
            draft[field] = raw_value
    except ValueError:
        await message.answer("Некорректный формат числа. Попробуй еще раз.")
        return

    awaiting_profile_field.pop(user_id, None)
    if field == "delete_photo":
        await message.answer(
            "Фото удалено. Можешь удалить еще одно фото или продолжить редактирование.",
            reply_markup=edit_profile_keyboard,
        )
        return

    if field in {"preferred_age_min", "preferred_age_max", "preferred_city", "preferred_gender"}:
        await message.answer(
            "Предпочтение обновлено в черновике. Можешь изменить другие предпочтения.",
            reply_markup=preferences_edit_keyboard,
        )
        return

    await message.answer(
        "Изменение добавлено в черновик. Выбери следующее поле или нажми «Сохранить».",
        reply_markup=edit_profile_keyboard,
    )


@dp.message(lambda message: message.photo)
async def upload_photo_handler(message: Message):
    user_id = await ensure_user_id(message.from_user.id)
    if not user_id or user_id not in uploading_profile_photos:
        return
    if not message.photo:
        return

    file_id = message.photo[-1].file_id
    try:
        attached, error_details = await attach_profile_photo(user_id, file_id)
        if not attached:
            await message.answer(
                f"Не удалось прикрепить фото. Попробуй еще раз.\n"
                f"Детали API: {error_details}"
            )
            return
        await message.answer("Фото добавлено к анкете.", reply_markup=photo_upload_keyboard)
    except Exception as exc:
        await message.answer(
            f"Ошибка при загрузке фото.\n{type(exc).__name__}: {exc}",
            reply_markup=photo_upload_keyboard,
        )


async def main():
    while True:
        try:
            await dp.start_polling(bot)
            break
        except TelegramNetworkError as exc:
            print(f"Telegram network error: {exc}. Retrying in 5 seconds...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
