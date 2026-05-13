document.addEventListener('DOMContentLoaded', () => {
    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if(target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });

    // Star Rating Logic
    const stars = document.querySelectorAll('.star');
    let currentRating = 0;

    if (stars.length > 0) {
        stars.forEach(star => {
            star.addEventListener('mouseover', function() {
                const value = this.getAttribute('data-value');
                highlightStars(value);
            });

            star.addEventListener('mouseout', function() {
                highlightStars(currentRating);
            });

            star.addEventListener('click', function() {
                currentRating = this.getAttribute('data-value');
                highlightStars(currentRating);
                // Optionally set hidden input value for form submission
                const ratingInput = document.getElementById('rating-value');
                if(ratingInput) ratingInput.value = currentRating;
            });
        });
    }

    function highlightStars(value) {
        stars.forEach(star => {
            if (star.getAttribute('data-value') <= value) {
                star.classList.add('active');
            } else {
                star.classList.remove('active');
            }
        });
    }

    // Review Form Validation
    const reviewForm = document.querySelector('.review-form form');
    if (reviewForm) {
        reviewForm.addEventListener('submit', function(e) {
            const ratingInput = document.getElementById('rating-value');
            if (ratingInput && (ratingInput.value === "0" || !ratingInput.value)) {
                e.preventDefault();
                alert("Please select a star rating before submitting your review.");
            }
        });
    }

    // Form Submission Interactions (Mock)
    const subscribeForm = document.getElementById('subscribe-form');
    if(subscribeForm) {
        subscribeForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const btn = subscribeForm.querySelector('button');
            const originalText = btn.innerText;
            btn.innerText = 'Subscribed!';
            btn.style.background = '#4CAF50';
            setTimeout(() => {
                btn.innerText = originalText;
                btn.style.background = '';
                subscribeForm.reset();
            }, 3000);
        });
    }

    // Add entrance animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: "0px 0px -50px 0px"
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    const animatedElements = document.querySelectorAll('.glass, .feature-card, .motd-card');
    animatedElements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });
});
