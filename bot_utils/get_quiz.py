from bot_utils.models import Quiz, Question

def get_quiz_for_guild(guild_id):
    questions = [
        Question("Kto jest Dziedzicem kamienicy w Pierdolnikach?", ["Kornel", "Arek", "Garnek"], 1,10),
        Question("Kto codziennie je drogie łososie?", ["Michał", "Szymon", "Arek"], 2, 10),
        Question("Kto ma jacht?", ["Arek", "Klaudia", "Szymon"], 0,10),
        Question("Kto spał z garnkiem w jednym łóżku?", ["Rudy", "Kornel", "Arek"], 2, 10),
        Question("Kto ślizgał się po brazylijczyku?", ["Arek", "Miłosz", "Dominik"], 0, 10),
    ]
    return Quiz(questions)
