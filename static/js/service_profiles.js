document.addEventListener('DOMContentLoaded', (event) => {
    const table = document.getElementById('profiles-table');
    if (!table) return;

    let dragged;

    // Add visual feedback for draggable rows
    table.querySelectorAll('tr').forEach(row => {
        row.addEventListener('mouseenter', () => {
            row.style.cursor = 'grab';
        });
    });

    document.addEventListener('dragstart', (event) => {
        if (!event.target.closest('tr')) return;
        dragged = event.target.closest('tr');
        dragged.classList.add('dragging');
        event.target.style.opacity = '0.5';
    });

    document.addEventListener('dragend', (event) => {
        if (!event.target.closest('tr')) return;
        event.target.style.opacity = '';
        dragged.classList.remove('dragging');
    });

    document.addEventListener('dragover', (event) => {
        event.preventDefault();
        const tr = event.target.closest('tr');
        if (!tr || !tr.parentElement || tr.parentElement.id !== 'profiles-table') return;
    });

    document.addEventListener('drop', (event) => {
        event.preventDefault();
        const tr = event.target.closest('tr');
        if (!tr || !dragged || tr === dragged || !tr.parentElement || tr.parentElement.id !== 'profiles-table') return;

        const parent = tr.parentNode;
        const afterDrop = Array.from(parent.children).indexOf(dragged) < Array.from(parent.children).indexOf(tr);
        parent.insertBefore(dragged, afterDrop ? tr.nextSibling : tr);
        
        saveOrder();
    });

    function saveOrder() {
        const order = Array.from(table.querySelectorAll('tr'))
            .map((row, index) => ({
                id: row.id.split('-')[1],
                position: index
            }));

        fetch('/settings/service_profiles/reorder', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ order: order }),
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            if (!data.success) {
                console.error('Failed to save order:', data.error);
            }
        })
        .catch(error => {
            console.error('Error saving order:', error);
        });
    }
});
