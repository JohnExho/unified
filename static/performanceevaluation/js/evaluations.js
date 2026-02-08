(function() {
    'use strict';

    function fetchForms(url) {
        fetch(url, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
            .then(response => response.json())
            .then(data => {
                const container = document.getElementById('evaluationsFormsSection');
                if (!container || !data.evaluations_forms_html) return;
                container.innerHTML = data.evaluations_forms_html;
            })
            .catch(() => window.location.reload());
    }

    const filterForm = document.getElementById('evaluationsFilterForm');
    if (!filterForm) return;

    const applyFilters = () => {
        const params = new URLSearchParams(new FormData(filterForm));
        const url = `${window.location.pathname}?${params.toString()}`;
        fetchForms(url);
    };

    let debounceId;
    const debounceApply = () => {
        window.clearTimeout(debounceId);
        debounceId = window.setTimeout(applyFilters, 250);
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
