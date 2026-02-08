(function() {
    'use strict';

    function getCookie(name) {
        const cookies = document.cookie ? document.cookie.split('; ') : [];
        for (let i = 0; i < cookies.length; i += 1) {
            const parts = cookies[i].split('=');
            const key = decodeURIComponent(parts.shift());
            if (key === name) {
                return decodeURIComponent(parts.join('='));
            }
        }
        return '';
    }

    function refreshEvaluationStructureLists() {
        fetch(window.location.href, { method: 'GET' })
            .then(response => response.text())
            .then(html => {
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');

                const listIds = [
                    'evaluation-forms-list',
                    'evaluation-categories-list',
                    'evaluation-criteria-list',
                    'rubrics-list'
                ];

                let replaced = false;
                listIds.forEach(id => {
                    const current = document.getElementById(id);
                    const updated = doc.getElementById(id);
                    if (current && updated) {
                        current.innerHTML = updated.innerHTML;
                        replaced = true;
                    }
                });

                if (!replaced) {
                    window.location.reload();
                }
            })
            .catch(() => window.location.reload());
    }

    function notify(message, type = 'success') {
        if (window.Swal) {
            Swal.fire({
                toast: true,
                position: 'top-end',
                icon: type,
                title: message,
                showConfirmButton: false,
                timer: 2500,
                timerProgressBar: true,
                background: '#fff'
            });
            return;
        }
        alert(message);
    }

    function submitAjaxForm(form) {
        const modalId = form.dataset.modalId;
        const url = form.action;
        const data = new FormData(form);
        const formId = form.id || '';

        fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: data,
            credentials: 'same-origin',
        })
            .then(response => {
                if (!response.ok) throw new Error('Request failed');
                let message = 'Changes saved successfully.';
                if (formId.startsWith('add')) message = 'Created successfully.';
                if (formId.startsWith('edit')) message = 'Updated successfully.';
                if (formId.startsWith('delete')) message = 'Deleted successfully.';
                notify(message, 'success');
                refreshEvaluationStructureLists();
            })
            .catch(() => notify('Something went wrong. Please try again.', 'error'))
            .finally(() => {
                if (modalId) {
                    hideModal(modalId);
                }
                if (form.id && form.id.startsWith('add')) {
                    form.reset();
                }
            });
    }

    function showModal(modalId) {
        const modal = document.querySelector(modalId);
        if (!modal) return;
        modal.classList.add('show');
        modal.setAttribute('aria-hidden', 'false');
        document.body.classList.add('modal-open');
    }

    function hideModal(modalId) {
        const modal = document.querySelector(modalId);
        if (!modal) return;
        modal.classList.remove('show');
        modal.setAttribute('aria-hidden', 'true');
        document.body.classList.remove('modal-open');
    }

    function closeAllModals() {
        document.querySelectorAll('.modal.show').forEach(modal => {
            hideModal(`#${modal.id}`);
        });
    }

    function switchTab(tabName) {
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));

        const button = document.querySelector(`.tab-btn[data-tab="${tabName}"]`);
        if (button) button.classList.add('active');

        const pane = document.getElementById(tabName);
        if (pane) pane.classList.add('active');
    }

    function openAddModal(btnId, modalId, formId) {
        const btn = document.getElementById(btnId);
        if (!btn) return;
        btn.addEventListener('click', () => {
            const form = document.getElementById(formId);
            if (form) form.reset();
            showModal(modalId);
        });
    }

    document.addEventListener('click', function(e) {
        const closeTrigger = e.target.closest('[data-dismiss="modal"]');
        if (closeTrigger) {
            e.preventDefault();
            const modal = closeTrigger.closest('.modal');
            if (modal && modal.id) hideModal(`#${modal.id}`);
            return;
        }

        const paginationLink = e.target.closest('.pagination-link');
        if (paginationLink) {
            e.preventDefault();
            const targetId = paginationLink.dataset.target;
            const url = paginationLink.getAttribute('href');
            if (!targetId || !url) return;

            fetch(url, { method: 'GET' })
                .then(response => response.text())
                .then(html => {
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, 'text/html');
                    const updated = doc.getElementById(targetId);
                    const current = document.getElementById(targetId);
                    if (current && updated) {
                        current.innerHTML = updated.innerHTML;
                    }
                })
                .catch(() => window.location.reload());
            return;
        }

        const backdrop = e.target.classList.contains('modal') ? e.target : null;
        if (backdrop && backdrop.id) {
            hideModal(`#${backdrop.id}`);
        }
    });

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeAllModals();
        }
    });

    document.addEventListener('submit', function(e) {
        const form = e.target;
        if (!form || !(form instanceof HTMLFormElement)) return;

        if (form.dataset.ajax === 'true') {
            e.preventDefault();
            submitAjaxForm(form);
        }
    });

    document.addEventListener('DOMContentLoaded', function() {
        openAddModal('addEvaluationFormBtn', '#addEvaluationFormModal', 'addEvaluationForm');
        openAddModal('addEvaluationCategoryBtn', '#addEvaluationCategoryModal', 'addEvaluationCategoryForm');
        openAddModal('addEvaluationCriteriaBtn', '#addEvaluationCriteriaModal', 'addEvaluationCriteriaForm');
        openAddModal('addRubricBtn', '#addRubricModal', 'addRubricForm');

        document.querySelectorAll('.tab-btn').forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                const tabName = this.getAttribute('data-tab');
                switchTab(tabName);
            });
        });

        document.querySelectorAll('.nav-submenu-link').forEach(link => {
            link.addEventListener('click', function(e) {
                const tabName = this.getAttribute('data-tab');
                if (!tabName) return;
                e.preventDefault();
                switchTab(tabName);
            });
        });

        document.addEventListener('click', function(e) {
            const editFormBtn = e.target.closest('.edit-form-btn');
            if (editFormBtn) {
                const form = document.getElementById('editEvaluationForm');
                if (form) form.action = `/performanceevaluation/admin/evaluation-forms/${editFormBtn.dataset.formId}/`;
                const cycle = document.getElementById('editFormCycle');
                const evaluatorType = document.getElementById('editFormEvaluatorType');
                const active = document.getElementById('editFormActive');
                if (cycle) cycle.value = editFormBtn.dataset.cycleId || '';
                if (evaluatorType) evaluatorType.value = editFormBtn.dataset.evaluatorType || '';
                if (active) active.checked = editFormBtn.dataset.active === 'True' || editFormBtn.dataset.active === 'true';
                showModal('#editEvaluationFormModal');
                return;
            }

            const deleteFormBtn = e.target.closest('.delete-form-btn');
            if (deleteFormBtn) {
                const form = document.getElementById('deleteEvaluationForm');
                if (form) form.action = `/performanceevaluation/admin/evaluation-forms/${deleteFormBtn.dataset.formId}/delete/`;
                const nameEl = document.getElementById('deleteEvaluationFormName');
                if (nameEl) nameEl.textContent = deleteFormBtn.dataset.title || '';
                showModal('#deleteEvaluationFormModal');
                return;
            }

            const editCategoryBtn = e.target.closest('.edit-category-btn');
            if (editCategoryBtn) {
                const form = document.getElementById('editEvaluationCategoryForm');
                if (form) form.action = `/performanceevaluation/admin/evaluation-categories/${editCategoryBtn.dataset.categoryId}/`;
                const cycle = document.getElementById('editCategoryCycle');
                const name = document.getElementById('editCategoryName');
                const weight = document.getElementById('editCategoryWeight');
                if (cycle) cycle.value = editCategoryBtn.dataset.cycleId || '';
                if (name) name.value = editCategoryBtn.dataset.name || '';
                if (weight) weight.value = editCategoryBtn.dataset.weight || '0';
                showModal('#editEvaluationCategoryModal');
                return;
            }

            const deleteCategoryBtn = e.target.closest('.delete-category-btn');
            if (deleteCategoryBtn) {
                const form = document.getElementById('deleteEvaluationCategoryForm');
                if (form) form.action = `/performanceevaluation/admin/evaluation-categories/${deleteCategoryBtn.dataset.categoryId}/delete/`;
                const nameEl = document.getElementById('deleteEvaluationCategoryName');
                if (nameEl) nameEl.textContent = deleteCategoryBtn.dataset.title || '';
                showModal('#deleteEvaluationCategoryModal');
                return;
            }

            const editCriteriaBtn = e.target.closest('.edit-criteria-btn');
            if (editCriteriaBtn) {
                const form = document.getElementById('editEvaluationCriteriaForm');
                if (form) form.action = `/performanceevaluation/admin/evaluation-criteria/${editCriteriaBtn.dataset.criteriaId}/`;
                const category = document.getElementById('editCriteriaCategory');
                const name = document.getElementById('editCriteriaName');
                const description = document.getElementById('editCriteriaDescription');
                const weight = document.getElementById('editCriteriaWeight');
                if (category) category.value = editCriteriaBtn.dataset.categoryId || '';
                if (name) name.value = editCriteriaBtn.dataset.name || '';
                if (description) description.value = editCriteriaBtn.dataset.description || '';
                if (weight) weight.value = editCriteriaBtn.dataset.weight || '0';
                showModal('#editEvaluationCriteriaModal');
                return;
            }

            const deleteCriteriaBtn = e.target.closest('.delete-criteria-btn');
            if (deleteCriteriaBtn) {
                const form = document.getElementById('deleteEvaluationCriteriaForm');
                if (form) form.action = `/performanceevaluation/admin/evaluation-criteria/${deleteCriteriaBtn.dataset.criteriaId}/delete/`;
                const nameEl = document.getElementById('deleteEvaluationCriteriaName');
                if (nameEl) nameEl.textContent = deleteCriteriaBtn.dataset.title || '';
                showModal('#deleteEvaluationCriteriaModal');
                return;
            }

            const editRubricBtn = e.target.closest('.edit-rubric-btn');
            if (editRubricBtn) {
                const form = document.getElementById('editRubricForm');
                if (form) form.action = `/performanceevaluation/admin/rubrics/${editRubricBtn.dataset.rubricId}/`;
                const criterion = document.getElementById('editRubricCriterion');
                const level = document.getElementById('editRubricLevel');
                const description = document.getElementById('editRubricDescription');
                if (criterion) criterion.value = editRubricBtn.dataset.criterionId || '';
                if (level) level.value = editRubricBtn.dataset.level || '';
                if (description) description.value = editRubricBtn.dataset.description || '';
                showModal('#editRubricModal');
                return;
            }

            const deleteRubricBtn = e.target.closest('.delete-rubric-btn');
            if (deleteRubricBtn) {
                const form = document.getElementById('deleteRubricForm');
                if (form) form.action = `/performanceevaluation/admin/rubrics/${deleteRubricBtn.dataset.rubricId}/delete/`;
                const nameEl = document.getElementById('deleteRubricName');
                if (nameEl) nameEl.textContent = deleteRubricBtn.dataset.title || '';
                showModal('#deleteRubricModal');
                return;
            }
        });

        document.querySelectorAll('.modal').forEach(modal => {
            modal.classList.remove('show');
            modal.setAttribute('aria-hidden', 'true');
        });
    });
})();
