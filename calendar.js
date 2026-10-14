/* Calendar dates are civil dates in Vienna; UTC arithmetic avoids DST drift. */
const CalendarDates = (() => {
    const zone = 'Europe/Vienna';
    const key = date => new Intl.DateTimeFormat('sv-SE', { timeZone: zone, year: 'numeric', month: '2-digit', day: '2-digit' }).format(date);
    const parse = value => new Date(value + 'T12:00:00Z');
    const shift = (value, days) => { const date = parse(value); date.setUTCDate(date.getUTCDate() + days); return date.toISOString().slice(0, 10); };
    const weekStart = value => shift(value, -((parse(value).getUTCDay() + 6) % 7));
    const label = (value, options = {}) => new Intl.DateTimeFormat('de-AT', { timeZone: 'UTC', day: 'numeric', month: 'long', ...options }).format(parse(value));
    function holidays(year) {
        const result = new Map();
        for (const [suffix, name] of [['01-01','Neujahr'],['01-06','Heilige Drei Könige'],['05-01','Staatsfeiertag'],['08-15','Mariä Himmelfahrt'],['10-26','Nationalfeiertag'],['11-01','Allerheiligen'],['12-08','Mariä Empfängnis'],['12-25','Christtag'],['12-26','Stefanitag']]) result.set(`${year}-${suffix}`, name);
        const a = year % 19, b = Math.floor(year / 100), c = year % 100;
        const d = Math.floor(b / 4), e = b % 4, f = Math.floor((b + 8) / 25), g = Math.floor((b - f + 1) / 3);
        const h = (19 * a + b - d - g + 15) % 30, i = Math.floor(c / 4), k = c % 4;
        const l = (32 + 2 * e + 2 * i - h - k) % 7, m = Math.floor((a + 11 * h + 22 * l) / 451);
        const month = Math.floor((h + l - 7 * m + 114) / 31), day = (h + l - 7 * m + 114) % 31 + 1;
        const easter = `${year}-${String(month).padStart(2,'0')}-${String(day).padStart(2,'0')}`;
        for (const [offset, name] of [[1,'Ostermontag'],[39,'Christi Himmelfahrt'],[50,'Pfingstmontag'],[60,'Fronleichnam']]) result.set(shift(easter, offset), name);
        return result;
    }
    function onDay(event, day) {
        const start = new Date(event.startAt), end = new Date(event.endAt || event.startAt);
        if (!Number.isFinite(start.getTime())) return false;
        const last = end > start ? new Date(end.getTime() - 1) : start;
        return key(start) <= day && key(last) >= day;
    }
    function uniqueEvents(events) {
        const seen = new Set();
        return events.filter(event => {
            const key = JSON.stringify([event.source,event.calendarId,event.externalId ?? event.id,event.startAt]);
            if (seen.has(key)) return false;
            seen.add(key); return true;
        });
    }
    const reminderKey = event => `${event.id || event.externalId || event.title}|${event.startAt}`;
    const reminderDue = (event, now) => {
        const remaining = new Date(event.startAt).getTime() - now;
        return !event.allDay && remaining > 0 && remaining <= 30 * 60 * 1000;
    };
    return { zone, key, parse, shift, weekStart, label, holidays, onDay, uniqueEvents, reminderKey, reminderDue };
})();
if (typeof module !== 'undefined') module.exports = CalendarDates;

if (typeof document !== 'undefined') (() => {
    const $ = id => document.getElementById(id);
    let today = CalendarDates.key(new Date());
    let selected = today, year = Number(today.slice(0,4)), view = 'day', events = [], loaded = false;
    let timer;
    let lastMinute;
    const reminderStorageKey = 'timetree-reminders-v1';
    let reminded = {};
    try { reminded = JSON.parse(sessionStorage.getItem(reminderStorageKey) || '{}');
        if (!reminded || typeof reminded !== 'object' || Array.isArray(reminded)) reminded = {};
    } catch { reminded = {}; }
    let reminderTimer;
    const make = (tag, className, text) => { const node = document.createElement(tag); node.className = className; if (text !== undefined) node.textContent = text; return node; };
    const forDay = day => events.filter(event => event.dayStart <= day && event.dayEnd >= day).sort((a,b) => Number(b.allDay) - Number(a.allDay) || new Date(a.startAt) - new Date(b.startAt));
    function pause() { $('autoView').checked = false; clearTimeout(timer); }
    function select(day) {
        if (!/^\d{4}-\d{2}-\d{2}$/.test(day) || !Number.isFinite(CalendarDates.parse(day).getTime())) return;
        pause(); selected = day; year = Number(day.slice(0,4)); view = 'day'; render();
    }
    function scheduleSwitch() {
        clearTimeout(timer);
        if (!$('autoView').checked) return;
        timer = setTimeout(() => {
            selected = CalendarDates.key(new Date()); year = Number(selected.slice(0,4));
            view = view === 'day' ? 'week' : 'day'; render(); scheduleSwitch();
        }, 60 * 1000);
    }
    function entry(event, day, next) {
        const past = day === today && !event.allDay && new Date(event.endAt || event.startAt) <= new Date();
        const node = make('li', 'agenda-entry' + (next ? ' next-event' : '') + (event.recurrences?.length ? ' recurring-event' : '') + (event.allDay ? ' all-day-event' : '') + (past ? ' past-event' : ''));
        const start = new Date(event.startAt);
        const continuing = CalendarDates.key(start) < day;
        const time = make('time', event.allDay || continuing ? 'time-label' : '', event.allDay ? 'Ganztägig' : continuing ? 'Fortlaufend' : new Intl.DateTimeFormat('de-AT', { timeZone: CalendarDates.zone, hour:'2-digit', minute:'2-digit' }).format(start));
        time.dateTime = event.startAt;
        const content = make('div',''); content.append(make('strong','',event.title));
        if (next) content.append(make('small','', 'Nächster Termin'));
        if (event.recurrences?.length) content.append(make('small','', 'Serientermin · Ausgangstermin'));
        node.append(time,content); return node;
    }
    function agenda(day, compact) {
        const node = make('div', compact ? '' : 'day-agenda');
        const holiday = CalendarDates.holidays(Number(day.slice(0,4))).get(day);
        if (holiday) node.append(make('p','holiday-banner', holiday));
        const items = forDay(day);
        if (!compact && items.length >= 6) node.classList.add('compact-agenda');
        if (!compact && items.length >= 10) node.classList.add('dense-agenda');
        if (!items.length) node.append(make('p','empty', loaded ? 'Keine Termine' : 'Termine noch nicht geladen'));
        const next = day === today ? items.find(event => !event.allDay && new Date(event.startAt) >= new Date()) : null;
        const groups = compact ? [['', items]] : [['Ganztägig', items.filter(event=>event.allDay)], ['Termine', items.filter(event=>!event.allDay)]];
        for (const [heading, group] of groups) {
            if (!group.length) continue;
            if (heading) node.append(make('h3', 'agenda-section-label', heading));
            const list = make('ul','agenda-list');
            for (const event of group) list.append(entry(event, day, event === next));
            node.append(list);
        }
        return node;
    }
    function renderYear() {
        $('yearHeading').textContent = String(year);
        $('yearGrid').replaceChildren();
        const holidays = CalendarDates.holidays(year);
        for (let month = 0; month < 12; month++) {
            const section = make('section','month');
            const prefix = `${year}-${String(month+1).padStart(2,'0')}`;
            section.append(make('h3','',CalendarDates.label(prefix+'-01',{month:'long',day:undefined})));
            const grid = make('div','month-grid');
            for (const weekday of ['Mo','Di','Mi','Do','Fr','Sa','So']) grid.append(make('span','weekday',weekday));
            const offset = (CalendarDates.parse(prefix+'-01').getUTCDay()+6)%7;
            for(let j=0;j<offset;j++) grid.append(make('span',''));
            const days = new Date(Date.UTC(year,month+1,0)).getUTCDate();
            for(let day=1;day<=days;day++) {
                const date = prefix+'-'+String(day).padStart(2,'0'), holiday=holidays.get(date), dayEvents=forDay(date), count=dayEvents.length;
                const weekend=(offset+day-1)%7>=5;
                const button=make('button','calendar-date'+(weekend?' weekend':'')+(holiday?' holiday':'')+(date===today?' today':'')+(date===selected?' selected':'')+(count?' has-events':'')+(dayEvents.some(event=>event.recurrences?.length)?' has-recurring':''),String(day));
                button.type='button'; button.setAttribute('aria-pressed',String(date===selected));
                const description=CalendarDates.label(date,{year:'numeric'})+(holiday?' · '+holiday:'')+(count?` · ${count} Termine`:'');
                button.setAttribute('aria-label',description); button.title=description;
                if(date===today) button.setAttribute('aria-current','date');
                button.addEventListener('click',()=>select(date)); grid.append(button);
            }
            section.append(grid); $('yearGrid').append(section);
        }
    }
    function render() {
        const summary = $('nextAppointment');
        summary.hidden = view !== 'day' || selected !== today || !loaded;
        summary.replaceChildren();
        summary.className = 'next-appointment';
        if (!summary.hidden) {
            const now = new Date();
            const timed = forDay(today).filter(event=>!event.allDay);
            const ongoing = timed.find(event=>new Date(event.startAt)<=now && new Date(event.endAt)>now);
            const next = ongoing || timed.find(event=>new Date(event.startAt)>now);
            if (next) {
                const minutes = Math.ceil((new Date(next.startAt)-now)/60000);
                const time = new Intl.DateTimeFormat('de-AT',{timeZone:CalendarDates.zone,hour:'2-digit',minute:'2-digit'}).format(new Date(next.startAt));
                summary.append(make('span','next-caption',ongoing ? 'Jetzt läuft · '+time : `Als Nächstes · ${time} · In ${minutes} Minuten`),make('strong','',next.title));
                if (next.recurrences?.length) summary.classList.add('recurring-event');
            } else summary.append(make('strong','', 'Für heute keine weiteren Termine'));
        }
        $('selectedDate').value=selected;
        $('dayView').setAttribute('aria-pressed',String(view==='day'));
        $('weekView').setAttribute('aria-pressed',String(view==='week'));
        $('previousDate').setAttribute('aria-label',view==='day'?'Vorheriger Tag':'Vorherige Woche');
        $('nextDate').setAttribute('aria-label',view==='day'?'Nächster Tag':'Nächste Woche');
        $('schedule').replaceChildren();
        if(view==='day') {
            $('calendarHeading').textContent=(selected===today?'Heute · ':'')+CalendarDates.label(selected,{weekday:'long',year:'numeric'});
            $('schedule').append(agenda(selected,false));
        } else {
            const start=CalendarDates.weekStart(selected);
            $('calendarHeading').textContent=`Woche · ${CalendarDates.label(start)} – ${CalendarDates.label(CalendarDates.shift(start,6),{year:'numeric'})}`;
            const grid=make('div','week-grid');
            for(let i=0;i<7;i++) {
                const day=CalendarDates.shift(start,i), column=make('section','week-day'+(day===today?' is-today':''));
                const button=make('button','week-date',CalendarDates.label(day,{weekday:'short',day:undefined,month:undefined}));
                button.type='button'; button.append(make('span','',day.slice(8))); button.addEventListener('click',()=>select(day));
                column.append(button,agenda(day,true)); grid.append(column);
            }
            $('schedule').append(grid);
        }
        renderYear();
    }
    async function loadEvents() {
        if($('refreshEvents').disabled) return;
        $('refreshEvents').disabled=true; $('calendarStatus').textContent='Termine werden geladen…';
        try {
            const response=await fetch(((location.protocol === 'http:' || location.protocol === 'https:') ? location.origin : 'http://localhost:3000') + '/events');
            if(response.status===404) { $('calendarStatus').textContent='Noch nicht synchronisiert. Die Termine erscheinen nach dem ersten Import.'; return; }
            if(!response.ok) throw new Error('HTTP '+response.status);
            const data=await response.json(); if(!Array.isArray(data)) throw new Error('Invalid events');
            events=CalendarDates.uniqueEvents(data.filter(event=>event.source==='timetree'))
                .filter(event=>Number.isFinite(new Date(event.startAt).getTime()))
                .map(event=>{
                    const start=new Date(event.startAt), end=new Date(event.endAt || event.startAt);
                    const last=end>start?new Date(end.getTime()-1):start;
                    return {...event, dayStart:CalendarDates.key(start), dayEnd:CalendarDates.key(last)};
                }); loaded=true;
            $('calendarStatus').textContent='Gespeicherter TimeTree-Stand · '+events.length+' Termine';
            render();
            checkReminders();
            try {
                const metadata=await fetch(((location.protocol === 'http:' || location.protocol === 'https:') ? location.origin : 'http://localhost:3000') + '/timeTreeSync');
                if(metadata.ok) {
                    const sync=await metadata.json();
                    if(sync.lastSyncedAt&&Number.isFinite(new Date(sync.lastSyncedAt).getTime())) $('calendarStatus').textContent='Letzter Import: '+new Intl.DateTimeFormat('de-AT',{timeZone:CalendarDates.zone,dateStyle:'medium',timeStyle:'short'}).format(new Date(sync.lastSyncedAt));
                }
            } catch { /* The saved events remain useful without sync metadata. */ }
        } catch { $('calendarStatus').textContent='Termine konnten nicht geladen werden. Prüfe den lokalen Server. Der letzte geladene Stand bleibt sichtbar.'; }
        finally { $('refreshEvents').disabled=false; }
    }
    $('dayView').addEventListener('click',()=>{pause();view='day';render();});
    $('weekView').addEventListener('click',()=>{pause();view='week';render();});
    $('selectedDate').addEventListener('change',event=>select(event.target.value));
    $('previousDate').addEventListener('click',()=>{pause();selected=CalendarDates.shift(selected,view==='day'?-1:-7);year=Number(selected.slice(0,4));render();});
    $('nextDate').addEventListener('click',()=>{pause();selected=CalendarDates.shift(selected,view==='day'?1:7);year=Number(selected.slice(0,4));render();});
    $('goToday').addEventListener('click',()=>{selected=CalendarDates.key(new Date());year=Number(selected.slice(0,4));view='day';render();scheduleSwitch();});
    for (const [buttonId,panelId] of [['toggleYear','yearPanel'],['toggleTasks','tasksPanel']]) {
        $(buttonId).addEventListener('click',()=>{
            const panel=$(panelId); panel.hidden=!panel.hidden;
            $(buttonId).setAttribute('aria-expanded',String(!panel.hidden));
            if (!panel.hidden) panel.scrollIntoView({block:'start'});
        });
    }
    $('autoView').addEventListener('change',()=>{if($('autoView').checked){selected=today;year=Number(today.slice(0,4));render();}scheduleSwitch();});
    $('previousYear').addEventListener('click',()=>{pause();year--;renderYear();});
    $('nextYear').addEventListener('click',()=>{pause();year++;renderYear();});
    $('refreshEvents').addEventListener('click',loadEvents);
    function closeReminder() {
        clearTimeout(reminderTimer);
        $('eventReminder').hidden = true;
        $('reminderItems').replaceChildren();
    }
    function checkReminders() {
        const now = Date.now();
        const due = events.filter(event => CalendarDates.reminderDue(event, now) && !reminded[CalendarDates.reminderKey(event)])
            .sort((a,b) => new Date(a.startAt) - new Date(b.startAt));
        if (!due.length) return;
        if ($('eventReminder').hidden) $('reminderItems').replaceChildren();
        for (const event of due) {
            reminded[CalendarDates.reminderKey(event)] = new Date(event.startAt).getTime();
            const item = make('li', 'reminder-item' + (event.recurrences?.length ? ' recurring-event' : ''));
            const remaining = Math.ceil((new Date(event.startAt) - now) / 60000);
            item.append(make('strong', '', event.title), make('span', '', `In ${remaining} Minuten · ` +
                new Intl.DateTimeFormat('de-AT', {timeZone:CalendarDates.zone, hour:'2-digit',minute:'2-digit'}).format(new Date(event.startAt))));
            $('reminderItems').append(item);
        }
        reminded = Object.fromEntries(Object.entries(reminded).filter(([,start]) => Number.isFinite(start) && start > now - 86400000));
        try { sessionStorage.setItem(reminderStorageKey, JSON.stringify(reminded)); } catch { /* In-memory deduplication remains active. */ }
        $('eventReminder').hidden = false;
        clearTimeout(reminderTimer);
        reminderTimer = setTimeout(closeReminder, 20000);
    }
    $('dismissReminder').addEventListener('click', closeReminder);
    document.addEventListener('visibilitychange', () => { if (!document.hidden) { tick(); checkReminders(); } });
    function tick() {
        const now=new Date(); $('clock').textContent=new Intl.DateTimeFormat('de-AT',{timeZone:CalendarDates.zone,hour:'2-digit',minute:'2-digit',second:'2-digit'}).format(now);
        $('todayLabel').textContent=CalendarDates.label(CalendarDates.key(now),{weekday:'long',year:'numeric'});
        const current=CalendarDates.key(now);
        if(current!==today) { const previousToday=today; today=current; if(selected===previousToday||$('autoView').checked){selected=today;year=Number(today.slice(0,4));view='day';scheduleSwitch();} render(); }
        const minute=Math.floor(now.getTime()/60000);
        if(minute!==lastMinute) { lastMinute=minute; render(); }
        checkReminders();
    }
    tick(); render(); scheduleSwitch(); loadEvents(); setInterval(tick,1000); setInterval(loadEvents,60000);
})();
