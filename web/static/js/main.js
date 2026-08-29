/* ===================================================================
 * Tyndale 1.0.0 - Main JS
 *
 * ------------------------------------------------------------------- */

(function (html) {

        'use strict';


        /* animations
         * -------------------------------------------------- */
        const tl = anime.timeline({
            easing: 'easeInOutCubic',
            duration: 800,
            autoplay: false
        })
            .add({
                targets: '#loader',
                opacity: 0,
                duration: 1000,
                begin: function (anim) {
                    window.scrollTo(0, 0);
                }
            })
            .add({
                targets: '#preloader',
                opacity: 0,
                complete: function (anim) {
                    document.querySelector("#preloader").style.visibility = "hidden";
                    document.querySelector("#preloader").style.display = "none";
                }
            })
            .add({
                targets: '.s-header',
                translateY: [-100, 0],
                opacity: [0, 1]
            }, '-=200')
            .add({
                targets: ['.s-intro__text', '.s-intro__about'],
                translateY: [100, 0],
                opacity: [0, 1],
                delay: anime.stagger(400)
            })
            .add({
                targets: '.s-intro__bg',
                opacity: [0, 1],
                duration: 1000,
            })
            .add({
                targets: ['.s-intro__scroll-down'],
                opacity: [0, 1],
                duration: 400
            });


        /* preloader
         * -------------------------------------------------- */
        const ssPreloader = function () {

            const preloader = document.querySelector('#preloader');
            if (!preloader) return;

            html.classList.add('ss-preload');

            window.addEventListener('load', function () {
                html.classList.remove('ss-preload');
                html.classList.add('ss-loaded');
                tl.play();
            });

        }; // end ssPreloader


        /* mobile menu
         * ---------------------------------------------------- */
        const ssMobileMenu = function () {

            const toggleButton = document.querySelector('.s-header__menu-toggle');
            const mainNavWrap = document.querySelector('.s-header__nav-wrap');
            const siteBody = document.querySelector('body');

            if (!(toggleButton && mainNavWrap)) return;

            toggleButton.addEventListener('click', function (event) {
                event.preventDefault();
                toggleButton.classList.toggle('is-clicked');
                siteBody.classList.toggle('menu-is-open');
            });

            mainNavWrap.querySelectorAll('.s-header__nav a').forEach(function (link) {

                link.addEventListener("click", function (event) {

                    // at 900px and below
                    if (window.matchMedia('(max-width: 900px)').matches) {
                        toggleButton.classList.toggle('is-clicked');
                        siteBody.classList.toggle('menu-is-open');
                    }
                });
            });

            window.addEventListener('resize', function () {

                // above 900px
                if (window.matchMedia('(min-width: 901px)').matches) {
                    if (siteBody.classList.contains('menu-is-open')) siteBody.classList.remove('menu-is-open');
                    if (toggleButton.classList.contains('is-clicked')) toggleButton.classList.remove('is-clicked');
                }
            });

        }; // end ssMobileMenu


        /* highlight active menu link on pagescroll
         * ------------------------------------------------------ */
        const ssScrollSpy = function () {

            const sections = document.querySelectorAll('.target-section');

            // Add an event listener listening for scroll
            window.addEventListener('scroll', navHighlight);

            function navHighlight() {

                // Get current scroll position
                let scrollY = window.pageYOffset;

                // Loop through sections to get height(including padding and border),
                // top and ID values for each
                sections.forEach(function (current) {
                    const sectionHeight = current.offsetHeight;
                    const sectionTop = current.offsetTop - 50;
                    const sectionId = current.getAttribute('id');

                    /* If our current scroll position enters the space where current section
                     * on screen is, add .current class to parent element(li) of the thecorresponding
                     * navigation link, else remove it. To know which link is active, we use
                     * sectionId variable we are getting while looping through sections as
                     * an selector
                     */
                    if (scrollY > sectionTop && scrollY <= sectionTop + sectionHeight) {
                        document.querySelector('.s-header__nav a[href*=' + sectionId + ']').parentNode.classList.add('current');
                    } else {
                        document.querySelector('.s-header__nav a[href*=' + sectionId + ']').parentNode.classList.remove('current');
                    }
                });
            }

        }; // end ssScrollSpy


        /* animate elements if in viewport
         * ------------------------------------------------------ */
        const ssAnimateOnScroll = function () {

            const blocks = document.querySelectorAll('[data-animate-block]');

            window.addEventListener('scroll', animateOnScroll);

            function animateOnScroll() {

                let scrollY = window.pageYOffset;

                blocks.forEach(function (current) {

                    const viewportHeight = window.innerHeight;
                    const triggerTop = (current.offsetTop + (viewportHeight * .2)) - viewportHeight;
                    const blockHeight = current.offsetHeight;
                    const blockSpace = triggerTop + blockHeight;
                    const inView = scrollY > triggerTop && scrollY <= blockSpace;
                    const isAnimated = current.classList.contains('ss-animated');

                    if (inView && (!isAnimated)) {

                        anime({
                            targets: current.querySelectorAll('[data-animate-el]'),
                            opacity: [0, 1],
                            translateY: [100, 0],
                            delay: anime.stagger(200, {start: 200}),
                            duration: 800,
                            easing: 'easeInOutCubic',
                            begin: function (anim) {
                                current.classList.add('ss-animated');
                            }
                        });

                        if (current.classList.contains('about-stats')) {

                            let counters = current.querySelectorAll('[data-animate-el] .stats__count');

                            counters.forEach(function (counter, i) {

                                let val = +counter.dataset.counter;
                                let valSpan = counter.querySelectorAll('span')[0];

                                valSpan.innerText = '0';

                                setTimeout(function () {
                                    anime({
                                        targets: valSpan,
                                        innerText: [0, val],
                                        easing: 'linear',
                                        round: 1,
                                        duration: 2000
                                    });
                                }, i * 200);

                            });
                        }
                    }
                });
            }

        }; // end ssAnimateOnScroll


        /* swiper
         * ------------------------------------------------------ */
        const ssSwiper = function () {

            const clientsSwiper = new Swiper('.clients', {

                slidesPerView: 4,
                spaceBetween: 4,
                slideClass: 'clients__slide',
                pagination: {
                    el: '.swiper-pagination',
                    clickable: true,
                },
                breakpoints: {
                    // when window width is > 400px
                    401: {
                        spaceBetween: 8
                    },
                    // when window width is > 900px
                    901: {
                        slidesPerView: 5,
                        spaceBetween: 10
                    },
                    // when window width is > 1200px
                    1201: {
                        slidesPerView: 6,
                        spaceBetween: 10
                    }
                }
            });

            const testimonialsSwiper = new Swiper('.testimonial-slider', {

                slidesPerView: 1,
                pagination: {
                    el: '.swiper-pagination',
                    clickable: true,
                },
                breakpoints: {
                    // when window width is > 400px
                    401: {
                        slidesPerView: 1,
                        spaceBetween: 20
                    },
                    // when window width is > 800px
                    801: {
                        slidesPerView: 2,
                        spaceBetween: 32
                    },
                    // when window width is > 1200px
                    1201: {
                        slidesPerView: 2,
                        spaceBetween: 80
                    }
                }
            });

        }; // end ssSwiper


        /* photoswipe
        * ----------------------------------------------------- */
        const ssPhotoswipe = function () {

            const pswp = document.querySelectorAll('.pswp')[0];
            const allFolioSelector = '.folio-item';
            if (!pswp) return;

            // internal arrays
            let staticItems = [];
            let dynamicItems = [];

            // returns a Promise that resolves to a "WxH" string (e.g. "1600x1200")
            function getImageSize(src) {
                return new Promise(function (resolve) {
                    const img = new Image();
                    img.onload = function () {
                        resolve(img.naturalWidth + 'x' + img.naturalHeight);
                    };
                    img.onerror = function () {
                        resolve('0x0'); // fallback same format as dataset.size default
                    };
                    // set crossOrigin if you need to load images from other origins and they allow CORS
                    // img.crossOrigin = 'anonymous';
                    img.src = src;
                });
            }

            // helper: build item from a folio DOM node (same logic for both lists)
            function buildItemFromNode(folio) {
                if (!folio) return null;
                const thumbLink = folio.querySelector('.folio-item__thumb-link');
                if (!thumbLink) return null;

                const titleEl = folio.querySelector('.folio-item__title');
                const captionEl = folio.querySelector('.folio-item__caption');

                const href = thumbLink.getAttribute('href');
                const sizeData = thumbLink.dataset.size || '0x0';
                const size = sizeData.split('x');
                const width = parseInt(size[0], 10) || 0;
                const height = parseInt(size[1], 10) || 0;

                const item = {
                    src: href,
                    w: width,
                    h: height
                };

                // Helper: plain-text extractor
                function getText(el) {
                    return el ? el.textContent.trim() : '';
                }

                // Keep HTML for PhotoSwipe caption, but also store plain text for sharing
                if (titleEl || captionEl) {
                    const htmlTitle = titleEl ? '<h4>' + titleEl.textContent.trim() + '</h4>' : '';
                    const htmlCaption = captionEl ? captionEl.innerHTML : ''; // keep caption HTML if you want formatting
                    item.title = (htmlTitle + htmlCaption).trim();

                    // Plain-text field used for share/tweet text
                    item.titleText = (getText(titleEl) + (captionEl ? '\n' + getText(captionEl) : '')).trim();
                }

                return item;
            }

            // build static items once (folio-items without data-updatable)
            function buildStaticItems() {
                staticItems = [];
                const nodes = document.querySelectorAll('.folio-item:not([data-updatable])');
                nodes.forEach(function (node) {
                    const it = buildItemFromNode(node);
                    if (it) staticItems.push(it);
                });
            }

            // build dynamic items from DOM (folio-items with data-updatable)
            function buildDynamicItems() {
                dynamicItems = [];
                const nodes = document.querySelectorAll('.folio-item[data-updatable]');
                nodes.forEach(function (node) {
                    const it = buildItemFromNode(node);
                    if (it) dynamicItems.push(it);
                });
            }

            // combined items used to initialize PhotoSwipe
            function getCombinedItems() {
                return staticItems.concat(dynamicItems);
            }

            // open PhotoSwipe at index
            function openAtIndex(index) {
                const items = getCombinedItems();
                const options = {
                    index: index,
                    showHideOpacity: true
                };
                const lightBox = new PhotoSwipe(pswp, PhotoSwipeUI_Default, items, options);
                lightBox.init();
            }

            // click handler attached to each folio-item thumb (keeps original UX)
            function attachClickHandlers() {
                // Attach a click listener to each current folio-item thumb link.
                // The handler computes the index from the current DOM order so dynamic changes are respected.
                const folioItems = document.querySelectorAll(allFolioSelector);
                folioItems.forEach(function (folioItem) {
                    const thumbLink = folioItem.querySelector('.folio-item__thumb-link');
                    if (!thumbLink) return;

                    // Remove any previously attached handler marker to avoid double-binding
                    if (thumbLink._pswpBound) return;
                    thumbLink._pswpBound = true;

                    thumbLink.addEventListener('click', function (event) {
                        event.preventDefault();

                        // Build node lists in the same order as items arrays:
                        const staticNodes = Array.from(document.querySelectorAll('.folio-item:not([data-updatable="true"])'));
                        const dynamicNodes = Array.from(document.querySelectorAll('.folio-item[data-updatable="true"]'));
                        const combinedNodes = staticNodes.concat(dynamicNodes);

                        // Find the clicked folio-item's index in the combined list
                        const clickedFolio = this.closest('.folio-item');
                        const index = combinedNodes.indexOf(clickedFolio);

                        if (index === -1) return;

                        // Ensure arrays are up-to-date before opening
                        // staticItems are built once at init; dynamicItems are rebuilt here to reflect current DOM
                        buildDynamicItems();

                        openAtIndex(index);
                    });
                });
            }

            // Public-ish refresh function (exposed globally so you can call it after DOM updates)
            window.refreshPhotoswipeDynamicItems = function () {
                buildDynamicItems();
            };

            // Initialize: build arrays and attach handlers
            buildStaticItems();
            buildDynamicItems();
            attachClickHandlers();

        };  // end ssPhotoswipe


        /* video Lightbox
         * ------------------------------------------------------ */
        const ssVideoLightbox = function () {

            const videoLink = document.querySelector('.video-link');
            if (!videoLink) return;

            videoLink.addEventListener('click', function (event) {

                const vLink = this.getAttribute('href');
                const iframe = "<iframe src='" + vLink + "' frameborder='0'></iframe>";

                event.preventDefault();

                const instance = basicLightbox.create(iframe);
                instance.show()

            });

        }; // end ssVideoLightbox


        /* alert boxes
         * ------------------------------------------------------ */
        const ssAlertBoxes = function () {

            const boxes = document.querySelectorAll('.alert-box');

            boxes.forEach(function (box) {

                box.addEventListener('click', function (event) {
                    if (event.target.matches('.alert-box__close')) {
                        event.stopPropagation();
                        event.target.parentElement.classList.add('hideit');

                        setTimeout(function () {
                            box.style.display = 'none';
                        }, 500)
                    }
                });
            })

        }; // end ssAlertBoxes


        /* smoothscroll
         * ------------------------------------------------------ */
        const ssMoveTo = function () {

            const easeFunctions = {
                easeInQuad: function (t, b, c, d) {
                    t /= d;
                    return c * t * t + b;
                },
                easeOutQuad: function (t, b, c, d) {
                    t /= d;
                    return -c * t * (t - 2) + b;
                },
                easeInOutQuad: function (t, b, c, d) {
                    t /= d / 2;
                    if (t < 1) return c / 2 * t * t + b;
                    t--;
                    return -c / 2 * (t * (t - 2) - 1) + b;
                },
                easeInOutCubic: function (t, b, c, d) {
                    t /= d / 2;
                    if (t < 1) return c / 2 * t * t * t + b;
                    t -= 2;
                    return c / 2 * (t * t * t + 2) + b;
                }
            }

            const triggers = document.querySelectorAll('.smoothscroll');

            const moveTo = new MoveTo({
                tolerance: 0,
                duration: 1200,
                easing: 'easeInOutCubic',
                container: window
            }, easeFunctions);

            triggers.forEach(function (trigger) {
                moveTo.registerTrigger(trigger);
            });

        }; // end ssMoveTo

        /* copyright year
         * ------------------------------------------------------ */
        const ssCopyrightYear = function () {
            const yearEl = document.querySelector('.copyright-year');
            if (yearEl) {
                yearEl.textContent = new Date().getFullYear().toString();
            }
        }; // end ssCopyrightYear


        /* remember scroll position
         * ------------------------------------------------------ */
        const ssRememberScroll = function () {
            window.addEventListener("beforeunload", function () {
                localStorage.setItem("scrollPosition", String(window.scrollY));
            });

            // Save current scroll position before leaving the page
            window.addEventListener("beforeunload", function () {
                localStorage.setItem("scrollPosition", String(window.scrollY));
            });

            // Restore saved position after everything has loaded
            window.addEventListener("load", function () {
                const scrollPosition = localStorage.getItem("scrollPosition");
                if (scrollPosition === null) return;
                const targetPosition = parseInt(scrollPosition, 10);
                if (isNaN(targetPosition)) return;

                // Wait for the preloader/layout to finish
                setTimeout(function () {
                    const startPosition = window.scrollY;
                    const distance = targetPosition - startPosition;
                    const duration = 1200;
                    const startTime = performance.now();

                    // Same easing used by MoveTo
                    function easeInOutCubic(t) {
                        t /= 0.5;
                        if (t < 1) {
                            return 0.5 * t * t * t;
                        }
                        t -= 2;
                        return 0.5 * (t * t * t + 2);
                    }

                    function animateScroll(currentTime) {
                        const elapsed = currentTime - startTime;
                        const progress = Math.min(elapsed / duration, 1);
                        const easedProgress = easeInOutCubic(progress);
                        window.scrollTo(0, startPosition + (distance * easedProgress));
                        if (progress < 1) {
                            requestAnimationFrame(animateScroll);
                        } else {
                            // Only remove it once the restoration has completed
                            localStorage.removeItem("scrollPosition");
                        }
                    }

                    requestAnimationFrame(animateScroll);
                }, 300);
            });
        }; // end ssRememberScroll


        /* Initialize
         * ------------------------------------------------------ */
        (function ssInit() {

            ssPreloader();
            ssMobileMenu();
            ssScrollSpy();
            ssAnimateOnScroll();
            ssSwiper();
            ssPhotoswipe();
            ssVideoLightbox();
            ssAlertBoxes();
            ssMoveTo();
            ssCopyrightYear();
            ssRememberScroll();

        })();

    }

)
(document.documentElement);