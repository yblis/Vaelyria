// Gestion de l'état offline/online
function updateOnlineStatus() {
    const indicator = document.createElement('div');
    indicator.className = 'offline-indicator';
    indicator.textContent = 'Vous êtes hors ligne';
    document.body.appendChild(indicator);

    window.addEventListener('online', () => {
        document.body.classList.remove('offline');
        // Synchroniser les données en attente
        if ('serviceWorker' in navigator && 'SyncManager' in window) {
            navigator.serviceWorker.ready.then(registration => {
                return registration.sync.register('sync-data');
            });
        }
    });

    window.addEventListener('offline', () => {
        document.body.classList.add('offline');
    });

    // État initial
    if (!navigator.onLine) {
        document.body.classList.add('offline');
    }
}

// Gestion des interactions tactiles
function setupTouchInteractions() {
    // Prévenir le double-tap zoom sur les boutons et liens
    const interactiveElements = document.querySelectorAll('button, a, .btn, .nav-link');
    interactiveElements.forEach(element => {
        element.addEventListener('touchend', e => {
            e.preventDefault();
            element.click();
        });
    });

    // Gestion du swipe pour la navigation
    let touchStartX = 0;
    let touchEndX = 0;

    document.addEventListener('touchstart', e => {
        touchStartX = e.changedTouches[0].screenX;
    }, false);

    document.addEventListener('touchend', e => {
        touchEndX = e.changedTouches[0].screenX;
        handleSwipe();
    }, false);

    function handleSwipe() {
        const swipeThreshold = 100;
        const diff = touchEndX - touchStartX;

        if (Math.abs(diff) > swipeThreshold) {
            // Swipe droite -> gauche
            if (diff < 0 && window.history.length > 1) {
                window.history.forward();
            }
            // Swipe gauche -> droite
            else if (diff > 0 && window.history.length > 1) {
                window.history.back();
            }
        }
    }
}

// Gestion des formulaires en mode offline
function setupOfflineFormHandling() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', async (e) => {
            if (!navigator.onLine) {
                e.preventDefault();
                
                const formData = new FormData(form);
                const data = {
                    url: form.action,
                    method: form.method,
                    data: Object.fromEntries(formData)
                };

                // Stocker la requête pour plus tard
                try {
                    const offlineData = JSON.parse(localStorage.getItem('offlineData') || '[]');
                    offlineData.push(data);
                    localStorage.setItem('offlineData', JSON.stringify(offlineData));
                    
                    // Feedback utilisateur
                    const alert = document.createElement('div');
                    alert.className = 'alert alert-warning';
                    alert.textContent = 'Vous êtes hors ligne. Les données seront synchronisées une fois la connexion rétablie.';
                    form.parentNode.insertBefore(alert, form);
                } catch (error) {
                    console.error('Erreur lors du stockage offline:', error);
                }
            }
        });
    });
}

// Initialisation
document.addEventListener('DOMContentLoaded', () => {
    updateOnlineStatus();
    setupTouchInteractions();
    setupOfflineFormHandling();

    // Demander la permission pour les notifications
    if ('Notification' in window) {
        Notification.requestPermission();
    }
});

// Synchronisation des données une fois en ligne
async function syncOfflineData() {
    const offlineData = JSON.parse(localStorage.getItem('offlineData') || '[]');
    
    for (const data of offlineData) {
        try {
            await fetch(data.url, {
                method: data.method,
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data.data)
            });
        } catch (error) {
            console.error('Erreur lors de la synchronisation:', error);
            return;
        }
    }

    // Nettoyer les données synchronisées
    localStorage.removeItem('offlineData');
}

// Écouter l'événement de synchronisation
self.addEventListener('sync', event => {
    if (event.tag === 'sync-data') {
        event.waitUntil(syncOfflineData());
    }
});
