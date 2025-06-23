import os
import re
import time
import threading
import subprocess
import sys
from pathlib import Path

from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional
from whatsapp_api_client_python import API
from whatsapp_chatbot_python import GreenAPIBot, Notification
from whatsapp_chatbot_python.filters import TEXT_TYPES
from whatsapp_chatgpt_python import WhatsappGptBot
from yaml import safe_load
from users.app_config import BotConfig

from app.bot.internal.GptProcess import GPTProcessingContext
from app.bot.internal.config import load_config, Config
from app.utils.logger import logger
from app.bot.internal.utils import (
    LANGUAGE_CODE_KEY,
    States,
    log_interaction,
    sender_state_data_updater,
    get_first_name, LAST_INTERACTION_KEY, get_state, get_sender_printable, send_lead_to_biz1,
)
bot_config = BotConfig("boti")
RELOAD_INTERVAL = 10

config: Config = load_config(str(bot_config.config_path))

with open(str(bot_config.data_yaml_path), encoding="utf8") as f:
    answers_data = safe_load(f)


prompt = bot_config.prompt_path.read_text(encoding="utf8")

gpt_bot = WhatsappGptBot(
    id_instance=config.user_id,
    api_token_instance=config.api_token_id,
    openai_api_key=config.open_ai_key,
    model="gpt-4o",
    system_message=prompt,
    max_history_length=10,
    temperature=0.7
)


bot = GreenAPIBot(
    config.user_id,
    config.api_token_id,
    settings={
        "webhookUrl": "",
        "webhookUrlToken": "",
        "delaySendMessagesMilliseconds": 200,
        "markIncomingMessagesReaded": "no",
        "incomingWebhook": "yes",
        "keepOnlineStatus": "no",
        "pollMessageWebhook": "yes",
    },
)

green_api = API.GreenAPI(idInstance=config.user_id, apiTokenInstance=config.api_token_id)
executor = ThreadPoolExecutor(max_workers=3)
# Global dictionary to map chatId to (Notification object, timestamp)

waiting_for_message_map = {}
in_chat = {}


@bot.router.message(type_message=TEXT_TYPES, state=None)
@log_interaction(logger=logger)
def initial_handler(notification: Notification) -> None:
    """
    Initial handler for new senders without any state
    """
    # Update sender's state data for chosen language
    if config.answer_only:
        if all(num not in notification.sender for num in config.answer_only):
            return
    
    if any(num in notification.sender for num in config.ignore_numbers):
        logger.info(f"Sender {notification.sender} is in ignore list.")
        return

    hebrew_code = "he"
    sender_first_name = get_first_name(notification.event["senderData"]["senderName"])
    answer_text = (
        f'*{answers_data["welcome_message"][hebrew_code]} {sender_first_name}!* 👋\n'
        f'{answers_data["menu"]["0"][hebrew_code]}'
    )

    set_state_and_answer(
        notification=notification,
        message=answer_text,
        state=States.MENU,
        state_data={
            LANGUAGE_CODE_KEY: hebrew_code,
        },
    )

    # Add notification to the map with current timestamp
    chat_id = notification.event["senderData"]["chatId"]
    waiting_for_message_map[chat_id] = (notification, get_state(notification, LAST_INTERACTION_KEY))  # Store Notification and timestamp

@bot.router.message(
    type_message=TEXT_TYPES,
    text_message=["0"]
)
@log_interaction(logger=logger)
def main_menu_menu_handler(notification: Notification) -> None:
    """
    Menu command handler for senders with `MENU` state.
    Does not change state, just returns menu
    """
    set_state_and_answer(
        notification=notification,
        message=build_message(notification, ['menu', "0"]),
        state=States.MENU
    )


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.MENU.value,
    regexp=r"^\s*([1-6])\s*$",
)
@log_interaction(logger=logger)
def main_menu_generic_handler(notification: Notification) -> None:
    """
    Handles menu options 1–6 for users in MENU state.
    """
    try:
        user_input = notification.message_text.strip()
        match = re.match(r"^\s*([1-6])\s*$", user_input)
        if not match:
            return

        option_number = match.group(1)
        set_state_and_answer(notification=notification,
                             message=build_message(notification, ["menu", option_number]))

    except KeyError as e:
        logger.exception(e)
        return


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.MENU.value,
    regexp=r"^\s*7\s*$",
)
@log_interaction(logger=logger)
def menu_7_handler(notification: Notification) -> None:
    language_code = get_state(notification, LANGUAGE_CODE_KEY)
    set_state_and_answer_poll(
        notification=notification,
        message=build_message(notification, ["menu", "7"]),
        options=[
            answers_data["kids_birthday_intro"][language_code],
            answers_data["adults_birthday_intro"][language_code],
            answers_data["team_event_intro"][language_code],
            answers_data["other_event_intro"][language_code],
        ],
        state=States.MENU_7_CHOICE,
    )


def handle_event_type_poll_response(notification: Notification, text) -> None:
    user_text = text
    language_code = get_state(notification, LANGUAGE_CODE_KEY)

    # Get event introductions from answers_data based on the selected language
    kids_birthday_intro = answers_data["kids_birthday_intro"][language_code]
    adults_birthday_intro = answers_data["adults_birthday_intro"][language_code]
    team_event_intro = answers_data["team_event_intro"][language_code]

    if kids_birthday_intro in user_text:
        set_state_and_answer_poll(
            notification,
            answers_data["kids_birthday_age"][language_code],  # Updated to use answers_data
            answers_data["ages"][language_code],
            States.BIRTHDAY_KIDS_AGE,
        )
    elif adults_birthday_intro in user_text:
        set_state_and_answer_poll(
            notification,
            answers_data["participants_question"][language_code],  # Updated to use answers_data
            answers_data["participants_options"][language_code],
            States.BIRTHDAY_ADULTS_PARTICIPANTS,
        )
    elif team_event_intro in user_text:
        set_state_and_answer_poll(
            notification,
            answers_data["participants_question"][language_code],  # Updated to use answers_data
            answers_data["participants_options"][language_code],
            States.TEAM_BUILDING_PARTICIPANTS,
        )
    else:
        set_state_and_answer_poll(
            notification,
            answers_data["participants_question"][language_code],  # Updated to use answers_data
            answers_data["participants_options"][language_code],
            States.OTHER_EVENT_PARTICIPANTS,
        )


def handle_birthday_kids_1(notification: Notification, text) -> None:
    language_code = get_state(notification, LANGUAGE_CODE_KEY)
    set_state_and_answer_poll(
        notification,
        build_message(notification, ["participants_question"]),
        answers_data["participants_options"][language_code],
        States.BIRTHDAY_KIDS_PARTICIPANTS,
    )


def handle_birthday_kids_2(notification: Notification, text) -> None:
    language_code = get_state(notification, LANGUAGE_CODE_KEY)
    set_state_and_answer_poll(
        notification,
        build_message(notification, ["contact_preference"]),
        [answers_data["send_details_now"][language_code],
         answers_data["prefer_call"][language_code]],
        States.KIDS_MORE_DETAILS,
    )


def handle_birthday_kids_3(notification: Notification, text) -> None:
    language_code = get_state(notification, LANGUAGE_CODE_KEY)
    send_now = answers_data["send_details_now"][language_code]
    
    if send_now in text:  # User opts to receive details via WhatsApp
        for number in config.notify_numbers:
            message = (
                f'{get_sender_printable(notification)}\n'
                f'ביקש פרטים לאירוע ילדים'
            )
            green_api.sending.sendMessage(f"{number}@c.us", message)
    
    set_state_and_answer(notification=notification,
                         message=build_message(notification, ["more_details"]),
                         state=States.KIDS_WAITING_FOR_MORE_DETAILS)
    
    waiting_for_message_map[notification.event["senderData"]["chatId"]] = (notification, get_state(notification, LAST_INTERACTION_KEY))  # Store Notification and timestamp


@bot.router.message(type_message=TEXT_TYPES, state=States.KIDS_WAITING_FOR_MORE_DETAILS.value)
@log_interaction(logger=logger)
def handle_birthday_kids_4(notification: Notification) -> None:
    set_state_and_answer(notification=notification,
                         message=build_message(notification, ["got_it_kids"]),
                         state=States.MENU,
                         link_preview=True)
    
    age = get_state(notification, States.BIRTHDAY_KIDS_AGE.value)
    participant = get_state(notification, States.BIRTHDAY_KIDS_PARTICIPANTS.value)
    text = notification.message_text
    message = f'חוגגים יומולדת{age} עם {participant} משתתפים. הלקוח כתב: {text}'
    send_lead_to_biz1(config.crm_api_token,
                      name=notification.event["senderData"]["senderName"],
                      phone=notification.event["senderData"]["chatId"].split('@')[0],
                      message=message,
                      classification="ימי הולדת"
                      )


def handle_birthday_adults_participants(notification: Notification, text: str) -> None:
    set_state_and_answer(
        notification=notification,
        message=build_message(notification, ["more_info_question"]),
        state=States.BIRTHDAY_ADULTS_MORE_DETAILS,
    )


@bot.router.message(type_message=TEXT_TYPES, state=States.BIRTHDAY_ADULTS_MORE_DETAILS.value)
@bot.router.message(type_message=TEXT_TYPES, state=States.TEAM_MORE_DETAILS.value)
@bot.router.message(type_message=TEXT_TYPES, state=States.OTHER_MORE_DETAILS.value)
@log_interaction(logger=logger)
def handle_birthday_adults_more_details(notification: Notification) -> None:
    state_name = notification.state_manager.get_state(notification.sender).name
    sender_data = notification.event["senderData"]
    phone = sender_data["chatId"].split('@')[0]
    name = sender_data["senderName"]
    user_text = notification.message_text

    formatted_message = ""
    classification = ""
    if state_name == States.BIRTHDAY_ADULTS_MORE_DETAILS.value:
        classification = "פרטיים"
        participants = get_state(notification, States.BIRTHDAY_ADULTS_PARTICIPANTS.value)
        formatted_message = f"חוגגים יום הולדת למבוגרים עם {participants} משתתפים. הלקוח כתב: {user_text}"
    elif state_name == States.TEAM_MORE_DETAILS.value:
        classification = "לקוחות עסקיים"
        participants = get_state(notification, States.TEAM_BUILDING_PARTICIPANTS.value)
        formatted_message = f"יום גיבוש עם {participants} משתתפים. הלקוח כתב: {user_text}"
    elif state_name == States.OTHER_MORE_DETAILS.value:
        classification = "פרטיים"
        participants = get_state(notification, States.OTHER_EVENT_PARTICIPANTS.value)
        formatted_message = f"חוגגים אירוע אחר עם {participants} משתתפים. הלקוח כתב: {user_text}"

    message = (
        f'{get_sender_printable(notification)}\n'
        f' ביקש פרטים לאירוע {classification}'
    )
    if config.notify_on_non_kids_events:
        for number in config.notify_numbers:
            green_api.sending.sendMessage(f"{number}@c.us", message)


    notification.answer(build_message(notification, ["got_it_adults"]))
    set_state_and_answer(  
        notification=notification,
        message=build_message(notification, ["back_to_main_menu"]),
        state=States.MENU,
        link_preview=True
    )

    send_lead_to_biz1(config.crm_api_token,
                      name=name,
                      phone=phone,
                      message=formatted_message,
                      classification=classification
                      )


@bot.router.poll_update_message()
def start_poll_handler(notification: Notification) -> None:
    votes = notification.event["messageData"]["pollMessageData"]["votes"]
    option_name = ""
    for vote_data in votes:
        voters = vote_data["optionVoters"]
        if voters:
            option_name = vote_data["optionName"]

    state_name = notification.state_manager.get_state(notification.sender).name
    notification.state_manager.update_state_data(notification.sender, {state_name: option_name})

    if state_name == States.MENU_7_CHOICE.value:
        notification.answer(option_name)
        handle_event_type_poll_response(notification, option_name)
    elif state_name == States.BIRTHDAY_KIDS_AGE.value:
        notification.answer(option_name)
        handle_birthday_kids_1(notification, option_name)
    elif state_name == States.BIRTHDAY_KIDS_PARTICIPANTS.value:
        notification.answer(option_name)
        handle_birthday_kids_2(notification, option_name)
    elif state_name == States.KIDS_MORE_DETAILS.value:
        notification.answer(option_name)
        handle_birthday_kids_3(notification, option_name)
    elif state_name == States.BIRTHDAY_ADULTS_PARTICIPANTS.value:
        notification.answer(option_name)
        set_state_and_answer(
            notification=notification,
            message=build_message(notification, ["more_details"]),
            state=States.BIRTHDAY_ADULTS_MORE_DETAILS,
            state_data={}
        )
    elif state_name == States.TEAM_BUILDING_PARTICIPANTS.value:
        notification.answer(option_name)
        set_state_and_answer(
            notification=notification,
            message=build_message(notification, ["more_details"]),
            state=States.TEAM_MORE_DETAILS,
        )
    elif state_name == States.OTHER_EVENT_PARTICIPANTS.value:
        notification.answer(option_name)
        set_state_and_answer(
            notification=notification,
            message=build_message(notification, ["more_details"]),
            state=States.OTHER_MORE_DETAILS,
        )
    else:
        answer = (
            f'{build_message(notification, ["choose_updated"])}: '
            f'{option_name}'
        )
        set_state_and_answer(notification, answer)


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.MENU.value,
    regexp=r"^\s*8\s*$",
)
@log_interaction(logger=logger)
def main_menu_8_handler(notification: Notification) -> None:
    """
    Handles menu options 1–8 for users in MENU state.
    """
    if sender_state_data_updater(notification):
        return initial_handler(notification)

    sender = notification.sender
    sender_state_data = notification.state_manager.get_state_data(sender)

    try:
        sender_lang_code = sender_state_data[LANGUAGE_CODE_KEY]
        answer_text = answers_data['ai_terms'][sender_lang_code]
        notification.answer(answer_text, link_preview=False)

        # Use the message from data.yml
        message = answers_data['how_can_i_help'][sender_lang_code]
        notification.answer(message)

        notification.state_manager.update_state(
            notification.sender,
            States.CHAT_GPT.value,
        )

    except KeyError as e:
        logger.exception(e)
        return


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.MENU.value,
    regexp=r"^\s*9\s*$",
)
@log_interaction(logger=logger)
def change_language_handler(notification: Notification) -> None:
    """
    Menu command handler for senders with `MENU` state.
    Does not change state, just returns menu
    """
    language_code = get_state(notification, LANGUAGE_CODE_KEY)
    if language_code == "he":
        language_code = "en"
    else:
        language_code = "he"
    
    set_state_and_answer(notification=notification, 
                        message=answers_data['menu']["0"][language_code],
                        state_data={LANGUAGE_CODE_KEY: language_code})


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.CHAT_GPT.value,
    text_message=["8"]
)
@log_interaction(logger=logger)
def human_request_handler(notification: Notification) -> None:
    """
    Menu command handler for senders with `MENU` state.
    Does not change state, just returns menu
    """

    set_state_and_answer(
        notification=notification,
        message=build_message(notification, ["human_request_message"]),
        state=States.WAITING_FOR_HUMAN_AFTER_CHAT_GPT
    )
    
    try:
        for number in config.notify_numbers:
            message = (
                f'{get_sender_printable(notification)}\n'
                f'{answers_data["human_request_notification"]["he"]}'
            )
            green_api.sending.sendMessage(f"{number}@c.us", message)

    except Exception as e:
        logger.exception(e)

@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.WAITING_FOR_HUMAN_AFTER_CHAT_GPT,
)
@log_interaction(logger=logger)
def human_request_handler(notification: Notification) -> None:
    """
    Menu command handler for senders with `MENU` state.
    Does not change state, just returns menu
    """

    set_state_and_answer(
        notification=notification,
        message=build_message(notification, ["got_it_message_to_human"]),
        state=States.MENU
    )
    

@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.MENU.value,
    regexp=(r"^(?!\s*([0-9])\s*$).*$", re.IGNORECASE)
)
@log_interaction(logger=logger)
def main_menu_incorrect_message_handler(notification: Notification) -> None:
    """
    Handler for senders with `MENU` state.

    Used as helper for any unrecognized
    commands from user just for displaying pretty message
    """
    chat_id = notification.event["senderData"]["chatId"]
    DAY = 24 * 60 * 60
    if chat_id in in_chat and (time.time() - in_chat[chat_id]) < DAY:
        return

    set_state_and_answer(notification=notification,
                         message=build_message(notification, ['invalid_menu_input'])
                         )


# Handle message, which sent from this instance without API
@bot.router.outgoing_message()
def message_handler_outgoing(notification: Notification) -> None:
    chat_id = notification.event["senderData"]["chatId"]
    in_chat[chat_id] = int(time.time())


@bot.router.message(
    state=States.CHAT_GPT.value,
)
@log_interaction(logger=logger)
def chat_gpt_handler(notification: Notification) -> None:
    """
    Handler for messages in the CHAT_GPT state.
    Simply forwards the message to your WhatsappGptBot for processing.
    """
    if sender_state_data_updater(notification):
        return initial_handler(notification)

    sender = notification.sender
    sender_state_data = notification.state_manager.get_state_data(sender)
    message_text = notification.message_text

    try:
        sender_lang_code = sender_state_data[LANGUAGE_CODE_KEY]
    except KeyError as e:
        logger.exception(e)
        return

    if notification.message_text:
        exit_keywords = answers_data["chat_gpt_exit_keywords"].get(sender_lang_code, [])
        if any(keyword.lower() == message_text.lower() for keyword in exit_keywords):
            notification.state_manager.update_state(
                notification.sender,
                States.MENU.value,
            )
            return main_menu_menu_handler(notification)
    
    chat_id = notification.event["senderData"]["chatId"]
    if GPTProcessingContext.is_waiting(chat_id=chat_id):
        notification.answer(build_message(notification, ["already_processing"]),
                            quoted_message_id=notification.get_id_message())
        return
    
    def run_gpt():
        with GPTProcessingContext(chat_id):
            gpt_bot.process_chat_sync(notification)
    
    executor.submit(run_gpt)


def build_message(notification: Notification, keys: List[str]) -> str:
    language_code = get_state(notification, LANGUAGE_CODE_KEY)
    current_dict = answers_data
    for key in keys:
        current_dict = current_dict.get(key)

    return current_dict.get(language_code)

def set_state_and_answer_poll(
    notification: Notification,
    message: str, 
    options: List[str],
    state: States
):
    if sender_state_data_updater(notification):
        return initial_handler(notification)
    
    try:
        notification.state_manager.update_state(notification.sender, state.value)
    except Exception as e:  
        logger.exception(e)

    try:
        poll = []
        for option in options:
            poll.append({"optionName": option})

        notification.answer_with_poll(message, poll)
    except Exception as e:
        logger.exception(e) 


def set_state_and_answer(
    notification: Notification,
    message: str,
    state: States | None = None,
    state_data: dict | None = None,
    link_preview: bool = False
):
    if sender_state_data_updater(notification):
        return initial_handler(notification)
    
    if state:
        notification.state_manager.update_state(notification.sender, state.value)

    if state_data:
        try:
            notification.state_manager.update_state_data(notification.sender, state_data)
        except Exception as e:
            logger.exception(e)

    try:
        notification.answer(message, link_preview=link_preview)
    except Exception as e:
        logger.exception(e)


def check_for_inactive_users():
    """
    This function runs in the background and checks the users waiting for messages.
    If any user has been waiting for more than 2 minutes, a reminder will be sent.
    """
    while True:
        time.sleep(5)  # Check every 5 seconds

        # Loop through the map and check each user's waiting time
        for chat_id, (notification, first_message_ts) in list(waiting_for_message_map.items()):
            try:
                last_interaction_ts = get_state(notification, LAST_INTERACTION_KEY)
                if last_interaction_ts != first_message_ts:
                    del waiting_for_message_map[chat_id]
                    continue

                if time.time() - last_interaction_ts >= config.reminder_timeout:
                    set_state_and_answer(notification, build_message(notification, ["reminder_message"]))
                    del waiting_for_message_map[chat_id]
            except Exception as e:
                logger.exception(e)

def get_mod_time(path: str) -> Optional[float]:
    try:
        return os.path.getmtime(path)
    except Exception as e:
        logger.warning(f"Could not get mtime for {path}: {e}")
        return None


def start_config_watcher(interval: int = RELOAD_INTERVAL):
    params_path = str(bot_config.config_path)
    yaml_data_path = str(bot_config.data_yaml_path)
    last_config_time = get_mod_time(params_path)
    last_data_time = get_mod_time(yaml_data_path)

    def watcher():
        global config, answers_data
        nonlocal last_config_time, last_data_time
        while True:
            time.sleep(interval)
            current_config_time = get_mod_time(params_path)
            current_data_time = get_mod_time(yaml_data_path)

            if current_config_time and current_config_time != last_config_time:
                try:
                    config = load_config(params_path)
                    logger.info("Config reloaded from file.")
                    last_config_time = current_config_time
                except Exception as e:
                    logger.error(f"Failed to reload config: {e}")

            if current_data_time and current_data_time != last_data_time:
                try:
                    with open(yaml_data_path, encoding="utf8") as f:
                        answers_data = safe_load(f)
                    logger.info("answers_data reloaded from YAML.")
                    last_data_time = current_data_time
                except Exception as e:
                    logger.error(f"Failed to reload answers_data: {e}")

    threading.Thread(target=watcher, daemon=True).start()

def main():
    logger.info("Starting WhatsApp Demo Chatbot")
    threading.Thread(target=check_for_inactive_users, daemon=True).start()
    start_config_watcher()
    bot.router.observers["pool"] = bot.router.poll_update_message
    bot.run_forever()

if __name__ == "__main__":
    main()

