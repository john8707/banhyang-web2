window.onload = function() {
    // YOUTUBE IFRAME API
    var tag = document.createElement('script');
    tag.src = "https://www.youtube.com/iframe_api";
    var firstScriptTag = document.getElementsByTagName('script')[0];
    firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

    // LOAD YOUTUBE PLAYERS

    const carouselSlide = document.querySelector('.carousel-slide');


    let youtubeId = ['dtryk5gc4lk', '2TjpqULYZ7k', '_5Suj0cWkAo', '7seP0CWp79E'];
    
    for (var i in youtubeId) {
        var youtubeContainer = document.createElement('div');
        youtubeContainer.className = 'youtube-container';

        var substitute = document.createElement('div');
        substitute.id = 'yt-' + i;
        youtubeContainer.appendChild(substitute)
        carouselSlide.appendChild(youtubeContainer);
    }
    window.onYouTubeIframeAPIReady = function() {
        
        var players = [];

        for (var i in youtubeId){
            players[i] = new YT.Player('yt-' + i,{
                videoId : youtubeId[i],
                playerVars : {
                    rel : 0
                }
            });
        }

        const carouselYoutubes = document.querySelectorAll('.youtube-container');
        const btnPrev = document.querySelector('#btnPrev');
        const btnNext = document.querySelector('#btnNext');

        let size = carouselYoutubes[0].clientWidth;

        let counter = 0;

        btnNext.addEventListener('click', () => {
            players[counter].pauseVideo();
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
            players[counter].pauseVideo();
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




        window.onresize = function() {
            size = carouselYoutubes[0].clientWidth;
            carouselSlide.style.transition = null

            carouselSlide.style.transform = 'translateX(' + (-counter * size) +'px)';

        }
    
    }


};
