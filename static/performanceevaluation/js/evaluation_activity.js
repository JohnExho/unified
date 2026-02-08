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

    function refreshEvaluationActivityLists() {
        fetch(window.location.href, { method: 'GET' })
            .then(response => response.text())
            .then(html => {
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');

                const listIds = ['evaluations-list'];
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
                refreshEvaluationActivityLists();
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

    document.addEventListener('submit', function(e) {
        const form = e.target;
        if (!form || !(form instanceof HTMLFormElement)) return;

        if (form.dataset.ajax === 'true') {
            e.preventDefault();
            submitAjaxForm(form);
        }
    });

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
            return;
        }

        const editEvaluationBtn = e.target.closest('.edit-evaluation-btn');
        if (editEvaluationBtn) {
            const evaluationId = editEvaluationBtn.getAttribute('data-evaluation-id');
            const formId = editEvaluationBtn.getAttribute('data-form-id');
            const evaluateeId = editEvaluationBtn.getAttribute('data-evaluatee-id');
            const evaluatorId = editEvaluationBtn.getAttribute('data-evaluator-id');
            const submittedAt = editEvaluationBtn.getAttribute('data-submitted-at');
            const isSubmitted = editEvaluationBtn.getAttribute('data-is-submitted');

            const formSelect = document.getElementById('editEvaluationFormSelect');
            const evaluateeSelect = document.getElementById('editEvaluatee');
            const evaluatorSelect = document.getElementById('editEvaluator');
            const submittedAtInput = document.getElementById('editSubmittedAt');
            const isSubmittedInput = document.getElementById('editIsSubmitted');

            if (formSelect) formSelect.value = formId || '';
            if (evaluateeSelect) evaluateeSelect.value = evaluateeId || '';
            if (evaluatorSelect) evaluatorSelect.value = evaluatorId || '';
            if (submittedAtInput) submittedAtInput.value = submittedAt || '';
            if (isSubmittedInput) isSubmittedInput.checked = isSubmitted === 'True';

            const form = document.getElementById('editEvaluationForm');
            if (form && evaluationId) {
                form.action = `/performanceevaluation/admin/evaluations/${evaluationId}/`;
            }
            showModal('#editEvaluationModal');
            return;
        }

        const deleteEvaluationBtn = e.target.closest('.delete-evaluation-btn');
        if (deleteEvaluationBtn) {
            const evaluationId = deleteEvaluationBtn.getAttribute('data-evaluation-id');
            const title = deleteEvaluationBtn.getAttribute('data-title');

            const nameEl = document.getElementById('deleteEvaluationName');
            if (nameEl) nameEl.textContent = title || '';

            const form = document.getElementById('deleteEvaluationForm');
            if (form && evaluationId) {
                form.action = `/performanceevaluation/admin/evaluations/${evaluationId}/delete/`;
            }
            showModal('#deleteEvaluationModal');
            return;
        }

    });

    document.addEventListener('DOMContentLoaded', function() {
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

        document.querySelectorAll('.modal').forEach(modal => {
            modal.classList.remove('show');
            modal.setAttribute('aria-hidden', 'true');
        });
    });
})();
