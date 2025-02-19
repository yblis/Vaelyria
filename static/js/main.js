// User Actions JavaScript
function initializeUserActions(isSearchPage = false) {
    // Destroy existing tooltips
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
        const tooltip = bootstrap.Tooltip.getInstance(el);
        if (tooltip) {
            tooltip.dispose();
        }
    });

    // Initialize tooltips
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
        new bootstrap.Tooltip(el);
    });

    // Initialize trash functionality
    document.querySelectorAll('.trash-user').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const dn = this.dataset.dn;
            if (confirm('Êtes-vous sûr de vouloir mettre cet utilisateur à la corbeille ?')) {
                fetch('/users/trash/' + encodeURIComponent(dn), {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.json().then(data => ({ ok: response.ok, data })))
                .then(({ ok, data }) => {
                    if (ok && data.success) {
                        if (isSearchPage) {
                            const row = document.querySelector(`tr[data-dn="${CSS.escape(dn)}"]`);
                            if (row) row.remove();
                        } else {
                            window.location.href = '/users/search';
                        }
                    } else {
                        throw new Error(data.error || 'Une erreur est survenue');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    if (isSearchPage) {
                        const row = document.querySelector(`tr[data-dn="${CSS.escape(dn)}"]`);
                        if (row) row.remove();
                    }
                });
            }
        });
    });

    // Initialize lock/unlock functionality
    document.querySelectorAll('.lock-user, .unlock-user').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const dn = this.dataset.dn;
            const action = this.classList.contains('lock-user') ? 'lock' : 'unlock';
            const confirmMessage = action === 'lock' ? 
                'Êtes-vous sûr de vouloir verrouiller cet utilisateur ?' :
                'Êtes-vous sûr de vouloir déverrouiller cet utilisateur ?';
            
            if (confirm(confirmMessage)) {
                fetch('/users/' + action + '/' + encodeURIComponent(dn), {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Network response was not ok');
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.success) {
                        if (isSearchPage) {
                            const row = document.querySelector(`tr[data-dn="${CSS.escape(dn)}"]`);
                            if (row) {
                                updateUserStatus(row, action);
                            }
                        } else {
                            window.location.reload();
                        }
                    } else {
                        alert('Erreur lors du ' + (action === 'lock' ? 'verrouillage' : 'déverrouillage') + ' : ' + 
                              (data.error || 'Une erreur est survenue'));
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('Une erreur est survenue lors du ' + (action === 'lock' ? 'verrouillage' : 'déverrouillage'));
                });
            }
        });
    });
}

function updateUserStatus(row, action) {
    const statusIcon = row.querySelector('td:first-child i');
    const actionButton = row.querySelector(`.${action}-user`);
    const dn = row.dataset.dn;
    
    if (action === 'lock') {
        statusIcon.className = 'fas fa-lock text-danger';
        statusIcon.title = 'Compte verrouillé';
        actionButton.outerHTML = `<a href="#" class="btn btn-sm btn-success unlock-user" data-dn="${dn}" title="Déverrouiller"><i class="fas fa-unlock"></i></a>`;
    } else {
        statusIcon.className = 'fas fa-lock-open text-success';
        statusIcon.title = 'Compte déverrouillé';
        actionButton.outerHTML = `<a href="#" class="btn btn-sm btn-warning lock-user" data-dn="${dn}" title="Verrouiller"><i class="fas fa-lock"></i></a>`;
    }
    
    initializeUserActions(true);
}

function initializeResetPassword() {
    document.querySelectorAll('.reset-password-btn').forEach(button => {
        button.addEventListener('click', function() {
            const dn = this.dataset.dn;
            document.getElementById('resetPasswordDn').value = dn;
        });
    });

    document.getElementById('confirmResetPassword')?.addEventListener('click', function() {
        const form = document.getElementById('resetPasswordForm');
        const dn = document.getElementById('resetPasswordDn').value;
        const password = document.getElementById('newPassword').value;
        const forceReset = document.getElementById('forceReset').checked;
        const enableUser = document.getElementById('enableUser').checked;
        const preventChange = document.getElementById('preventChange').checked;
        const neverExpire = document.getElementById('neverExpire').checked;

        if (!password) {
            alert('Veuillez entrer un mot de passe');
            return;
        }

        fetch('/users/reset_password/' + encodeURIComponent(dn), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                password: password,
                force_reset: forceReset,
                enable_account: enableUser,
                prevent_changes: preventChange,
                never_expire: neverExpire
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload();
            } else {
                alert('Erreur lors de la réinitialisation du mot de passe : ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Une erreur s\'est produite lors de la réinitialisation du mot de passe');
        });

        // Clear the form and close the modal
        document.getElementById('newPassword').value = '';
        document.getElementById('forceReset').checked = false;
        document.getElementById('enableUser').checked = false;
        document.getElementById('preventChange').checked = false;
        document.getElementById('neverExpire').checked = false;
        const modal = bootstrap.Modal.getInstance(document.getElementById('resetPasswordModal'));
        modal.hide();
    });
}

// Note: Les gestionnaires des boutons restore-user et move-user sont maintenant gérés dans user_search.js
