(() => {
    const API = ((location.protocol === 'http:' || location.protocol === 'https:') ? location.origin : 'http://localhost:3000') + '/todos';
    const $ = id => document.getElementById(id);
    let todos = [], editingId = null, deletingId = null, loading = false, saving = false;
    const make = (tag, className, text) => {
        const node = document.createElement(tag); node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    };
    const today = () => new Intl.DateTimeFormat('sv-SE', {timeZone: 'Europe/Vienna', year: 'numeric', month:'2-digit', day:'2-digit'}).format(new Date());
    function controls() {
        for (const control of $('tasksPanel').querySelectorAll('input, button')) control.disabled = loading || saving;
        $('addButton').textContent = saving ? 'Speichert…' : editingId === null ? 'Hinzufügen' : 'Änderungen speichern';
        $('cancelEdit').hidden = editingId === null;
    }
    function resetForm() {
        editingId = null; $('todoinput').value = ''; $('todoDueDate').value = ''; controls();
    }
    function action(label, className, callback) {
        const button = make('button', className, label); button.type = 'button';
        button.addEventListener('click', callback); return button;
    }
    function renderTasks() {
        $('todoList').replaceChildren();
        $('todoCount').textContent = `${todos.length} ${todos.length === 1 ? 'Aufgabe' : 'Aufgaben'}`;
        if (!todos.length) $('todoList').append(make('li','empty','Noch keine Aufgaben. Füge oben deine erste Aufgabe hinzu.'));
        for (const todo of [...todos].sort((a,b) => (a.dueDate || '9999').localeCompare(b.dueDate || '9999'))) {
            const item = make('li','todo');
            const content = make('div','todo-content');
            content.append(make('span','todo-title',todo.title));
            if (todo.dueDate && /^\d{4}-\d{2}-\d{2}$/.test(todo.dueDate)) {
                const date = new Date(todo.dueDate + 'T12:00:00Z');
                if (Number.isFinite(date.getTime())) {
                    const overdue = todo.dueDate < today(), dueToday = todo.dueDate === today();
                    const label = (overdue ? 'Überfällig · ' : dueToday ? 'Heute fällig · ' : 'Fällig am ') + new Intl.DateTimeFormat('de-AT',{timeZone:'UTC',dateStyle:'medium'}).format(date);
                    const time = make('time','todo-due' + (overdue ? ' overdue' : dueToday ? ' due-today' : ''),label);
                    time.dateTime = todo.dueDate; content.append(time);
                }
            }
            const actions = make('div','todo-actions');
            if (deletingId === todo.id) {
                actions.append(action('Löschen bestätigen','danger-button',()=>deleteTodo(todo)),
                               action('Abbrechen','secondary-button',()=>{deletingId=null;renderTasks();}));
            } else {
                const edit = action('Bearbeiten','secondary-button',()=>{
                    editingId=todo.id; deletingId=null; $('todoinput').value=todo.title;
                    $('todoDueDate').value=todo.dueDate || ''; $('formMessage').textContent='';
                    renderTasks(); $('todoinput').focus();
                });
                edit.setAttribute('aria-label', 'Aufgabe bearbeiten: ' + todo.title);
                const remove = action('Löschen','danger-button',()=>{deletingId=todo.id;renderTasks();});
                remove.setAttribute('aria-label', 'Aufgabe löschen: ' + todo.title);
                actions.append(edit,remove);
            }
            item.append(content,actions); $('todoList').append(item);
        }
        controls();
    }
    async function request(url, options) {
        const response=await fetch(url, options);
        if (!response.ok) throw new Error('HTTP ' + response.status);
        return response;
    }
    async function loadTasks() {
        if (loading || saving) return;
        loading=true; controls(); $('todoCount').textContent='Lädt…';
        $('todoList').innerHTML='<li class="loading" role="status"><span class="spinner" aria-hidden="true"></span>Deine Aufgaben werden geladen…</li>';
        const minimumWait = new Promise(resolve=>setTimeout(resolve,1000));
        try {
            const data=await (await request(API)).json();
            if (!Array.isArray(data)) throw new Error('Invalid todos');
            await minimumWait; todos=data; renderTasks();
        } catch {
            await minimumWait; $('todoCount').textContent='Nicht geladen';
            const item=make('li','error','Aufgaben konnten nicht geladen werden. Prüfe den lokalen Server.');
            item.append(action('Erneut versuchen','',loadTasks)); $('todoList').replaceChildren(item);
        } finally { loading=false; controls(); }
    }
    async function saveTodo(event) {
        event.preventDefault();
        const title=$('todoinput').value.trim(); if (!title || loading || saving) return;
        const dueDate=$('todoDueDate').value || null;
        saving=true; controls(); $('formMessage').textContent='';
        const id=editingId;
        try {
            const response=await request(id===null ? API : API+'/'+encodeURIComponent(id), {
                method:id===null?'POST':'PATCH', headers:{'Content-Type':'application/json'}, body:JSON.stringify({title,dueDate})
            });
            const saved=await response.json();
            if (id===null) todos.push(saved); else todos=todos.map(todo=>todo.id===id?saved:todo);
            resetForm(); deletingId=null; renderTasks();
        } catch { $('formMessage').textContent='Die Aufgabe konnte nicht gespeichert werden. Deine Eingaben bleiben erhalten. Versuche es erneut.'; }
        finally { saving=false; controls(); $('todoinput').focus(); }
    }
    async function deleteTodo(todo) {
        if (loading || saving) return;
        saving=true; controls(); $('formMessage').textContent='';
        try {
            await request(API+'/'+encodeURIComponent(todo.id), {method:'DELETE'});
            todos=todos.filter(item=>item.id!==todo.id);
            if (editingId===todo.id) resetForm();
            deletingId=null; renderTasks();
        } catch { $('formMessage').textContent='Die Aufgabe konnte nicht gelöscht werden. Versuche es erneut.'; }
        finally { saving=false; controls(); }
    }
    $('todoForm').addEventListener('submit',saveTodo);
    $('cancelEdit').addEventListener('click',()=>{resetForm();$('formMessage').textContent='';});
    loadTasks();
})();
