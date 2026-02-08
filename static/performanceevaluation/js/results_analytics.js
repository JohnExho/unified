(function() {
    'use strict';

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

    function fetchReports(url) {
        fetch(url, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
            .then(response => {
                const contentType = response.headers.get('content-type') || '';
                if (contentType.includes('application/json')) {
                    return response.json().then(data => ({ data }));
                }
                return response.text().then(html => ({ html }));
            })
            .then(payload => {
                const table = document.getElementById('results-analytics-table');
                if (!table) return;

                if (payload.data && payload.data.results_analytics_table_html) {
                    table.innerHTML = payload.data.results_analytics_table_html;
                    return;
                }

                if (payload.html) {
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(payload.html, 'text/html');
                    const updated = doc.getElementById('results-analytics-table');
                    if (updated) {
                        table.innerHTML = updated.innerHTML;
                    }
                }
            })
            .catch(() => window.location.reload());
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
            fetchReports(url);
            return;
        }

        const sortBtn = e.target.closest('.sort-btn');
        if (sortBtn) {
            e.preventDefault();
            const sort = sortBtn.getAttribute('data-sort');
            const dir = sortBtn.getAttribute('data-dir');
            const form = document.getElementById('resultsAnalyticsFilterForm');
            const params = new URLSearchParams(form ? new FormData(form) : undefined);
            if (sort) params.set('sort', sort);
            if (dir) params.set('dir', dir);
            params.set('page', '1');
            const url = `${window.location.pathname}?${params.toString()}`;
            fetchReports(url);
            return;
        }

        const viewBtn = e.target.closest('.view-report-btn');
        if (viewBtn) {
            const evaluatee = viewBtn.getAttribute('data-evaluatee');
            const cycle = viewBtn.getAttribute('data-cycle');
            const score = viewBtn.getAttribute('data-score');
            const level = viewBtn.getAttribute('data-level');
            const computed = viewBtn.getAttribute('data-computed');
            const recommendations = viewBtn.getAttribute('data-recommendations');

            const elEvaluatee = document.getElementById('reportEvaluatee');
            const elCycle = document.getElementById('reportCycle');
            const elScore = document.getElementById('reportScore');
            const elLevel = document.getElementById('reportLevel');
            const elComputed = document.getElementById('reportComputed');
            const elRecommendations = document.getElementById('reportRecommendations');

            if (elEvaluatee) elEvaluatee.textContent = evaluatee || '';
            if (elCycle) elCycle.textContent = cycle || '';
            if (elScore) elScore.textContent = score || '';
            if (elLevel) elLevel.textContent = level || '';
            if (elComputed) elComputed.textContent = computed || '';
            if (elRecommendations) elRecommendations.textContent = recommendations || '';

            showModal('#viewReportModal');
        }

        const reportRow = e.target.closest('.report-row');
        if (reportRow && !e.target.closest('.view-report-btn')) {
            const resultId = reportRow.getAttribute('data-result-id');
            if (!resultId) return;

            const nextRow = reportRow.nextElementSibling;
            if (nextRow && nextRow.classList.contains('recommendations-row')) {
                nextRow.remove();
                return;
            }

            fetch(`/performanceevaluation/admin/results-analytics/${resultId}/recommendations/`, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
                .then(response => response.json())
                .then(data => {
                    if (!data.recommendations_html) return;
                    const row = document.createElement('tr');
                    row.className = 'recommendations-row';
                    row.innerHTML = `<td colspan="7">${data.recommendations_html}</td>`;
                    reportRow.parentNode.insertBefore(row, reportRow.nextSibling);
                })
                .catch(() => window.location.reload());
        }

        const backdrop = e.target.classList.contains('modal') ? e.target : null;
        if (backdrop && backdrop.id) {
            hideModal(`#${backdrop.id}`);
        }
    });

    document.addEventListener('keydown', function(e) {
        if (e.key !== 'Escape') return;
        const openModal = document.querySelector('.modal.show');
        if (openModal && openModal.id) {
            hideModal(`#${openModal.id}`);
        }
    });

    const filterForm = document.getElementById('resultsAnalyticsFilterForm');
    if (filterForm) {
        const searchField = filterForm.querySelector('.search-field');
        const searchInput = filterForm.querySelector('input[name="search"]');
        const clearButton = filterForm.querySelector('.clear-search');

        const applyFilters = () => {
            const params = new URLSearchParams(new FormData(filterForm));
            params.set('page', '1');
            const url = `${window.location.pathname}?${params.toString()}`;
            fetchReports(url);
        };

        let debounceId;
        const debounceApply = () => {
            window.clearTimeout(debounceId);
            debounceId = window.setTimeout(applyFilters, 300);
        };

        filterForm.addEventListener('submit', function(e) {
            e.preventDefault();
            applyFilters();
        });

        filterForm.querySelectorAll('input, select').forEach(field => {
            const eventName = field.tagName.toLowerCase() === 'select' ? 'change' : 'input';
            field.addEventListener(eventName, debounceApply);
        });

        const toggleClearButton = () => {
            if (!searchField || !searchInput) return;
            if (searchInput.value.trim()) {
                searchField.classList.add('has-value');
            } else {
                searchField.classList.remove('has-value');
            }
        };

        toggleClearButton();

        if (searchInput) {
            searchInput.addEventListener('input', toggleClearButton);
        }

        if (clearButton && searchInput) {
            clearButton.addEventListener('click', function() {
                searchInput.value = '';
                toggleClearButton();
                applyFilters();
            });
        }
    }

    document.querySelectorAll('.modal').forEach(modal => {
        modal.classList.remove('show');
        modal.setAttribute('aria-hidden', 'true');
    });
})();
