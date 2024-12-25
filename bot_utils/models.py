class Quiz:
    def __init__(self, questions):
        self.questions = questions

class Question:
    def __init__(self, text, answers, correct_answer, time_limit=20):
        self.text = text
        self.answers = answers
        self.correct_answer = correct_answer
        self.time_limit = time_limit


