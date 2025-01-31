from pydantic import BaseModel, conint


class SettingsModel(BaseModel):
    guild_id: int
    join_window_display_time: conint(ge=5, le=30) = 10
    answer_display_time: conint(ge=5, le=30) = 5
    results_display_time: conint(ge=5, le=30) = 5
    show_results_per_question: bool = True

