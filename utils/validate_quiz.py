def validate_quiz_data(title: str, questions_data: list):
    if not title or title.strip() == "":
        return False

    if len(questions_data) < 1:
        return False

    for idx, question in enumerate(questions_data):
        if not question.get('content'):
            return False

        answers = question.get('answers', [])
        if len(answers) < 2 or len(answers) > 4:
            return False

        correct_answers = [answer for answer in answers if answer.get('is_correct')]
        if not correct_answers:
            return False

        for ans_idx, answer in enumerate(answers):
            if not answer.get('content'):
                return False
        return True