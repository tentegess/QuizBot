let currentPage = 1;

function loadPage(page) {
    currentPage = page;
    const sortOption = document.getElementById('sort-select').value;
    const searchQuery = document.getElementById('search-input').value;

    fetch(`/quiz/data?page=${page}&sort=${sortOption}&search=${encodeURIComponent(searchQuery)}`)
        .then(response => response.json())
        .then(data => {
            const quizList = document.getElementById('quiz-list');
            quizList.innerHTML = '';
            data.quizzes.forEach(quiz => {
                quizList.innerHTML += `
                    <div class="col">
                        <div class="card border-dark color-l" style="border-radius: 0.5rem; overflow: hidden;">
                            <div class="card-body border-0 text-white text-center p-4 color-d" style="border-radius: 0.5rem 0.5rem 0 0;">
                                <h5 class="card-title scalable-text border-0">${quiz.title}</h5>
                            </div>
                            <div class="card-footer color-l2 border-top border-dark text-light text-center" style="border-radius: 0 0 0.5rem 0.5rem;">
                                <p class="mb-0"><strong>Autor</strong></p>
                                <div class="bg-secondary rounded-3 text-center d-inline-block p-1">
                                    <p class="mb-0">${quiz.author}</p>
                                </div>
                                <p class="mb-0">Obejmuje ${quiz.questions} pytań</p>

                                <div class="d-flex justify-content-between align-items-center">
                                    <div class="d-flex gap-3">
                                        <a href="/quiz/view/${quiz._id}" class="text-light clickable-icon" title="Podgląd">
                                            <i class="bi bi-eye"></i>
                                        </a>
                                    ${
                                        quiz.is_editable
                                            ? `<a href="/quiz/edit/${quiz._id}" class="text-light clickable-icon" title="Edycja">
                                                 <i class="bi bi-pencil"></i>
                                               </a>`
                                            : ''
                                    }

                                    </div>
                                    ${
                                        quiz.is_editable
                                            ? `<span class="text-light clickable-icon" title="Usuń" onclick="confirmDelete('${quiz._id}')">
                                                <i class="bi bi-trash text-danger"></i>
                                            </span>`
                                            : ''
                                    }                                    
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            });

            const pagination = document.getElementById('pagination');
            pagination.innerHTML = `
                <nav aria-label="Page navigation">
                    <ul class="pagination color-d">
                        <li class="page-item ${page == 1 ? 'disabled' : ''}">
                            <a class="page-link color-l2" href="#" onclick="loadPage(1)">&laquo;&laquo;</a>
                        </li>
                        <li class="page-item ${page == 1 ? 'disabled' : ''}">
                            <a class="page-link color-l2" href="#" onclick="loadPage(${page - 1})">&laquo;</a>
                        </li>
                        <li class="page-item">
                            <span class="page-link color-d2">Strona ${page} z ${data.total_pages}</span>
                        </li>
                        <li class="page-item ${page == data.total_pages ? 'disabled' : ''}">
                            <a class="page-link color-l2" href="#" onclick="loadPage(${page + 1})">&raquo;</a>
                        </li>
                        <li class="page-item ${page == data.total_pages ? 'disabled' : ''}">
                            <a class="page-link color-l2" href="#" onclick="loadPage(${data.total_pages})">&raquo;&raquo;</a>
                        </li>
                    </ul>
                </nav>
            `;
        });
}

function setupDynamicSearchAndSort() {
    const searchInput = document.getElementById('search-input');
    const sortSelect = document.getElementById('sort-select');

    searchInput.addEventListener('input', () => {
        loadPage(1);
    });

    sortSelect.addEventListener('change', () => {
        loadPage(1);
    });
}

window.onload = function() {
    loadPage(1);
    setupDynamicSearchAndSort();
};

let quizToDelete = null;

function confirmDelete(quizId) {
    quizToDelete = quizId;

    const deleteModal = new bootstrap.Modal(document.getElementById('deleteModal'));
    deleteModal.show();
}

document.getElementById('confirmDeleteButton').addEventListener('click', function() {
    if (quizToDelete) {
        fetch(`/quiz/delete/${quizToDelete}`, {
            method: 'DELETE',
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Nie udało się usunąć quizu.');
            }
        })
        .then(data => {
            const deleteModalElement = document.getElementById('deleteModal');
            const deleteModalInstance = bootstrap.Modal.getInstance(deleteModalElement);
            deleteModalInstance.hide();

            loadPage(currentPage);
        });
    }
});

