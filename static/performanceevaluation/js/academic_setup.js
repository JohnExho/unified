/**
 * Admin Modal Handler
 * Handles Bootstrap modal functionality for admin pages
 */

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

    function refreshAcademicSetupLists() {
        fetch(window.location.href, {
            method: 'GET',
        })
            .then(response => response.text())
            .then(html => {
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');

                const listIds = ['academic-terms-list', 'evaluation-cycles-list', 'departments-list'];
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
            .catch(() => {
                window.location.reload();
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
                refreshAcademicSetupLists();
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

    document.addEventListener('submit', function(e) {
        const form = e.target;
        if (!form || !(form instanceof HTMLFormElement)) return;

        if (
            form.matches('#addTermForm, #addCycleForm, #addDepartmentForm, #editTermForm, #editCycleForm, #editDepartmentForm, #deleteTermForm, #deleteCycleForm, #deleteDepartmentForm')
        ) {
            e.preventDefault();
            submitAjaxForm(form);
        }
    });

    document.addEventListener('click', function(e) {
        const openTrigger = e.target.closest('[data-toggle="modal"]');
        const target = openTrigger ? openTrigger.getAttribute('data-target') : null;

        const closeTrigger = e.target.closest('[data-dismiss="modal"]');
        if (closeTrigger) {
            e.preventDefault();
            const modal = closeTrigger.closest('.modal');
            if (modal && modal.id) hideModal(`#${modal.id}`);
            return;
        }

        const backdrop = e.target.classList.contains('modal') ? e.target : null;
        if (backdrop && backdrop.id) {
            hideModal(`#${backdrop.id}`);
            return;
        }

        const editTermBtn = e.target.closest('[data-target="#editAcademicTermModal"]');
        if (editTermBtn) {
            const button = editTermBtn;
        const termId = button.getAttribute('data-term-id');
        const termName = button.getAttribute('data-term-name');
        const termStart = button.getAttribute('data-term-start');
        const termEnd = button.getAttribute('data-term-end');
        const termActive = button.getAttribute('data-term-active');

        const termIdInput = document.getElementById('editTermId');
        const termNameInput = document.getElementById('editTermName');
        const termStartInput = document.getElementById('editTermStartDate');
        const termEndInput = document.getElementById('editTermEndDate');
        const termActiveInput = document.getElementById('editTermIsActive');

        if (termIdInput) termIdInput.value = termId || '';
        if (termNameInput) termNameInput.value = termName || '';
        if (termStartInput) termStartInput.value = termStart || '';
        if (termEndInput) termEndInput.value = termEnd || '';
        if (termActiveInput) termActiveInput.checked = termActive === 'True';

        const form = document.getElementById('editTermForm');
        if (form && termId) {
            form.action = `/performanceevaluation/admin/academic-term/${termId}/`;
        }
            if (target) showModal(target);
            return;
        }

        const deleteTermBtn = e.target.closest('[data-target="#deleteAcademicTermModal"]');
        if (deleteTermBtn) {
            const button = deleteTermBtn;
        const termId = button.getAttribute('data-term-id');
        const termName = button.getAttribute('data-term-name');

        const nameEl = document.getElementById('deleteTermName');
        if (nameEl) nameEl.textContent = termName || '';

        const form = document.getElementById('deleteTermForm');
        if (form && termId) {
            form.action = `/performanceevaluation/admin/academic-term/${termId}/delete/`;
        }
            if (target) showModal(target);
            return;
        }

        const editCycleBtn = e.target.closest('[data-target="#editEvaluationCycleModal"]');
        if (editCycleBtn) {
            const button = editCycleBtn;
        const cycleId = button.getAttribute('data-cycle-id');
        const cycleName = button.getAttribute('data-cycle-name');
        const cycleTerm = button.getAttribute('data-cycle-term');
        const cycleStart = button.getAttribute('data-cycle-start');
        const cycleEnd = button.getAttribute('data-cycle-end');
        const cycleClosed = button.getAttribute('data-cycle-closed');

        const cycleNameInput = document.getElementById('editCycleName');
        const cycleTermInput = document.getElementById('editCycleAcademicTerm');
        const cycleStartInput = document.getElementById('editCycleStartDate');
        const cycleEndInput = document.getElementById('editCycleEndDate');
        const cycleClosedInput = document.getElementById('editCycleIsClosed');

        if (cycleNameInput) cycleNameInput.value = cycleName || '';
        if (cycleTermInput) cycleTermInput.value = cycleTerm || '';
        if (cycleStartInput) cycleStartInput.value = cycleStart || '';
        if (cycleEndInput) cycleEndInput.value = cycleEnd || '';
        if (cycleClosedInput) cycleClosedInput.checked = cycleClosed === 'True';

        const form = document.getElementById('editCycleForm');
        if (form && cycleId) {
            form.action = `/performanceevaluation/admin/evaluation-cycle/${cycleId}/`;
        }
            if (target) showModal(target);
            return;
        }

        const deleteCycleBtn = e.target.closest('[data-target="#deleteEvaluationCycleModal"]');
        if (deleteCycleBtn) {
            const button = deleteCycleBtn;
        const cycleId = button.getAttribute('data-cycle-id');
        const cycleName = button.getAttribute('data-cycle-name');

        const nameEl = document.getElementById('deleteCycleName');
        if (nameEl) nameEl.textContent = cycleName || '';

        const form = document.getElementById('deleteCycleForm');
        if (form && cycleId) {
            form.action = `/performanceevaluation/admin/evaluation-cycle/${cycleId}/delete/`;
        }
            if (target) showModal(target);
            return;
        }

        const editDeptBtn = e.target.closest('[data-target="#editDepartmentModal"]');
        if (editDeptBtn) {
            const button = editDeptBtn;
        const deptId = button.getAttribute('data-dept-id');
        const deptName = button.getAttribute('data-dept-name');
        const deptCode = button.getAttribute('data-dept-code');
        const deptActive = button.getAttribute('data-dept-active');

        const deptNameInput = document.getElementById('editDepartmentName');
        const deptCodeInput = document.getElementById('editDepartmentCode');
        const deptActiveInput = document.getElementById('editDepartmentIsActive');

        if (deptNameInput) deptNameInput.value = deptName || '';
        if (deptCodeInput) deptCodeInput.value = deptCode || '';
        if (deptActiveInput) deptActiveInput.checked = deptActive === 'True';

        const form = document.getElementById('editDepartmentForm');
        if (form && deptId) {
            form.action = `/performanceevaluation/admin/department/${deptId}/`;
        }
            if (target) showModal(target);
            return;
        }

        const deleteDeptBtn = e.target.closest('[data-target="#deleteDepartmentModal"]');
        if (deleteDeptBtn) {
            const button = deleteDeptBtn;
        const deptId = button.getAttribute('data-dept-id');
        const deptName = button.getAttribute('data-dept-name');

        const nameEl = document.getElementById('deleteDepartmentName');
        if (nameEl) nameEl.textContent = deptName || '';

        const form = document.getElementById('deleteDepartmentForm');
        if (form && deptId) {
            form.action = `/performanceevaluation/admin/department/${deptId}/delete/`;
        }
            if (target) showModal(target);
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

        if (openTrigger && target) {
            e.preventDefault();
            showModal(target);
        }
    });

    document.addEventListener('keydown', function(e) {
        if (e.key !== 'Escape') return;
        const openModal = document.querySelector('.modal.show');
        if (openModal && openModal.id) {
            hideModal(`#${openModal.id}`);
        }
    });

    // Tab switching functionality
    function switchTab(tabName) {
        // Remove active class from all tabs and buttons
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));

        // Add active class to matching button and corresponding pane
        const button = document.querySelector(`.tab-btn[data-tab="${tabName}"]`);
        if (button) button.classList.add('active');
        
        const pane = document.getElementById(tabName);
        if (pane) pane.classList.add('active');
    }

    const tabButtons = document.querySelectorAll('.tab-btn');
    tabButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const tabName = this.getAttribute('data-tab');
            switchTab(tabName);
        });
    });

    // Submenu link switching
    const submenuLinks = document.querySelectorAll('.nav-submenu-link');
    submenuLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const tabName = this.getAttribute('data-tab');
            switchTab(tabName);
        });
    });

    // Ensure modals are hidden on load
    document.querySelectorAll('.modal').forEach(modal => {
        modal.classList.remove('show');
        modal.setAttribute('aria-hidden', 'true');
    });
})();
