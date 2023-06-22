import asyncio
import html
import json
import logging
import os
import tempfile
import time
import traceback
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import List

import database
import long_term
import memory
import openai_utils
import pydub
import telegram
import voice_clone
from telegram import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Update,
    User,
)
from telegram.constants import ParseMode
from telegram.ext import (
    AIORateLimiter,
    Application,
    ApplicationBuilder,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

import config

# setup

db: database.Database = database.Database()
logger = logging.getLogger(__name__)
voice_clone = voice_clone.VoiceClone()
user_semaphores: dict = {}
user_tasks: dict = {}
bot_memory: memory.Memory = memory.Memory()
long_term_memory: long_term.LongTermMemory = long_term.LongTermMemory()

HELP_MESSAGE = """Commands:
⚪ /mode – Select chat mode
⚪ /delete_memory – Clear memory of our last 10 messages. Keep in mind that I will not remember those conversations once deleted
⚪ /deposit – Add credits to you account
⚪ /balance – Show balance
⚪ /help – Show help
⚪ /policy – view our Terms of Use & Privacy Policy

🎤 You can send <b>Voice Messages</b> instead of text

Please select chat mode, default to sweet mode.
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


async def register_user_if_not_exists(user: User) -> None:
    if not (await db.check_if_user_exists(user_id=user.id)):
        await db.add_new_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )
        bot_memory.create_dialog(user.id)

    if user.id not in user_semaphores:
        user_semaphores[user.id] = asyncio.Semaphore(1)


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


async def is_previous_message_not_answered_yet(user_id):
    await user_semaphores[user_id].acquire()
    user_semaphores[user_id].release()


def createButton(amounts: list):
    return [
        InlineKeyboardButton(x, callback_data=f"deposit|{x}", pay=True) for x in amounts
    ]


async def deposit_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update.message.from_user)

    reply_text = "Please choose the amount you want to deposit. For reference, 600 tokens cost $1.\n\n"

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
        provider_token=config.stripe_token,
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

    await db.increase_remaining_tokens(
        user_id=user_id,
        tokens_added=successful_payment.total_amount
        * 6,  # 1 dollar == total amount 100, each dollar 600 tokens
    )

    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="Thanks for your purchase!"
    )


async def start_handle(update: Update, context: CallbackContext) -> None:
    await register_user_if_not_exists(update.message.from_user)
    user: User = update.message.from_user

    reply_text = f"Hey <b>{user.first_name}</b> here, how are you doing?\n\n"
    reply_text += HELP_MESSAGE
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=reply_text, parse_mode=ParseMode.HTML
    )
    await show_chat_modes_handle(update, context)


async def help_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update.message.from_user)
    await update.message.reply_text(HELP_MESSAGE, parse_mode=ParseMode.HTML)

async def policy_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update.message.from_user)
    await update.message.reply_text(config.policy, parse_mode=ParseMode.HTML)

async def delete_memory_handle(update: Update, context: CallbackContext):
    user = update.message.from_user
    await register_user_if_not_exists(user)
    async with user_semaphores[user.id]:
        bot_memory.delete_memory(user_id=user.id)
        
async def help_group_chat_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update.message.from_user)

    text = HELP_GROUP_CHAT_MESSAGE.format(bot_username="@" + context.bot.username)

    await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    await update.message.reply_video(config.help_group_chat_video_path)


async def message_handle(update: Update, context: CallbackContext, message=None):
    # check if bot was mentioned (for group chats)
    functionStartTime = time.perf_counter()
    if not await is_bot_mentioned(update, context):
        return

    message_obj = update.edited_message or update.message
    incoming_message: str = message or message_obj.text

    # remove bot mention (in group chats)
    if message_obj.chat.type != "private":
        incoming_message = incoming_message.replace(
            "@" + context.bot.username, ""
        ).strip()

    user_id: int = message_obj.from_user.id

    await register_user_if_not_exists(message_obj.from_user)

    async def message_handle_fn():
        chat_mode: str | None = bot_memory.get_chat_mode(user_id=user_id)
        dialog_info = bot_memory.get_dialog(user_id)
        dialog_messages, dialog_start_time, dialog_chat_mode = (
            dialog_info["messages"],
            dialog_info["start_time"],
            dialog_info["chat_mode"],
        )

        dialog_messages: str = dialog_messages
        dialog_start_time: datetime = dialog_start_time
        dialog_chat_mode: str = dialog_chat_mode
        # new dialog timeout
        # TODO delete dialog,  when reset write to pinecone
        if len(dialog_messages) > 8192:
            long_term_memory.add_text(user_id,bot_memory.reset_dialog(user_id=user_id),2048)

        n_input_tokens, n_output_tokens = 0, 0
        if await db.get_remaining_tokens(user_id=user_id) <= 0:
            await message_obj.reply_text(
                text="You have no remaining tokens. Please type /deposit to add more tokens."
            )
            return
        try:  # in case of CancelledError
            # send use that action showing bot is talking and recording audio
            to_delete = await message_obj.reply_text(text="...")
            await message_obj.chat.send_action(action="record_audio")

            if incoming_message is None or len(incoming_message) == 0:
                # TODO - Change this to voice response
                await message_obj.reply_text(
                    "🥲 You sent <b>empty message</b>. Please, try again!",
                    parse_mode=ParseMode.HTML,
                )
                return

            openAIStartTime = time.perf_counter()
            chatgpt_instance = openai_utils.ChatGPT()
            openAIActualCallStartTime = time.perf_counter()
            # take last 150 char + incoming messages as query to have more relevant similarity search results
            similarity_search_query = dialog_messages[-150:] + incoming_message

            previous_conv = (
                "OUR HISTORY CONVERSATION:\n\n"
                + await long_term_memory.similarity_search(
                    user_namespace=user_id, query=similarity_search_query, topK=2
                )
            )

            celerity_background = (
                "YOUR BACKGOUND:\n\n"
                + await long_term_memory.similarity_search(
                    user_namespace=config.celebrity_namespace,
                    query=similarity_search_query,
                    topK=1,
            ))
            toChatGPT = "".join([celerity_background
                        ,previous_conv
                        , "OUR RECENT CONVERSATION THAT MATTERS THE MOST: \n\n"
                        , dialog_messages])
            for i in range(1, 4):
                try:
                    (
                        answer,
                        (n_input_tokens, n_output_tokens),
                        not_used,
                    ) = await chatgpt_instance.send_message(
                        incoming_message,
                        dialog_messages=toChatGPT,
                        chat_mode=chat_mode,
                    )
                    break
                except Exception as error:
                    logger.error(
                        msg=f"OpenAI send_message error: {error}, retry times:{i}"
                    )
            else:
                raise NameError("OpenAI send_message fails 3 times")
            openAIActualCallEndTime = time.perf_counter()
            logger.error(
                msg=f"OpenAI actual call elapsed time: {openAIActualCallEndTime-openAIActualCallStartTime} seconds."
            )

            answer = answer[:4096]  # telegram message limit
            openAIEndTime = time.perf_counter()
            logger.error(
                msg=f"OpenAI elapsed time: {openAIEndTime-openAIStartTime} seconds."
            )

            # update user data
            bot_memory.add_message(
                user_id=user_id, human_message=incoming_message, bot_response=answer
            )
            await db.update_n_used_tokens(
                user_id=user_id,
                n_input_tokens=n_input_tokens,
                n_output_tokens=n_output_tokens,
            )

            try:
                start_time = time.perf_counter()
                audio_data: bytes = await voice_clone.generateVoice(text=answer)
                end_time = time.perf_counter()
                logger.error(
                    msg=f"11 labs elapsed time: {end_time-start_time} seconds."
                )
                audio_file = BytesIO(audio_data)
                audio_file.name = "output.ogg"
                current_chat_id = update.effective_chat.id
                if current_chat_id is None:
                    logger.critical(f"Current chat id is None. Update: {update}")

                await context.bot.send_voice(chat_id=current_chat_id, voice=audio_file)
                await context.bot.delete_message(
                    chat_id=current_chat_id, message_id=to_delete.message_id
                )
                functionEndTime = time.perf_counter()
                logger.error(
                    msg=f"Function elapsed time: {functionEndTime-functionStartTime} seconds."
                )
            except telegram.error.BadRequest as error:
                if str(error).startswith("Message is not modified"):
                    logger.critical(msg=f"bad request error with {error}.")
                else:
                    logger.critical(msg=f"bad request erroer with {error}.")
                    await context.bot.send_message(
                        current_chat_id,
                        "Something went wrong, please try again.",
                        parse_mode=ParseMode.HTML,
                    )

        except Exception as error:
            error_text = (
                f"Something went wrong during completion in message_fn. Reason: {error}"
            )
            logger.critical(error_text)
            await message_obj.reply_text(
                "Hey there, something went wrong. Please try again."
            )

    async with user_semaphores[user_id]:
        task = asyncio.create_task(coro=message_handle_fn())
        user_tasks[user_id] = task

        try:
            await task
        except asyncio.CancelledError:
            await message_obj.reply_text(text="✅ Canceled", parse_mode=ParseMode.HTML)
        else:
            pass
        finally:
            if user_id in user_tasks:
                del user_tasks[user_id]


async def voice_message_handle(update: Update, context: CallbackContext):
    # check if bot was mentioned (for group chats)
    if not await is_bot_mentioned(update, context):
        return

    await register_user_if_not_exists(update.message.from_user)

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

    await message_handle(update, context, message=transcribed_text)


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
    await register_user_if_not_exists(update.message.from_user)
    await is_previous_message_not_answered_yet(update.message.from_user.id)

    text, reply_markup = get_chat_mode_menu(0)
    await update.message.reply_text(
        text, reply_markup=reply_markup, parse_mode=ParseMode.HTML
    )


async def show_chat_modes_callback_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update.callback_query.from_user)
    await is_previous_message_not_answered_yet(update.message.from_user.id)

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
    await register_user_if_not_exists(update.callback_query.from_user)
    user_id = update.callback_query.from_user.id

    query = update.callback_query
    await query.answer()

    chat_mode = query.data.split("|")[1]
    bot_memory.set_chat_mode(user_id, chat_mode)

    await context.bot.send_message(
        update.callback_query.message.chat.id,
        f"{config.chat_modes[chat_mode]['welcome_message']}",
        parse_mode=ParseMode.HTML,
    )


async def show_balance_handle(update: Update, context: CallbackContext):
    """return n_remaining_output_tokens tokens for the user"""
    await register_user_if_not_exists(update.message.from_user)

    remaining_token = await db.get_remaining_tokens(update.message.from_user.id)
    await update.message.reply_text(
        text=f"<b>{remaining_token}</b> tokens are still available in your account! Need more? Just type <code>/deposit</code> to top up.",
        parse_mode=ParseMode.HTML,
    )


async def error_handle(update: Update, context: CallbackContext) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    if not update:
        return
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
    except Exception as error:
        error_text = f"Something went wrong during completion. Reason: {error}, update: {update}, context: {context}"
        logger.error(error_text)


async def post_init(application: Application):
    await application.bot.set_my_commands(
        [
            BotCommand("/mode", "Select chat mode"),
            BotCommand("/delete_memory", "Clear memory of our last 10 messages. Keep in mind that I will not remember those conversations once deleted"),
            BotCommand("/balance", "Show balance"),
            BotCommand("/deposit", "deposit to your account"),
            BotCommand("/help", "Show help message"),
            BotCommand("/policy", "view our Terms of Use & Privacy Policy"),
        ]
    )


def run_bot() -> None:
    application = (
        ApplicationBuilder()
        .token(config.telegram_token)
        .concurrent_updates(True)
        .rate_limiter(AIORateLimiter(max_retries=5))
        .post_init(post_init)
        .read_timeout(30)
        .write_timeout(30)
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
    application.add_handler(CommandHandler("policy", policy_handle, filters=user_filter))
    application.add_handler(CommandHandler("delete_memory", delete_memory_handle, filters=user_filter))
    application.add_handler(
        CommandHandler("help_group_chat", help_group_chat_handle, filters=user_filter)
    )

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND & user_filter, message_handle)
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
