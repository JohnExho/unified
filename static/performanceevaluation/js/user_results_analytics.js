(function() {
    'use strict';

    function fetchTable(url) {
        fetch(url, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
            .then(response => response.json())
            .then(data => {
                const table = document.getElementById('user-results-table');
                if (!table || !data.user_results_table_html) return;
                table.innerHTML = data.user_results_table_html;
            })
            .catch(() => window.location.reload());
    }

    const filterForm = document.getElementById('userResultsFilterForm');
    if (!filterForm) return;

    const applyFilters = () => {
        const params = new URLSearchParams(new FormData(filterForm));
        const url = `${window.location.pathname}?${params.toString()}`;
        fetchTable(url);
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
})();
