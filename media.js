(() => {
    const $ = id => document.getElementById(id);
    let photos = [], tracks = [], photoIndex = 0, trackIndex = 0, rotation;
    const audio = $('backgroundMusic');
    audio.volume = 0.25;
    let stopped = false, needsGesture = false;
    function gestureStart(event) {
        if(stopped || !needsGesture || event.target.closest('#musicPanel'))return;
        if(tracks.length)play();
    }
    document.addEventListener('click',gestureStart);
    document.addEventListener('keydown',gestureStart);
    function showPhoto() {
        if (!photos.length) return;
        $('familyPhoto').src = photos[photoIndex].src;
        $('familyPhoto').alt = photos[photoIndex].title || 'Unser Foto';
        $('photoCount').textContent = `${photoIndex+1} / ${photos.length}`;
    }
    function rotate() { clearInterval(rotation); rotation = setInterval(()=>{photoIndex=(photoIndex+1)%photos.length;showPhoto();},20000); }
    function loadTrack() {
        audio.src = tracks[trackIndex].src;
        $('musicTrack').textContent = tracks[trackIndex].title;
        $('musicTrack').title = tracks[trackIndex].title;
        $('musicStatus').textContent = 'Lokale Musik';
    }
    async function play() {
        try { await audio.play(); needsGesture=false; } catch(error) { needsGesture=error.name==='NotAllowedError'; $('musicStatus').textContent = needsGesture ? 'Autoplay blockiert · Musik starten.' : 'Wiedergabe nicht möglich. Musikformat und TV-Browser prüfen.'; }
    }
    $('musicToggle').addEventListener('click',()=>{ if(audio.paused){stopped=false;play();}else{stopped=true;needsGesture=false;audio.pause();} });
    audio.addEventListener('play',()=>{$('musicToggle').textContent='Musik pausieren';});
    audio.addEventListener('pause',()=>{$('musicToggle').textContent='Musik starten';});
    audio.addEventListener('ended',()=>{trackIndex=(trackIndex+1)%tracks.length;loadTrack();play();});
    audio.addEventListener('error',()=>{$('musicStatus').textContent='Musikdatei konnte nicht geladen werden.';});
    $('musicVolume').addEventListener('input',event=>{audio.volume=Number(event.target.value);});
    $('nextPhoto').addEventListener('click',()=>{photoIndex=(photoIndex+1)%photos.length;showPhoto();});
    $('pausePhotos').addEventListener('click',()=>{
        if(rotation){clearInterval(rotation);rotation=null;$('pausePhotos').textContent='Diashow starten';}
        else {rotate();$('pausePhotos').textContent='Diashow pausieren';}
    });
    fetch('media-list.json', {cache:'no-store'}).then(response=>{if(!response.ok)throw new Error();return response.json();}).then(data=>{
        photos=Array.isArray(data.photos)?data.photos:[]; tracks=Array.isArray(data.tracks)?data.tracks:[];
        $('familyMedia').hidden=!photos.length;
        $('musicPanel').hidden=!tracks.length;
        $('photoStatus').textContent=photos.length ? '' : 'Noch keine Fotos gefunden. Bilder im NAS-Ordner media/photos ablegen.';
        document.querySelector('main').classList.toggle('has-photos',!!photos.length);
        if(photos.length){showPhoto();rotate();}
        if(tracks.length)loadTrack();
        needsGesture=true;
        if(tracks.length)play();
    }).catch(()=>{ $('photoStatus').textContent='Fotos konnten nicht geladen werden. Medienordner und Dateirechte prüfen.'; });
})();
