window.onload = function() {
    const carouselSlide = document.querySelector('.carousel-slide');
    const carouselYoutubes = document.querySelectorAll('.youtube-container');

    const btnPrev = document.querySelector('#btnPrev');
    const btnNext = document.querySelector('#btnNext');
    const size = carouselYoutubes[0].clientWidth;
    let counter = 0;

    btnNext.addEventListener('click', () => {
        if(counter >= 0 && counter <= carouselYoutubes.length -1) {
            btnPrev.style.visibility = 'visible';
            counter += 1;
            carouselSlide.style.transition = 'transform 0.4s ease-in-out';
            carouselSlide.style.transform = 'translateX(' + (-counter * size) +'px)';
        }
        else return;

        if(counter == carouselYoutubes.length -1){
            btnNext.style.visibility = 'hidden';
        }

    });

    btnPrev.addEventListener('click', () => {
        if(counter > 0 && counter <= carouselYoutubes.length) {
            btnNext.style.visibility = 'visible';
            counter -= 1;
            carouselSlide.style.transition = 'transform 0.4s ease-in-out';
            carouselSlide.style.transform = 'translateX(' + (-counter * size) +'px)';
        }
        else return;

        if(counter == 0){
            btnPrev.style.visibility = 'hidden';
        }

    });
};