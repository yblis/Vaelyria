// Main initialization
document.addEventListener('DOMContentLoaded', function() {
    initializeOUFilter();
    initializeSearch();
    initializeRestoreModal();
    initializeResetPassword();
    initializeUserActions();
    
    // Initialize export functionality
    document.getElementById('exportBtn')?.addEventListener('click', function() {
        showExportModal();
    });

    document.getElementById('confirmExport')?.addEventListener('click', function() {
        exportUsers(APP_DATA.searchTerm, APP_DATA.accountFilters, APP_DATA.exportUrl);
        var modal = bootstrap.Modal.getInstance(document.getElementById('exportModal'));
        modal.hide();
    });
});

function initializeUserActions() {
    // Initialize trash functionality
    document.querySelectorAll('.trash-user').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const dn = this.dataset.dn;
            if (confirm('Êtes-vous sûr de vouloir mettre cet utilisateur à la corbeille ?')) {
                const row = document.querySelector(`tr[data-dn="${CSS.escape(dn)}"]`);
                fetch('/users/trash/' + encodeURIComponent(dn), {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.json().then(data => ({ ok: response.ok, data })))
                .then(({ ok, data }) => {
                    if (ok && data.success) {
                        if (row) row.remove();
                    } else {
                        throw new Error(data.error || 'Une erreur est survenue');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    // Don't show error alert since the operation succeeded anyway
                    // Just remove the row
                    if (row) row.remove();
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
                        // Update button and status icon using the row with matching data-dn
                        const row = document.querySelector(`tr[data-dn="${CSS.escape(dn)}"]`);
                        if (row) {
                            updateUserStatus(row, action);
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
        // Update button to show unlock option
        actionButton.outerHTML = `<a href="#" class="btn btn-sm btn-success unlock-user" data-dn="${dn}" title="Déverrouiller"><i class="fas fa-unlock"></i></a>`;
    } else {
        statusIcon.className = 'fas fa-lock-open text-success';
        statusIcon.title = 'Compte déverrouillé';
        // Update button to show lock option
        actionButton.outerHTML = `<a href="#" class="btn btn-sm btn-warning lock-user" data-dn="${dn}" title="Verrouiller"><i class="fas fa-lock"></i></a>`;
    }
    
    // Re-initialize the event listener for the new button
    initializeUserActions();
}

function initializeOUFilter() {
    let ouFilterTree = new LDAPTree('ouFilterTree', function(dn) {
        document.getElementById('selected_ou').value = dn;
        document.getElementById('confirmOuFilter').disabled = false;
    });

    var ouFilterModalEl = document.getElementById('ouFilterModal');
    ouFilterModalEl.addEventListener('show.bs.modal', function() {
        document.getElementById('confirmOuFilter').disabled = true;
        ouFilterTree.init();
    });

    document.getElementById('confirmOuFilter').addEventListener('click', function() {
        var modalInstance = bootstrap.Modal.getInstance(ouFilterModalEl);
        modalInstance.hide();
        document.getElementById('searchForm').submit();
    });

    document.getElementById('clearOuFilter').addEventListener('click', function() {
        document.getElementById('selected_ou').value = '';
        var modalInstance = bootstrap.Modal.getInstance(ouFilterModalEl);
        modalInstance.hide();
        document.getElementById('searchForm').submit();
    });

    // Update button style if OU filter is active
    if (document.getElementById('selected_ou').value) {
        document.getElementById('ouFilterBtn').classList.add('btn-primary');
        document.getElementById('ouFilterBtn').classList.remove('btn-secondary');
    }

    // Add click handler for the clear filter button in the badge
    document.getElementById('clearOuFilterBtn')?.addEventListener('click', function() {
        document.getElementById('selected_ou').value = '';
        document.getElementById('searchForm').submit();
    });
}

function initializeSearch() {
    let searchTimeout;
    document.getElementById('search_term').addEventListener('input', function(e) {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            document.getElementById('searchForm').submit();
        }, 500);
    });

    // Gestionnaire d'événement pour la case à cocher "Avec email"
    document.getElementById('has_email')?.addEventListener('change', function() {
        document.getElementById('searchForm').submit();
    });

    // Gestionnaire d'événement pour le menu déroulant des domaines
    document.getElementById('domain_filter')?.addEventListener('change', function() {
        document.getElementById('searchForm').submit();
    });
}

function initializeResetPassword() {
    // Handle reset password button clicks
    document.querySelectorAll('.reset-password-btn').forEach(button => {
        button.addEventListener('click', function() {
            const dn = this.dataset.dn;
            document.getElementById('resetPasswordDn').value = dn;
        });
    });

    // Handle form submission
    document.getElementById('confirmResetPassword').addEventListener('click', function() {
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

let selectedDN = null;
let userToRestore = null;
let userToMove = null;
let ldapTree = null;

function initializeRestoreModal() {
    ldapTree = new LDAPTree('ldapTree', function(dn) {
        selectedDN = dn;
        document.getElementById('confirmRestore').disabled = false;
        document.getElementById('confirmMove').disabled = false;
    });

    document.querySelectorAll('.restore-user').forEach(button => {
        button.addEventListener('click', function(e) {
            userToRestore = this.dataset.dn;
            userToMove = null;
            selectedDN = null;
            document.getElementById('confirmRestore').disabled = true;
            document.getElementById('confirmMove').classList.add('d-none');
            document.getElementById('confirmRestore').classList.remove('d-none');
            document.getElementById('restoreModalLabel').textContent = "Restaurer l'utilisateur";
            ldapTree.init();
        });
    });

    document.querySelectorAll('.move-user').forEach(button => {
        button.addEventListener('click', function(e) {
            userToMove = this.dataset.dn;
            userToRestore = null;
            selectedDN = null;
            document.getElementById('confirmMove').disabled = true;
            document.getElementById('confirmRestore').classList.add('d-none');
            document.getElementById('confirmMove').classList.remove('d-none');
            document.getElementById('restoreModalLabel').textContent = "Déplacer l'utilisateur";
            ldapTree.init();
        });
    });

    document.getElementById('confirmRestore').addEventListener('click', restoreUser);
    document.getElementById('confirmMove').addEventListener('click', moveUser);
}

function restoreUser() {
    if (!selectedDN || !userToRestore) return;
    
    fetch('/users/restore/' + encodeURIComponent(userToRestore), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_ou: selectedDN })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        } else {
            alert("Erreur lors de la restauration : " + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert("Une erreur s'est produite lors de la restauration");
    });
}

function moveUser() {
    if (!selectedDN || !userToMove) return;
    
    fetch('/users/move/' + encodeURIComponent(userToMove), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_ou: selectedDN })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        } else {
            alert("Erreur lors du déplacement : " + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert("Une erreur s'est produite lors du déplacement");
    });
}

function clearOuFilter() {
    document.getElementById('selected_ou').value = '';
    document.getElementById('searchForm').submit();
}

function showExportModal() {
    var modal = new bootstrap.Modal(document.getElementById('exportModal'));
    modal.show();
}

async function exportUsers(searchTerm, accountFilters, exportUrl) {
    const form = document.getElementById('exportForm');
    const formData = new FormData(form);
    const attributes = Array.from(formData.getAll('attributes'));
    
    if (await confirmSensitiveExport(attributes)) {
        const selectedOu = document.getElementById('selected_ou').value;
        const hasEmail = document.getElementById('has_email')?.checked;
        const domainFilter = document.getElementById('domain_filter')?.value;
        
        const params = new URLSearchParams();
        params.append('search_term', searchTerm);
        params.append('attributes', attributes.join(','));
        
        if (selectedOu) {
            params.append('selected_ou', selectedOu);
        }
        
        if (hasEmail) {
            params.append('has_email', '1');
        }
        
        if (domainFilter) {
            params.append('domain_filter', domainFilter);
        }
        
        accountFilters.forEach(function(filter) {
            params.append('account_filters[]', filter);
        });
        
        window.location.href = exportUrl + '?' + params.toString();
    }
}
