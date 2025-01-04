const addQuestionButton = document.getElementById('addQuestionButton');
const questionsContainer = document.getElementById('questionsContainer');
const saveButton = document.getElementById('saveButton');

document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('#questionsContainer .card').forEach((questionCard) => {
        setupDeleteAnswer(questionCard);
        toggleAddAnswerButton(questionCard);
        imgTransfer(questionCard);
        removeQuestion(questionCard);
        chooseAnswer(questionCard);
        toggleRemoveIconVisibility();
        sliderValue();

        const addAnswerButton = questionCard.querySelector('.add-answer-btn');
        addAnswerButton.addEventListener('click', () => {
            addAnswer(questionCard);
        });

        const removeImageBtn = questionCard.querySelector('.show-image-btn');
        removeImageBtn.addEventListener('click', () => {
            removeImage(questionCard);
        })

    });
})

function createQuestionCard() {
    const questionCard = document.createElement('div');
    questionCard.classList.add('card', 'mb-3', 'border-dark');
    questionCard.innerHTML = `
            <div class="card-body color-l">
                <div class="mb-3">
                    <div class="input-group mb-4">
                        <span class="input-group-text color-m border-dark text-white clickable-icon">
                            <i class="bi bi-image"></i>
                            <input type="file" class="file-input d-none" accept="image/*">
                        </span>
                        
                        <span class="btn color-m border-dark text-white show-image-btn clickable-icon d-none">
                            <i class="bi bi-search text-white"></i>
                        </span>
                        
                        <input type="text" class="form-control color-m border-dark text-white" placeholder="Treść Pytania" maxlength="256">
                        <span class="input-group-text color-m border-dark text-danger clickable-icon delete-icon">
                            <i class="bi bi-trash"></i>
                        </span>
                    </div>

                    <div class="input-group mb-2 border-custom">
                        <input type="text" class="form-control text-white color-m border-dark" placeholder="Treść Odpowiedzi" maxlength="60">
                        <div class="input-group-text text-white color-m border-dark">
                            <input type="checkbox" aria-label="Correct Answer" class="me-2 answer-checkbox">
                            Odpowiedź
                        </div>
                        <span class="input-group-text color-m border-dark text-danger clickable-icon delete-answer-icon">
                            <i class="bi bi-trash"></i>
                        </span>
                    </div>
                    <div class="input-group mb-2 border-custom">
                        <input type="text" class="form-control text-white color-m border-dark" placeholder="Treść Odpowiedzi" maxlength="60">
                        <div class="input-group-text text-white color-m border-dark">
                            <input type="checkbox" aria-label="Correct Answer" class="me-2 answer-checkbox">
                            Odpowiedź
                        </div>
                        <span class="input-group-text color-m border-dark text-danger clickable-icon delete-answer-icon">
                            <i class="bi bi-trash"></i>
                        </span>
                    </div>
                </div>
               
                <div class="d-flex align-items-center mt-2">
                    <span class="btn color-m border-dark text-white mt-2 add-answer-btn clickable-icon">
                        <i class="bi bi-plus"></i> Dodaj odpowiedź
                    </span>
                    <div class="d-flex align-items-center mt-2 ms-2 flex-grow-1">
                        <input type="range" class="form-range answer-range slider" min="5" max="30" value="5">
                        <span class="ms-2 text-white range-value">5</span>
                    </div>
                </div>
            </div>
    `;
    questionsContainer.appendChild(questionCard);

    const addAnswerButton = questionCard.querySelector('.add-answer-btn');
    addAnswerButton.addEventListener('click', () => {
        addAnswer(questionCard);
    });

    setupDeleteAnswer(questionCard);
    toggleAddAnswerButton(questionCard);
    imgTransfer(questionCard);
    removeQuestion(questionCard);
    chooseAnswer(questionCard);
    toggleRemoveIconVisibility();
    sliderValue();

    const removeImageBtn = questionCard.querySelector('.show-image-btn');
    removeImageBtn.addEventListener('click', () => {
        removeImage(questionCard);
    })
}

function addAnswer(questionCard) {
    const answerContainer = questionCard.querySelector('.mb-3');

    const newAnswerGroup = document.createElement('div');
    newAnswerGroup.classList.add('input-group', 'mb-2', 'border-custom');

    newAnswerGroup.innerHTML = `
        <input type="text" class="form-control text-white color-m border-dark" placeholder="Treść Odpowiedzi" maxlength="60">
        <div class="input-group-text text-white color-m border-dark">
            <input type="checkbox" aria-label="Correct Answer" class="me-2 answer-checkbox">
            Odpowiedź
        </div>
        <span class="input-group-text color-m border-dark text-danger clickable-icon delete-answer-icon">
            <i class="bi bi-trash"></i>
        </span>
    `;

    const lastAnswerGroup = answerContainer.querySelector('.input-group.mb-2:last-of-type');

    if (lastAnswerGroup) {
        lastAnswerGroup.after(newAnswerGroup);
    } else {
        answerContainer.prepend(newAnswerGroup);
    }

    chooseAnswer(questionCard);
    toggleAddAnswerButton(questionCard);
    setupDeleteAnswer(questionCard);
}

function setupDeleteAnswer(questionCard) {
    const deleteIcons = questionCard.querySelectorAll('.delete-answer-icon');

    deleteIcons.forEach(icon => {
        icon.addEventListener('click', () => {
            const answerGroups = questionCard.querySelectorAll('.input-group.mb-2');

            if (answerGroups.length > 2) {
                icon.closest('.input-group').remove();
                toggleAddAnswerButton(questionCard);
            }
        });
    });
}

function chooseAnswer(questionCard){
    const checkboxes = questionCard.querySelectorAll('.answer-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', (event) => {
            const inputGroup = event.target.closest('.input-group');

            if (event.target.checked) {
                inputGroup.classList.add('green-border');

                checkboxes.forEach(otherCheckbox => {
                    if (otherCheckbox !== event.target) {
                        otherCheckbox.checked = false;
                        const otherInputGroup = otherCheckbox.closest('.input-group');
                        otherInputGroup.classList.remove('green-border');
                    }
                });
            } else {
                inputGroup.classList.remove('green-border');
            }
        });
    });
}

function removeQuestion(questionCard){
    const deleteButton = questionCard.querySelector('.delete-icon');
    deleteButton.addEventListener('click', () => {
        if (questionsContainer.children.length > 1) {
            questionCard.remove();
        }
        toggleRemoveIconVisibility();
    });
}

function toggleRemoveIconVisibility() {
    const deleteIcons = document.querySelectorAll('.delete-icon');

    if (questionsContainer.children.length <= 1) {
        deleteIcons.forEach(icon => {
            icon.style.display = 'none';
        });
    } else {
        deleteIcons.forEach(icon => {
            icon.style.display = 'inline-block';
        });
    }
}

function imgTransfer(questionCard) {
    const imageIcon = questionCard.querySelector('.clickable-icon');
    const fileInput = questionCard.querySelector('.file-input');
    const showImageBtn = questionCard.querySelector('.show-image-btn');
    const defaultIcon = '<i class="bi bi-search text-white"></i>';
    const hoverIcon = '<i class="bi bi-trash text-danger"></i>';

    const imgUrl = questionCard.dataset.imgUrl;
    if (imgUrl) {
        showImageBtn.classList.remove('d-none');
        showImageBtn.setAttribute(
            'title',
            `<img src="${imgUrl}" class="img-fluid" style="max-width: 200px; max-height: 200px;" />`
        );
        const tooltip = new bootstrap.Tooltip(showImageBtn, {
            html: true,
            placement: 'right',
            trigger: 'hover',
        });
        showImageBtn._tooltip = tooltip;
    } else {
        showImageBtn.classList.add('d-none');
    }

    imageIcon.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', (event) => {
        const file = event.target.files[0];

        if (file) {
            const reader = new FileReader();
            reader.onload = function (e) {
                if (showImageBtn._tooltip) {
                    showImageBtn._tooltip.dispose();
                }

                showImageBtn.classList.remove('d-none');

                showImageBtn.setAttribute(
                    'title',
                    `<img src="${e.target.result}" class="img-fluid" style="max-width: 200px; max-height: 200px;" />`
                );

                const tooltip = new bootstrap.Tooltip(showImageBtn, {
                    html: true,
                    placement: 'right',
                    trigger: 'hover',
                });

                showImageBtn._tooltip = tooltip;
            };

            reader.readAsDataURL(file);
        }
    });

    showImageBtn.addEventListener('mouseenter', () => {
        showImageBtn.innerHTML = hoverIcon;
    });

    showImageBtn.addEventListener('mouseleave', () => {
        showImageBtn.innerHTML = defaultIcon;
    });
}




function removeImage(questionCard) {
    const showImageBtn = questionCard.querySelector('.show-image-btn');
    const fileInput = questionCard.querySelector('.file-input');

    showImageBtn.classList.add('d-none');

    fileInput.value = '';

    if (showImageBtn._tooltip) {
        showImageBtn._tooltip.hide();
    }

    showImageBtn.innerHTML = '<i class="bi bi-search text-white"></i>';
}

function toggleAddAnswerButton(questionCard) {
    const addAnswerButton = questionCard.querySelector('.add-answer-btn');
    const answerGroups = questionCard.querySelectorAll('.input-group.mb-2');

    if (answerGroups.length >= 4) {
        addAnswerButton.style.display = 'none';
    } else {
        addAnswerButton.style.display = 'inline-block';
    }

    if (answerGroups.length <= 2) {
        questionCard.querySelectorAll('.delete-answer-icon').forEach(icon => {
            icon.style.display = 'none';
        });
    } else {
        questionCard.querySelectorAll('.delete-answer-icon').forEach(icon => {
            icon.style.display = 'inline-block';
        });
    }
}

addQuestionButton.addEventListener('click', () => {
    createQuestionCard();
});

function sliderValue(){
    document.querySelectorAll('.answer-range').forEach(rangeInput => {
        const rangeValue = rangeInput.nextElementSibling;

        rangeValue.textContent = rangeInput.value;

        rangeInput.addEventListener('input', () => {
            rangeValue.textContent = rangeInput.value;
        });
    });
}

saveButton.addEventListener('click', () => {
    const quizTitleElement = document.getElementById('quizTitle');
    const quizTitle = quizTitleElement.value;
    const questions = [];
    const formData = new FormData();

    let isValid = true;

    isValid = validateInput(quizTitleElement) && isValid;

    document.querySelectorAll('#questionsContainer .card').forEach((card, index) => {
        const questionInput = card.querySelector('input[type="text"]');
        const fileInput = card.querySelector('.file-input');
        const showImageBtn = card.querySelector('.show-image-btn');
        const imageFile = fileInput.files[0] || null;

        isValid = validateInput(questionInput) && isValid;

        let imageUrl = null;
        if (imageFile) {
            formData.append('files', imageFile);
            imageUrl = `file_${index}`;
        } else if (showImageBtn && !showImageBtn.classList.contains('d-none')) {
            const originalTitle = showImageBtn.getAttribute('data-bs-original-title');
            const imgTagMatch = originalTitle.match(/<img src="([^"]+)"/);
            const fullUrl = imgTagMatch[1];
            const parts = fullUrl.split('/');
            imageUrl = parts[parts.length - 1];
        }

        const answers = [];
        let hasCorrectAnswer = false;

        card.querySelectorAll('.input-group.mb-2').forEach((group) => {
            const answerInput = group.querySelector('input[type="text"]');
            const isCorrect = group.querySelector('input[type="checkbox"]').checked;

            isValid = validateInput(answerInput) && isValid;

            answers.push({ content: answerInput.value.trim(), is_correct: isCorrect });

            if (isCorrect) {
                hasCorrectAnswer = true;
            }
        });

        card.querySelectorAll('.input-group.mb-2').forEach(group => {
                const checkboxDiv = group.querySelector('.input-group-text');
                checkboxDiv.classList.remove('input-error');
            });
        if (!hasCorrectAnswer) {
            isValid = false;
            card.querySelectorAll('.input-group.mb-2').forEach(group => {
                const checkboxDiv = group.querySelector('.input-group-text');
                checkboxDiv.classList.add('input-error');
            });
        }

        const rangeInput = card.querySelector('.form-range');
        const rangeValue = rangeInput ? rangeInput.value : 5;

        if (isValid) {
            questions.push({
                content: questionInput.value.trim(),
                image_url: imageUrl,
                answers: answers,
                time: rangeValue
            });
        }
    });

    if (!isValid) {
        return;
    }

    formData.append('title', quizTitle);
    formData.append('questions', JSON.stringify(questions));

    const quizId = document.getElementById('quizId') ? document.getElementById('quizId').value : null;
    if (quizId) {
        formData.append('quiz_id', quizId);
    }

    fetch('/quiz/add', {
        method: 'POST',
        body: formData,
    })
    .then(response => {
        if (response.ok) {
            alert('Quiz został zapisany!');
        } else {
            alert('Wystąpił błąd podczas zapisu quizu.');
        }
    })
    .catch(error => console.error('Błąd:', error));
});

function validateInput(inputElement) {
    const value = inputElement?.value.trim() || '';
    inputElement?.classList.remove('input-error');

    if (!value) {
        inputElement?.classList.add('input-error');
        return false;
    }
    return true;
}



