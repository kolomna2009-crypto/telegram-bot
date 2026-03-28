from aiogram.fsm.state import State, StatesGroup


class BroadcastState(StatesGroup):
    choosing_category = State()
    waiting_for_message = State()


class GreetingState(StatesGroup):
    waiting_for_text = State()


class AddCategoryState(StatesGroup):
    waiting_for_name = State()
