import os
import logging
import asyncio
import traceback
import html
import json
import tempfile
from pathlib import Path
import pydub
from datetime import datetime
import openai
from io import BytesIO
import time

import telegram
from telegram import (
    Update,
    User,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
    LabeledPrice,
)
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackContext,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    AIORateLimiter,
    filters,
    PreCheckoutQueryHandler,
)
from telegram.constants import ParseMode

import database
import voice_clone
import openai_utils
import config


# setup
db = database.Database()
logger = logging.getLogger(__name__)
voice_clone = voice_clone.VoiceClone()
user_semaphores: dict = {}
user_tasks: dict = {}

HELP_MESSAGE = """Commands:
⚪ /retry – Regenerate last bot answer
⚪ /new – Start new dialog
⚪ /mode – Select chat mode
⚪ /balance – Show balance
⚪ /help – Show help
⚪ /deposit – Add credits to you account

🎤 You can send <b>Voice Messages</b> instead of text
"""

HELP_GROUP_CHAT_MESSAGE = """You can add bot to any <b>group chat</b> to help and entertain its participants!

Instructions (see <b>video</b> below):
1. Add the bot to the group chat
2. Make it an <b>admin</b>, so that it can see messages (all other rights can be restricted)
3. You're awesome!

To get a reply from the bot in the chat – @ <b>tag</b> it or <b>reply</b> to its message.
For example: "{bot_username} write a poem about Telegram"
"""


def split_text_into_chunks(text, chunk_size):
    for i in range(0, len(text), chunk_size):
        yield text[i : i + chunk_size]


async def register_user_if_not_exists(
    update: Update, context: CallbackContext, user: User
) -> None:
    if not db.check_if_user_exists(user.id):
        db.add_new_user(
            user_id=user.id,
            chat_id=update.message.chat_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )
        db.start_new_dialog(user.id)

    if db.get_user_attribute(user.id, "current_dialog_id") is None:
        db.start_new_dialog(user.id)

    if user.id not in user_semaphores:
        user_semaphores[user.id] = asyncio.Semaphore(1)

    if db.get_user_attribute(user.id, "current_model") is None:
        db.set_user_attribute(
            user.id, "current_model", config.models["available_text_models"][0]
        )

    # voice message transcription
    if db.get_user_attribute(user.id, "n_transcribed_seconds") is None:
        db.set_user_attribute(user.id, "n_transcribed_seconds", 0.0)

    # image generation
    if db.get_user_attribute(user.id, "n_generated_images") is None:
        db.set_user_attribute(user.id, "n_generated_images", 0)


async def is_bot_mentioned(update: Update, context: CallbackContext) -> bool:
    try:
        message = update.message

        if message.chat.type == "private":
            return True

        if message.text is not None and ("@" + context.bot.username) in message.text:
            return True

        if message.reply_to_message is not None:
            if message.reply_to_message.from_user.id == context.bot.id:
                return True
    except:
        return True
    else:
        return False


def createButton(amounts: list):
    return [
        InlineKeyboardButton(x, callback_data=f"deposit|{x}", pay=True) for x in amounts
    ]


async def deposit_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)

    user_id = update.message.from_user.id
    reply_text = "Please choose the amount you want to deposit. For reference, 300 tokens cost $1.\n\n"

    invoice_choice = []
    invoice_choice.append(createButton(["5", "10", "30"]))
    invoice_choice.append(createButton(["60", "100", "250"]))
    invoice_choice.append(createButton(["500"]))

    reply_markup = InlineKeyboardMarkup(invoice_choice)
    await update.message.reply_text(
        reply_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML
    )


async def send_invoice_handle(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    invoice_amount = query.data.split("|")[1]
    await context.bot.sendInvoice(
        query.message.chat_id,
        title="Deposit",
        description=f"deposit {invoice_amount} USD to your account",
        payload="unique invoice id",
        provider_token=config.stripe_token_live,
        # provider_token=config.stripe_token_test,
        currency="USD",
        prices=[
            LabeledPrice(
                label=f"{invoice_amount} mins of usage",
                amount=int(invoice_amount) * 100,
            )
        ],
    )


async def pre_checkout_query_handle(update: Update, context: CallbackContext):
    query = update.pre_checkout_query
    await context.bot.answer_pre_checkout_query(query.id, True)


async def successful_payment_handle(update: Update, context: CallbackContext):
    """
    this method is called when a successful payment has been made,
    We increase available tokens of the user corresponding to the amount paid
    """
    successful_payment = update.message.successful_payment
    user_id: int = update.message.from_user.id
    current_model: str = db.get_user_attribute(user_id=user_id, key="current_model")

    db.increase_remaining_tokens(
        user_id,
        current_model,
        successful_payment.total_amount
        * 3,  # 1 dollar == total amount 100, each dollar 300 tokens
    )

    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="Thanks for your purchase!"
    )


async def start_handle(update: Update, context: CallbackContext) -> None:
    await register_user_if_not_exists(update, context, update.message.from_user)
    user = update.message.from_user
    user_id = user.id
    username = user.first_name

    db.set_user_attribute(user_id, "last_interaction", datetime.now())
    db.start_new_dialog(user_id)

    reply_text = f"Hey <b>{username}</b> here, how are you doing?\n\n"
    reply_text += HELP_MESSAGE
    await update.message.reply_text(reply_text, parse_mode=ParseMode.HTML)
    await show_chat_modes_handle(update, context)


async def help_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)
    user_id = update.message.from_user.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())
    await update.message.reply_text(HELP_MESSAGE, parse_mode=ParseMode.HTML)


async def help_group_chat_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)
    user_id = update.message.from_user.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())

    text = HELP_GROUP_CHAT_MESSAGE.format(bot_username="@" + context.bot.username)

    await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    await update.message.reply_video(config.help_group_chat_video_path)


async def retry_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)
    if await is_previous_message_not_answered_yet(update, context):
        return

    user_id = update.message.from_user.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())

    dialog_messages = db.get_dialog_messages(user_id, dialog_id=None)
    if len(dialog_messages) == 0:
        await update.message.reply_text("No message to retry 🤷‍♂️")
        return

    last_dialog_message = dialog_messages.pop()
    db.set_dialog_messages(
        user_id, dialog_messages, dialog_id=None
    )  # last message was removed from the context

    await message_handle(
        update,
        context,
        message=last_dialog_message["user"],
        use_new_dialog_timeout=False,
    )


async def message_handle(
    update: Update, context: CallbackContext, message=None, use_new_dialog_timeout=True
):
    # check if bot was mentioned (for group chats)
    functionStartTime = time.perf_counter()
    if not await is_bot_mentioned(update, context):
        return

    # check if message is edited
    if update.edited_message is not None:
        await edited_message_handle(update, context)
        return

    _message = message or update.message.text

    # remove bot mention (in group chats)
    if update.message.chat.type != "private":
        _message = _message.replace("@" + context.bot.username, "").strip()

    await register_user_if_not_exists(update, context, update.message.from_user)
    if await is_previous_message_not_answered_yet(update, context):
        return

    user_id: int = update.message.from_user.id
    chat_mode: str | None = db.get_user_attribute(
        user_id=user_id, key="current_chat_mode"
    )

    if chat_mode == "artist":
        await generate_image_handle(update, context, message=message)
        return

    async def message_handle_fn():
        # new dialog timeout
        if use_new_dialog_timeout:
            if (
                datetime.now() - db.get_user_attribute(user_id, "last_interaction")
            ).seconds > config.new_dialog_timeout and len(
                db.get_dialog_messages(user_id)
            ) > 0:
                db.start_new_dialog(user_id)
                await update.message.reply_text(
                    f"Starting new dialog due to timeout (<b>{config.chat_modes[chat_mode]['name']}</b> mode) ✅",
                    parse_mode=ParseMode.HTML,
                )
        db.set_user_attribute(user_id, "last_interaction", datetime.now())

        n_input_tokens, n_output_tokens = 0, 0
        current_model: str | None = db.get_user_attribute(user_id, key="current_model")
        remaining_tokens: int = db.get_remaining_tokens(user_id=user_id)
        print("remaining token:" + str(remaining_tokens))
        if (remaining_tokens) <= 0:
            await update.message.reply_text(
                text="You have no remaining tokens. Please type /deposit to add more tokens."
            )
            return
        try:  # in case of CancelledError
            # send placeholder message to user
            placeholder_message = await update.message.reply_text("...")

            # send typing action
            await update.message.chat.send_action(action="typing")

            if _message is None or len(_message) == 0:
                # TODO - Change this to voice response
                await update.message.reply_text(
                    "🥲 You sent <b>empty message</b>. Please, try again!",
                    parse_mode=ParseMode.HTML,
                )
                return

            dialog_messages = db.get_dialog_messages(user_id, dialog_id=None)
            parse_mode = {"html": ParseMode.HTML, "markdown": ParseMode.MARKDOWN}[
                config.chat_modes[chat_mode]["parse_mode"]
            ]
            openAIStartTime = time.perf_counter()
            chatgpt_instance = openai_utils.ChatGPT(model=current_model)

            if config.enable_message_streaming:
                gen = chatgpt_instance.send_message_stream(
                    _message, dialog_messages=dialog_messages, chat_mode=chat_mode
                )
            else:
                openAIActualCallStartTime = time.perf_counter()
                (
                    answer,
                    (n_input_tokens, n_output_tokens),
                    n_first_dialog_messages_removed,
                ) = await chatgpt_instance.send_message(
                    _message,
                    dialog_messages=dialog_messages,
                    chat_mode=chat_mode,
                )
                openAIActualCallEndTime = time.perf_counter()
                print(
                    f"OpenAI actual call elapsed time: {openAIActualCallEndTime-openAIActualCallStartTime} seconds."
                )

                async def fake_gen():
                    yield "finished", answer, (
                        n_input_tokens,
                        n_output_tokens,
                    ), n_first_dialog_messages_removed

                gen = fake_gen()

            prev_answer = ""
            async for gen_item in gen:
                (
                    status,
                    answer,
                    (n_input_tokens, n_output_tokens),
                    n_first_dialog_messages_removed,
                ) = gen_item

                answer = answer[:4096]  # telegram message limit

                # update only when 100 new symbols are ready
                if abs(len(answer) - len(prev_answer)) < 100 and status != "finished":
                    continue

                # try:
                #     await context.bot.edit_message_text(
                #         answer,
                #         chat_id=placeholder_message.chat_id,
                #         message_id=placeholder_message.message_id,
                #         parse_mode=parse_mode,
                #     )
                # except telegram.error.BadRequest as e:
                #     if str(e).startswith("Message is not modified"):
                #         continue
                #     else:
                #         await context.bot.edit_message_text(
                #             answer,
                #             chat_id=placeholder_message.chat_id,
                #             message_id=placeholder_message.message_id,
                #         )

                await asyncio.sleep(0.01)  # wait a bit to avoid flooding

                prev_answer = answer
            openAIEndTime = time.perf_counter()
            print(f"OpenAI elapsed time: {openAIEndTime-openAIStartTime} seconds.")
            # update user data
            new_dialog_message = {
                "user": _message,
                "bot": answer,
                "date": datetime.now(),
            }
            db.set_dialog_messages(
                user_id,
                db.get_dialog_messages(user_id, dialog_id=None) + [new_dialog_message],
                dialog_id=None,
            )

            remaining_token: int = db.update_n_used_tokens(
                user_id=user_id,
                model=current_model,
                n_input_tokens=n_input_tokens,
                n_output_tokens=n_output_tokens,
            )

            try:
                start_time = time.perf_counter()
                audio_data: bytes = await voice_clone.generateVoice(text=answer)
                end_time = time.perf_counter()
                print(f"11 labs elapsed time: {end_time-start_time} seconds.")
                audio_file = BytesIO(audio_data)
                audio_file.name = "output.ogg"
                await context.bot.send_voice(
                    chat_id=placeholder_message.chat_id, voice=audio_file
                )
                # Update Remaining Tokens
                await context.bot.edit_message_text(
                    # answer + "Remaining Token: " + str(remaining_token),       Commenting out because we are not sending text
                    "Remaining Token: " + str(remaining_token),
                    chat_id=placeholder_message.chat_id,
                    message_id=placeholder_message.message_id,
                    parse_mode=parse_mode,
                )
                functionEndTime = time.perf_counter()
                print(
                    f"Function elapsed time: {functionEndTime-functionStartTime} seconds."
                )

            except telegram.error.BadRequest as e:
                if str(e).startswith("Message is not modified"):
                    print(e)
                else:
                    await context.bot.edit_message_text(
                        answer
                        + "Remaining Token: "
                        + str(remaining_token)
                        + "\n"
                        + "bad request"
                        + str(e),
                        chat_id=placeholder_message.chat_id,
                        message_id=placeholder_message.message_id,
                    )

            await asyncio.sleep(0.01)

        except asyncio.CancelledError:
            # note: intermediate token updates only work when enable_message_streaming=True (config.yml)
            db.update_n_used_tokens(
                user_id, current_model, n_input_tokens, n_output_tokens
            )
            raise

        except Exception as e:
            error_text = f"Something went wrong during completion. Reason: {e}"
            logger.error(error_text)
            await update.message.reply_text(error_text)
            return

        # TODO - Say something more human back
        # send message if some messages were removed from the context
        if n_first_dialog_messages_removed > 0:
            if n_first_dialog_messages_removed == 1:
                text = "✍️ <i>Note:</i> Your current dialog is too long, so your <b>first message</b> was removed from the context.\n Send /new command to start new dialog"
            else:
                text = f"✍️ <i>Note:</i> Your current dialog is too long, so <b>{n_first_dialog_messages_removed} first messages</b> were removed from the context.\n Send /new command to start new dialog"
            await update.message.reply_text(text, parse_mode=ParseMode.HTML)

    async with user_semaphores[user_id]:
        task = asyncio.create_task(message_handle_fn())
        user_tasks[user_id] = task

        try:
            await task
        except asyncio.CancelledError:
            await update.message.reply_text("✅ Canceled", parse_mode=ParseMode.HTML)
        else:
            pass
        finally:
            if user_id in user_tasks:
                del user_tasks[user_id]


async def is_previous_message_not_answered_yet(
    update: Update, context: CallbackContext
):
    await register_user_if_not_exists(update, context, update.message.from_user)

    user_id = update.message.from_user.id
    if user_semaphores[user_id].locked():
        text = "⏳ Please <b>wait</b> for a reply to the previous message\n"
        text += "Or you can /cancel it"
        await update.message.reply_text(
            text, reply_to_message_id=update.message.id, parse_mode=ParseMode.HTML
        )
        return True
    else:
        return False


async def voice_message_handle(update: Update, context: CallbackContext):
    # check if bot was mentioned (for group chats)
    if not await is_bot_mentioned(update, context):
        return

    await register_user_if_not_exists(update, context, update.message.from_user)
    if await is_previous_message_not_answered_yet(update, context):
        return

    user_id = update.message.from_user.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())

    voice = update.message.voice
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir = Path(tmp_dir)
        voice_ogg_path = tmp_dir / "voice.ogg"

        # download
        voice_file = await context.bot.get_file(voice.file_id)
        await voice_file.download_to_drive(voice_ogg_path)

        # convert to mp3
        voice_mp3_path = tmp_dir / "voice.mp3"
        pydub.AudioSegment.from_file(voice_ogg_path).export(
            voice_mp3_path, format="mp3"
        )

        # transcribe
        with open(voice_mp3_path, "rb") as f:
            transcribed_text = await openai_utils.transcribe_audio(f)

            if transcribed_text is None:
                transcribed_text = ""

    text = f"🎤: <i>{transcribed_text}</i>"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

    # update n_transcribed_seconds
    db.set_user_attribute(
        user_id,
        "n_transcribed_seconds",
        voice.duration + db.get_user_attribute(user_id, "n_transcribed_seconds"),
    )

    await message_handle(update, context, message=transcribed_text)


async def generate_image_handle(update: Update, context: CallbackContext, message=None):
    await register_user_if_not_exists(update, context, update.message.from_user)
    if await is_previous_message_not_answered_yet(update, context):
        return

    user_id = update.message.from_user.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())

    await update.message.chat.send_action(action="upload_photo")

    message = message or update.message.text

    try:
        image_urls = await openai_utils.generate_images(
            message, n_images=config.return_n_generated_images
        )
    except openai.error.InvalidRequestError as e:
        if str(e).startswith(
            "Your request was rejected as a result of our safety system"
        ):
            text = "🥲 Your request <b>doesn't comply</b> with OpenAI's usage policies.\nWhat did you write there, huh?"
            await update.message.reply_text(text, parse_mode=ParseMode.HTML)
            return
        else:
            raise

    # token usage
    db.set_user_attribute(
        user_id,
        "n_generated_images",
        config.return_n_generated_images
        + db.get_user_attribute(user_id, "n_generated_images"),
    )

    for i, image_url in enumerate(image_urls):
        await update.message.chat.send_action(action="upload_photo")
        await update.message.reply_photo(image_url, parse_mode=ParseMode.HTML)


async def new_dialog_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)
    if await is_previous_message_not_answered_yet(update, context):
        return

    user_id = update.message.from_user.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())

    db.start_new_dialog(user_id)
    await update.message.reply_text("Starting new dialog ✅")

    chat_mode = db.get_user_attribute(user_id, "current_chat_mode")
    await update.message.reply_text(
        f"{config.chat_modes[chat_mode]['welcome_message']}", parse_mode=ParseMode.HTML
    )


async def cancel_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)

    user_id = update.message.from_user.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())

    if user_id in user_tasks:
        task = user_tasks[user_id]
        task.cancel()
    else:
        await update.message.reply_text(
            "<i>Nothing to cancel...</i>", parse_mode=ParseMode.HTML
        )


def get_chat_mode_menu(page_index: int):
    n_chat_modes_per_page = config.n_chat_modes_per_page
    text = f"Select <b>chat mode</b> ({len(config.chat_modes)} modes available):"

    # buttons
    chat_mode_keys = list(config.chat_modes.keys())
    page_chat_mode_keys = chat_mode_keys[
        page_index * n_chat_modes_per_page : (page_index + 1) * n_chat_modes_per_page
    ]

    keyboard = []
    for chat_mode_key in page_chat_mode_keys:
        name = config.chat_modes[chat_mode_key]["name"]
        keyboard.append(
            [InlineKeyboardButton(name, callback_data=f"set_chat_mode|{chat_mode_key}")]
        )

    # pagination
    if len(chat_mode_keys) > n_chat_modes_per_page:
        is_first_page = page_index == 0
        is_last_page = (page_index + 1) * n_chat_modes_per_page >= len(chat_mode_keys)

        if is_first_page:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        "»", callback_data=f"show_chat_modes|{page_index + 1}"
                    )
                ]
            )
        elif is_last_page:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        "«", callback_data=f"show_chat_modes|{page_index - 1}"
                    ),
                ]
            )
        else:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        "«", callback_data=f"show_chat_modes|{page_index - 1}"
                    ),
                    InlineKeyboardButton(
                        "»", callback_data=f"show_chat_modes|{page_index + 1}"
                    ),
                ]
            )

    reply_markup = InlineKeyboardMarkup(keyboard)

    return text, reply_markup


async def show_chat_modes_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)
    if await is_previous_message_not_answered_yet(update, context):
        return

    user_id = update.message.from_user.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())

    text, reply_markup = get_chat_mode_menu(0)
    await update.message.reply_text(
        text, reply_markup=reply_markup, parse_mode=ParseMode.HTML
    )


async def show_chat_modes_callback_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(
        update.callback_query, context, update.callback_query.from_user
    )
    if await is_previous_message_not_answered_yet(update.callback_query, context):
        return

    user_id = update.callback_query.from_user.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())

    query = update.callback_query
    await query.answer()

    page_index = int(query.data.split("|")[1])
    if page_index < 0:
        return

    text, reply_markup = get_chat_mode_menu(page_index)
    try:
        await query.edit_message_text(
            text, reply_markup=reply_markup, parse_mode=ParseMode.HTML
        )
    except telegram.error.BadRequest as e:
        if str(e).startswith("Message is not modified"):
            pass


async def set_chat_mode_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(
        update.callback_query, context, update.callback_query.from_user
    )
    user_id = update.callback_query.from_user.id

    query = update.callback_query
    await query.answer()

    chat_mode = query.data.split("|")[1]

    db.set_user_attribute(user_id, "current_chat_mode", chat_mode)
    db.start_new_dialog(user_id)

    await context.bot.send_message(
        update.callback_query.message.chat.id,
        f"{config.chat_modes[chat_mode]['welcome_message']}",
        parse_mode=ParseMode.HTML,
    )


async def show_balance_handle(update: Update, context: CallbackContext):
    """return n_remaining_output_tokens tokens for the user"""
    await register_user_if_not_exists(update, context, update.message.from_user)

    user_id = update.message.from_user.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())

    remaining_token = db.get_remaining_tokens(
        user_id=user_id
    )  # TODO: Remove model and not hardcode
    await update.message.reply_text(
        text="Here are your remaining tokens: " + str(remaining_token),
        parse_mode=ParseMode.HTML,
    )


async def edited_message_handle(update: Update, context: CallbackContext):
    if update.edited_message.chat.type == "private":
        text = "🥲 Unfortunately, message <b>editing</b> is not supported"
        await update.edited_message.reply_text(text, parse_mode=ParseMode.HTML)


async def error_handle(update: Update, context: CallbackContext) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

    try:
        # collect error message
        tb_list = traceback.format_exception(
            None, context.error, context.error.__traceback__
        )
        tb_string = "".join(tb_list)
        update_str = update.to_dict() if isinstance(update, Update) else str(update)
        message = (
            f"An exception was raised while handling an update\n"
            f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
            "</pre>\n\n"
            f"<pre>{html.escape(tb_string)}</pre>"
        )

        # split text into multiple messages due to 4096 character limit
        for message_chunk in split_text_into_chunks(message, 4096):
            try:
                await context.bot.send_message(
                    update.effective_chat.id, message_chunk, parse_mode=ParseMode.HTML
                )
            except telegram.error.BadRequest:
                # answer has invalid characters, so we send it without parse_mode
                await context.bot.send_message(update.effective_chat.id, message_chunk)
    except:
        await context.bot.send_message(
            update.effective_chat.id, "Some error in error handler"
        )


async def post_init(application: Application):
    await application.bot.set_my_commands(
        [
            BotCommand("/new", "Start new dialog"),
            BotCommand("/mode", "Select chat mode"),
            BotCommand("/retry", "Re-generate response for previous query"),
            BotCommand("/balance", "Show balance"),
            BotCommand("/help", "Show help message"),
            BotCommand("/deposit", "deposit to your account"),
        ]
    )


def run_bot() -> None:
    application = (
        ApplicationBuilder()
        .token(config.telegram_token)
        .concurrent_updates(True)
        .rate_limiter(AIORateLimiter(max_retries=5))
        .post_init(post_init)
        .build()
    )

    # add handlers
    user_filter = filters.ALL

    application.add_handler(CommandHandler("start", start_handle, filters=user_filter))

    application.add_handler(
        CommandHandler("deposit", deposit_handle, filters=user_filter)
    )
    application.add_handler(PreCheckoutQueryHandler(pre_checkout_query_handle))
    application.add_handler(
        MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handle)
    )
    application.add_handler(
        CallbackQueryHandler(send_invoice_handle, pattern="^deposit")
    )

    application.add_handler(CommandHandler("help", help_handle, filters=user_filter))
    application.add_handler(
        CommandHandler("help_group_chat", help_group_chat_handle, filters=user_filter)
    )

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND & user_filter, message_handle)
    )
    application.add_handler(CommandHandler("retry", retry_handle, filters=user_filter))
    application.add_handler(
        CommandHandler("new", new_dialog_handle, filters=user_filter)
    )
    application.add_handler(
        CommandHandler("cancel", cancel_handle, filters=user_filter)
    )

    application.add_handler(
        MessageHandler(filters.VOICE & user_filter, voice_message_handle)
    )

    application.add_handler(
        CommandHandler("mode", show_chat_modes_handle, filters=user_filter)
    )
    application.add_handler(
        CallbackQueryHandler(
            show_chat_modes_callback_handle, pattern="^show_chat_modes"
        )
    )
    application.add_handler(
        CallbackQueryHandler(set_chat_mode_handle, pattern="^set_chat_mode")
    )

    application.add_handler(
        CommandHandler("balance", show_balance_handle, filters=user_filter)
    )

    application.add_error_handler(error_handle)

    # start the bot
    application.run_polling()


if __name__ == "__main__":
    run_bot()
