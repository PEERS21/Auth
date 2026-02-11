document.getElementById('get').onsubmit = async function(e) {
    e.preventDefault();
    const btn_get = document.getElementById('btn_get');
    btn_get.classList.add('clicked_btn');
    btn_get.innerText = 'Отправили ;]';
    const login = document.getElementById('login').value;
    const state = document.getElementById('state_get').value;
    if (!login) { alert('Впишите логин'); btn_get.classList.remove('clicked_btn'); return; }

    const unlockAudio = new Audio();
    unlockAudio.volume = 0;
    unlockAudio.play().catch(() => {});

    const resp = await fetch('/send_code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ state, login }),
        credentials: 'include'
    });
    const j = await resp.json();
    if (!resp.ok) {
        btn_get.classList.remove('clicked_btn');
        alert((j.error || JSON.stringify(j)));
        return;
    }
    if (j.blacklisted) {
        const audioUrl = '/auth/static/blocked.mp3';

        // Флаг, чтобы не создавать несколько fetch'ей/объектов
        let objectUrl = null;
        let listener = null;

        // Загрузим аудио заранее (без кэширования) — чтобы при клике не ждать загрузки
        (async () => {
            try {
                const resp = await fetch(audioUrl + '?_cb=' + Date.now(), { cache: 'no-store', credentials: 'include' });
                if (!resp.ok) {
                    console.warn('Audio fetch failed', resp.status);
                    return;
                }
                const blob = await resp.blob();
                objectUrl = URL.createObjectURL(blob);
            } catch (err) {
                console.warn('Audio preload error', err);
                objectUrl = null;
            }
        })();

        const src = objectUrl || (audioUrl + '?_cb=' + Date.now());
        unlockAudio.src = src;
        unlockAudio.volume = 0.2;

        unlockAudio.play().catch(err => {
            console.warn('Audio play failed even after unlock:', err);
            document.addEventListener('click', function playFallback() {
                document.removeEventListener('click', playFallback);
                unlockAudio.play().catch(err2 => console.error('Fallback play failed:', err2));
            }, { once: true });
        });

        btn_get.innerText = 'Вас никто не услышал...';
        btn_get.classList.remove('clicked_btn');
        btn_get.classList.add('ban_btn');
        btn_get.id = 'u_banned';
        const btn_verif = document.getElementById('btn_verif');
        btn_verif.id = 'u_banned2';
        btn_verif.classList.add('ban_btn');
        alert((j.error || JSON.stringify(j)));
        return;
    }
    document.getElementById("state_verif").value = j.state;
};
document.getElementById('verif').onsubmit = async function(e) {
    e.preventDefault();
    const btn_verif = document.getElementById('btn_verif');
    btn_verif.classList.add('clicked_btn');
    const code = document.getElementById('code').value;
    const state = document.getElementById('state_verif').value;
    const login = document.getElementById('login').value;
    if (!code) { alert('Впишите код'); return; }
    const resp = await fetch('/verif_code', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ state, login, code }), credentials: 'include' });
    const j = await resp.json();
    if (!resp.ok) { btn_verif.classList.remove('clicked_btn'); alert((j.error || JSON.stringify(j))); return; }
    const next = j.next || '/';
    window.location.href = next;
    btn_verif.innerText = 'Ждём подтверждения';
};
