import base64
import openai

from aiogram import Bot, Dispatcher, executor, types
from datetime import datetime
from io import BytesIO
from math import ceil
from typing import Dict

from const import *
from database import *
from funcs import *
from utils import *

# === TODO ===
# Apis:
# - Reddit
# - Image search
#
# Code:
# - Cut tokens so the model would not overflow
# - Ability to select model (default/in-chat)
# - Admin panel

bot = Bot(config["bot_token"])
dp = Dispatcher(bot)
db = Database()
openai.api_key = config["openai_token"]

selected_chats: Dict[int, int] = {}


@dp.callback_query_handler()
async def callback_handler(query: types.CallbackQuery):
    data = query.data
    if data == "donothing":
        await query.answer()

    elif data.startswith("chatpage"):
        page_id = -1
        try:
            page_id = int(data.split("_")[-1])
        except ValueError:
            await query.answer("Invalid query!")
            return

        all_chats = db.get_chats(query.from_user.id)
        if len(all_chats) == 0:
            await query.message.answer("You have no chats.")
            return
        
        if page_id < 0 or (page_id * 5) >= len(all_chats):
            await query.answer("Invalid page!")
            page_id = 0

        start = page_id * 5
        end = min(len(all_chats), (page_id + 1) * 5)
        cut = all_chats[start:end]
        
        buttons = []
        for chat in cut:
            buttons.append([types.InlineKeyboardButton(chat.title, callback_data=f"chatinfo_{chat.uid}")])
        
        pagination_buttons = [
            types.InlineKeyboardButton("<<", callback_data=f"chatpage_{page_id - 1}") if page_id > 0 else types.InlineKeyboardButton("•", callback_data="donothing"),
            types.InlineKeyboardButton(f"{page_id + 1}/{ceil(len(all_chats) / 5)}", callback_data="donothing"),
            types.InlineKeyboardButton(">>", callback_data=f"chatpage_{page_id + 1}") if end < len(all_chats) else types.InlineKeyboardButton("•", callback_data="donothing")
        ]
        buttons.append(pagination_buttons)
        
        await query.message.edit_reply_markup(reply_markup=types.InlineKeyboardMarkup(inline_keyboard=buttons))

    elif data.startswith("chatinfo"):
        chat_id = -1
        try:
            chat_id = int(data.split("_")[-1])
        except:
            await query.answer("Invalid query!")
            return
        
        chat = db.get_chat(chat_id)
        if chat is None:
            await query.answer("Chat not found!")
            return
        
        if chat.owner != query.from_user.id:
            await query.answer("Access denied!")
            return

        buttons = [
            [types.InlineKeyboardButton("🗑️ Delete", callback_data=f"deletechat_{chat_id}")],
            [types.InlineKeyboardButton("📥 Load", callback_data=f"loadchat_{chat_id}")]
        ]

        await query.message.answer(f"#{chat.uid}\n" + \
                                    f"Chat title: <b>{chat.title}</b>\n" + \
                                    f"Created at <b>{chat.created_at.strftime('%H:%M %d.%m.%Y')}</b>\n" + \
                                    f"Last accessed <b>{chat.last_accessed.strftime('%H:%M %d.%m.%Y')}</b>",
                                    parse_mode="html",
                                    reply_markup=types.InlineKeyboardMarkup(inline_keyboard=buttons))
                                    # TODO: created and accessed at

        selected_chats[query.from_user.id] = chat.uid

    elif data.startswith("deletechat"):
        chat_id = -1
        try:
            chat_id = int(data.split("_")[-1])
        except:
            await query.answer("Invalid query!")
            return
        
        chat = db.get_chat(chat_id)
        if chat is None:
            await query.answer("Chat not found!")
            return
        
        if chat.owner != query.from_user.id:
            await query.answer("Access denied!")
            return
        
        db.delete_chat(chat_id)
        await query.message.edit_text(f"Chat <b>{chat.title}</b> has been successfully deleted", parse_mode="html")

    elif data.startswith("loadchat"):
        chat_id = -1
        try:
            chat_id = int(data.split("_")[-1])
        except:
            await query.answer("Invalid query!")
            return
        
        chat = db.get_chat(chat_id)
        if chat is None:
            await query.answer("Chat not found!")
            return
        
        if chat.owner != query.from_user.id:
            await query.answer("Access denied!")
            return
        
        selected_chats[query.from_user.id] = chat.uid
        await query.message.edit_text(f"Chat <b>{chat.title}</b> has been successfully loaded. Total {len(db.get_messages(chat.uid))} messages", parse_mode="html")


@dp.message_handler(commands=["askweb"])
async def on_askweb(message: types.Message):
    if message.from_id not in config["whitelist"]:
        await message.answer("⚠️ Access denied!")
        return

    split = message.text.split()

    if len(split) < 3:
        await message.answer("❌ Invalid input")

    url = split[1]
    question = " ".join(split[2:])
    new = await message.answer("🧠 Starting generating...")
    result = to_html(await ask_webpage(url, question))
    if len(result) > 3500:
        chunked = chunks(result, 3500)
        await new.edit_text(chunked[0], parse_mode="html")
        for chunk in chunked[1:]:
            await new.answer(chunk, parse_mode="html")
    else:
        await new.edit_text(result, parse_mode="html")


@dp.message_handler(commands=["keyres"])
async def on_keyres(message: types.Message):
    await message.answer("Removing keyboard...", reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(commands=["help"])
async def on_help(message: types.Message):
    text = ""
    for command, description in commands.items():
        text += f"/{command} - {description}\n"
    await message.answer(text)


@dp.message_handler(commands=["start"])
async def on_start(message: types.Message):
    await message.reply("Hello! I'm GPT4 client developed and maintained by @thed1mas")


@dp.message_handler(commands=["delete", "regen"])
async def on_wip(message: types.Message):
    await message.reply("Work in progress!")


@dp.message_handler(commands=["reset"])
async def on_reset(message: types.Message):
    selected_chats.pop(message.from_id, 0)
    await message.reply("Message history has been cleared")


@dp.message_handler(commands=["chats"])
async def on_chats(message: types.Message):
    chats = db.get_chats(message.from_id)
    if len(chats) == 0:
        await message.answer("You have no chats")
        return
    buttons = []
    for chat in chats[:min(5, len(chats))]:
        buttons.append([types.InlineKeyboardButton(chat.title, callback_data=f"chatinfo_{chat.uid}")])
    buttons.append([
        types.InlineKeyboardButton("•", callback_data="donothing"),
        types.InlineKeyboardButton(f"1/{ceil(len(chats)/5)}", callback_data="donothing"),
        types.InlineKeyboardButton(">>", callback_data="chatpage_1") if len(chats) > 5 else types.InlineKeyboardButton("•", callback_data="donothing")
    ])
    await message.answer("Your chats", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=buttons))


@dp.message_handler(commands=["model"])
async def on_model(message: types.Message):
    if message.from_id not in config["whitelist"]:
        await message.answer("⚠️ Access denied!")
        return
    
    if not db.user_exists(message.from_id):
        db.create_user(message.from_id)
    
    user = db.get_user(message.from_id)
    if args := message.get_args():
        if args not in models.keys():
            await message.answer(f"❌ Model <b>{args}</b> not found!", parse_mode="html")
            return
        if not user.has_gpt4 and args.lower() == "gpt-4":
            await message.answer(f"⚠️ You don't have access to <b>{args}</b>!")
            return
        user["model"] = models[args.lower()]
        db.commit()
    else:
        await message.answer(f"🤖 Current model <b>{db.get}</b>" + \
                       f"📃 Available {map(', '.join(lambda s: s.lower(), models.keys()))}")


async def generate_result(message: types.Message, start_prompt: str, level: int = 0, sources: Optional[List[str]] = None, images: Optional[List[str]] = None) -> None:
    user = db.get_user(message.chat.id)
    try:
        sources: List[str] = sources or []
        images: List[str] = images or []
        start = datetime.now()
        response = await openai.ChatCompletion.acreate(
            model=user.model,
            messages=db.get_messages(selected_chats[message.chat.id]),
            max_tokens=2048,
            tools=functions
        )
        spent = str(round((datetime.now() - start).total_seconds(), 2))
        tokens_total = response["usage"]["total_tokens"]
        tokens_prompt = response["usage"]["prompt_tokens"]
        tokens_completion = tokens_total - tokens_prompt
        price = round((tokens_prompt * pricing[user.model][0] + tokens_completion * pricing[user.model][1]) / 1000, 2)
        
        log.success(
            f"Generation of [bold]{truncate_text(start_prompt)}[/] finished. Used [bold]{tokens_total}[/] tokens. Spent [bold]{spent}s[/]")
        
        msg = response["choices"][0]["message"]
        if msg["content"]:
            await message.delete()
            if tokens_completion == 0:
                await message.answer("📭 Model returned nothing (zero-length text)")
            else:
                result = to_html(msg["content"])
                if len(result) > 3500:
                    chunked = chunks(result, 3500)
                    for chunk in chunked:
                        await message.answer(chunk, parse_mode="html", disable_web_page_preview=True)
                else:
                    await message.answer(result, parse_mode="html", disable_web_page_preview=True)

            if len(images) > 0:
                images = list(map(lambda i: types.InputMediaPhoto(i), images))
                await message.answer_media_group(images)
            if len(sources) > 0:
                await message.answer("<b>📜 Sources</b>\n" + \
                                    "\n".join(map(lambda s: f"<a href='{s}'>{parse_domain(s)}</a>", sources)), 
                                    parse_mode="html", disable_web_page_preview=True)

            await message.answer(
                f"📊 Used tokens *{tokens_total}* \(*{tokens_prompt}* prompt, *{tokens_completion}* completion\)\n" + \
                f"⌛ Time spent *{escape(spent)}s*\n" + \
                f"💸 Approximate price: *{escape(price)}$*",
                parse_mode="MarkdownV2")
            
            db.create_message(selected_chats[message.chat.id], "assistant", content=msg["content"])
        elif msg["tool_calls"]:
            calls = msg["tool_calls"]
            db.create_message(selected_chats[message.chat.id], "assistant", tool_calls=calls)
            for call in calls:
                func = call['function']
                args = json.loads(func["arguments"])
                if func["name"] == "add_image":
                    images.append(args["url"])
                    db.create_message(selected_chats[message.chat.id], "tool", content="Done!", call_id=call["id"], function_name="add_image")
                elif func["name"] in py_functions.keys():
                    log.info(f"Calling [bold]{func['name']}[/] with [bold]{func['arguments']}[/]")
                    await message.answer(display_function(func['name'], args), parse_mode="html", disable_web_page_preview=True)
                    if func["name"] == "ask_webpage":
                        sources.append(args["url"])
                    db.create_message(selected_chats[message.chat.id], "tool", 
                                      content=await py_functions[func["name"]](**args), call_id=call["id"], function_name=func["name"])
                else:
                    log.warn(f"GPT tried to call non-existing {func['name']}")
                    await message.answer(f"❌ GPT tried to call non-existing <code>{func['name']}</code>", parse_mode="html")
                    db.create_message(selected_chats[message.chat.id], "tool", content=f"Function {func['name']} not found!", call_id=call["id"], function_name=func["name"])
            await generate_result(message, start_prompt, level+1, sources, images)
        else:
            log.error("Empty message!..")
            return

    except Exception as e:
        log.error(
            f"Caught exception [bold]{type(e).__name__}[/] ({'. '.join(e.args)}) on line [bold]{e.__traceback__.tb_lineno}[/]")
        log.console.print_exception()
        await message.answer(f"❌ Error: `{type(e).__name__} ({'. '.join(e.args)})`", parse_mode="MarkdownV2")


@dp.message_handler(content_types=["text", "photo"])
async def on_message(message: types.Message):
    if message.get_command():
        return

    if message.from_id not in config["whitelist"]:
        await message.answer("⚠️ Access denied!")
        return

    if not db.user_exists(message.from_id):
        db.create_user(message.from_id)

    new = await message.answer("🧠 Starting generating...")
    user = db.get_user(message)

    if len(message.photo):
        if user.model != "gpt-4-turbo":
            await new.edit_text("❌ Images are not supported in this model")
            return
        for photo in message.photo:
            buffer = BytesIO()
            await photo.download(destination_file=buffer)
            img_str = str(base64.b64encode(buffer.getvalue()), encoding="utf8")
            if message.from_id not in selected_chats.keys():
                selected_chats[message.from_id] = db.create_chat(await create_title(message.text or message.caption), message.from_id).uid
            db.create_message(selected_chats[message.from_id], "user",
                              content=[{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_str}"}}])  # TODO: improve code
    
    if message.from_id not in selected_chats.keys():
        selected_chats[message.from_id] = db.create_chat(await create_title(message.text or message.caption), message.from_id).uid
        if system_message is not None:
            db.create_message(selected_chats[message.from_id], "system", content=system_message)

    db.create_message(selected_chats[message.from_id], "user", content = message.text or message.caption)
    log.info(f"Starting generation from [bold]{message.from_user.full_name} ({message.from_id})[/] with prompt [bold]{truncate_text(message.text)}[/]")
    await generate_result(new, message.text)


def main():
    executor.start_polling(dp, skip_updates=True)


if __name__ == "__main__":
    main()
