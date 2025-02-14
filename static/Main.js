document.addEventListener("DOMContentLoaded", function () {
    var swiper = new Swiper("#bg-slider", {
        effect: "slide", // Enables sliding transition
        speed: 1500, // Smooth transition speed
        autoplay: {
            delay: 4000, // Change slides every 4 seconds
            disableOnInteraction: false, // Keeps auto-swiping after user interaction
        },
        loop: true, // Infinite looping
        slidesPerView: 1, // Show only one slide at a time
        spaceBetween: 0, // No extra spacing between slides
        navigation: false, // No navigation buttons
    });

    console.log("Swiper initialized:", swiper); // Debugging check
});
