/**
 * GOMA-Efootball League - Scripts JavaScript
 * Animations et interactions dynamiques
 */

document.addEventListener('DOMContentLoaded', function() {

    // ========================
    // ANIMATION COMPTEURS
    // ========================
    const counters = document.querySelectorAll('.counter');
    counters.forEach(counter => {
        const target = parseInt(counter.innerText);
        if (isNaN(target)) return;

        counter.innerText = '0';
        const duration = 1500; // ms
        const step = target / (duration / 16); // 60fps

        let current = 0;
        const updateCounter = () => {
            current += step;
            if (current < target) {
                counter.innerText = Math.floor(current);
                requestAnimationFrame(updateCounter);
            } else {
                counter.innerText = target;
            }
        };
        updateCounter();
    });

    // ========================
    // AUTO-DISMISS DES ALERTES
    // ========================
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) {
                bsAlert.close();
            }
        }, 5000); // Fermer après 5 secondes
    });

    // ========================
    // CONFIRMATION SUPPRESSION
    // ========================
    const deleteButtons = document.querySelectorAll('[data-confirm]');
    deleteButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm') || 'Êtes-vous sûr ?';
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });

    // ========================
    // TOOLTIP BOOTSTRAP
    // ========================
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltipTriggerList.forEach(el => {
        new bootstrap.Tooltip(el);
    });

    // ========================
    // NAVBAR SCROLL EFFECT
    // ========================
    let lastScrollTop = 0;
    const navbar = document.querySelector('.navbar');

    window.addEventListener('scroll', function() {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;

        if (scrollTop > 100) {
            navbar.style.boxShadow = '0 2px 20px rgba(13, 110, 253, 0.3)';
        } else {
            navbar.style.boxShadow = 'none';
        }

        lastScrollTop = scrollTop;
    });

    // ========================
    // PREVIEW IMAGE UPLOAD
    // ========================
    const imageInput = document.querySelector('input[type="file"][accept="image/*"]');
    if (imageInput) {
        imageInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(event) {
                    // Créer ou mettre à jour la preview
                    let preview = document.getElementById('image-preview');
                    if (!preview) {
                        preview = document.createElement('img');
                        preview.id = 'image-preview';
                        preview.className = 'rounded mt-2';
                        preview.style.maxHeight = '100px';
                        imageInput.parentNode.appendChild(preview);
                    }
                    preview.src = event.target.result;
                };
                reader.readAsDataURL(file);
            }
        });
    }

    console.log('🎮 GOMA-Efootball League - Chargé avec succès');
});