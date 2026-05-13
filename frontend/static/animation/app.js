/**
 * CineAI - Core Frontend Logic
 */

// Define global handlers early to avoid "undefined" errors on click
window.openTrailer = function(key) {
    const modal = document.getElementById('trailerModal');
    const iframe = document.getElementById('trailerIframe');
    if (modal && iframe) {
        iframe.src = `https://www.youtube.com/embed/${key}?autoplay=1`;
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
    }
};

document.addEventListener('DOMContentLoaded', () => {
<<<<<<< HEAD
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
=======
    initNavbar();
    initHeroSlider();
    initRowScrolling();
    initTrailerModal(); // This will now just handle the close logic
    initStarRating();
});

// ── Navbar ──────────────────────────────────────────────────
function initNavbar() {
    const nav = document.getElementById('navbar');
    if (!nav) return;
    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            nav.classList.add('scrolled');
        } else {
            nav.classList.remove('scrolled');
        }
    });
}

// ── Hero Slider ──────────────────────────────────────────────
function initHeroSlider() {
    const slides = document.querySelectorAll('.hero-slide');
    const dots = document.querySelectorAll('.hero-dot');
    const nextBtn = document.getElementById('heroNext');
    const prevBtn = document.getElementById('heroPrev');
    if (slides.length === 0) return;

    let currentSlide = 0;
    let slideInterval = setInterval(nextSlide, 8000);

    function showSlide(n) {
        slides[currentSlide].classList.remove('active');
        dots[currentSlide].classList.remove('active');
        currentSlide = (n + slides.length) % slides.length;
        slides[currentSlide].classList.add('active');
        dots[currentSlide].classList.add('active');
    }
    function nextSlide() { showSlide(currentSlide + 1); }
    function prevSlide() { showSlide(currentSlide - 1); }

    if (nextBtn) nextBtn.addEventListener('click', () => { nextSlide(); resetInterval(); });
    if (prevBtn) prevBtn.addEventListener('click', () => { prevSlide(); resetInterval(); });
    dots.forEach(dot => {
        dot.addEventListener('click', () => {
            showSlide(parseInt(dot.dataset.idx));
            resetInterval();
        });
    });
    function resetInterval() {
        clearInterval(slideInterval);
        slideInterval = setInterval(nextSlide, 8000);
    }
}

// ── Horizontal Row Scrolling ─────────────────────────────────────
function initRowScrolling() {
    const rows = document.querySelectorAll('.row-wrapper');
    rows.forEach(wrapper => {
        const row = wrapper.querySelector('.movie-row');
        const next = wrapper.querySelector('.row-next');
        const prev = wrapper.querySelector('.row-prev');
        if (!row || !next || !prev) return;
        next.addEventListener('click', () => { row.scrollBy({ left: 600, behavior: 'smooth' }); });
        prev.addEventListener('click', () => { row.scrollBy({ left: -600, behavior: 'smooth' }); });
    });
}

// ── Trailer Modal (Close Logic) ──────────────────────────────────
function initTrailerModal() {
    const modal = document.getElementById('trailerModal');
    const close = document.getElementById('modalClose');
    const iframe = document.getElementById('trailerIframe');
    if (!modal || !close || !iframe) return;

    function closeModal() {
        modal.classList.remove('show');
        iframe.src = '';
        document.body.style.overflow = '';
    }
    close.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.classList.contains('show')) closeModal();
    });
}

// ── Star Rating ───────────────────────────────────────────────
function initStarRating() {
    const stars = document.querySelectorAll('.star-btn');
    const input = document.getElementById('ratingInput');
    const label = document.getElementById('starLabel');
    const submitBtn = document.getElementById('submitReview');
    if (!stars.length || !input) return;

    stars.forEach(star => {
        star.addEventListener('mouseover', () => highlightStars(star.dataset.val));
        star.addEventListener('mouseout', () => highlightStars(input.value));
        star.addEventListener('click', () => {
            input.value = star.dataset.val;
            highlightStars(input.value);
            if(label) label.innerText = `You rated ${input.value}/5`;
            if(submitBtn) submitBtn.disabled = false;
        });
    });
    function highlightStars(val) {
        stars.forEach(s => {
            s.style.color = (parseInt(s.dataset.val) <= parseInt(val)) ? '#f5c518' : '#444';
        });
    }
}
