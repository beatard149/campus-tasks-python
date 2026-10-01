// @ts-check
const STORAGE_KEY = 'campus-tasks-v1';
/** @typedef {{ id: string, text: string, completed: boolean }} Task */
/** @type {Task[]} */
let tasks = readTasks();
let filter = 'all';
let editingId = null;

const form = document.querySelector('#add-form');
const newTask = /** @type {HTMLInputElement} */ (document.querySelector('#new-task'));
const list = document.querySelector('#task-list');
const validation = document.querySelector('#validation');
const clearButton = /** @type {HTMLButtonElement} */ (document.querySelector('#clear-completed'));

function readTasks() {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    return Array.isArray(stored) ? stored.filter(task => typeof task.id === 'string' && typeof task.text === 'string' && typeof task.completed === 'boolean') : [];
  } catch { return []; }
}

// Workshop regression: this number must count only unfinished tasks.
function remainingCount(tasks) {
  return tasks.length;
}

function saveAndRender() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks));
  render();
}

function actionButton(label, accessibleName, action) {
  const button = document.createElement('button');
  button.type = 'button';
  button.textContent = label;
  button.setAttribute('aria-label', accessibleName);
  button.addEventListener('click', action);
  return button;
}

function render() {
  list.replaceChildren();
  const visibleTasks = tasks.filter(task => filter === 'all' || (filter === 'completed' ? task.completed : !task.completed));
  for (const task of visibleTasks) {
    const item = document.createElement('li');
    item.dataset.testid = 'task-item';
    if (task.completed) item.className = 'completed';
    if (editingId === task.id) {
      const editInput = document.createElement('input');
      editInput.className = 'edit-input';
      editInput.value = task.text;
      editInput.setAttribute('aria-label', 'Edit task');
      const save = () => {
        const text = editInput.value.trim();
        if (!text) { editInput.setAttribute('aria-invalid', 'true'); return; }
        task.text = text;
        editingId = null;
        saveAndRender();
      };
      editInput.addEventListener('keydown', event => {
        if (event.key === 'Enter') save();
        if (event.key === 'Escape') { editingId = null; render(); }
      });
      item.append(editInput, actionButton('Save', 'Save', save), actionButton('Cancel', 'Cancel', () => { editingId = null; render(); }));
    } else {
      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.checked = task.completed;
      checkbox.setAttribute('aria-label', `Complete ${task.text}`);
      checkbox.addEventListener('change', () => { task.completed = checkbox.checked; saveAndRender(); });
      const text = document.createElement('span');
      text.className = 'task-text';
      text.dataset.testid = 'task-title';
      text.textContent = task.text;
      const actions = document.createElement('div');
      actions.className = 'row-actions';
      actions.append(actionButton('Edit', `Edit ${task.text}`, () => {
        editingId = task.id;
        render();
        document.querySelector('input[aria-label="Edit task"]').focus();
      }), actionButton('Delete', `Delete ${task.text}`, () => { tasks = tasks.filter(entry => entry.id !== task.id); saveAndRender(); }));
      item.append(checkbox, text, actions);
    }
    list.append(item);
  }
  document.querySelector('[data-testid="remaining-count"]').textContent = String(remainingCount(tasks));
  document.querySelector('#list-summary').textContent = `${tasks.length} ${tasks.length === 1 ? 'task' : 'tasks'} in total`;
  document.querySelector('#empty-state').hidden = visibleTasks.length !== 0;
  clearButton.disabled = !tasks.some(task => task.completed);
  document.querySelectorAll('[data-filter]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.filter === filter)));
}

form.addEventListener('submit', event => {
  event.preventDefault();
  const text = newTask.value.trim();
  if (!text) {
    validation.textContent = 'Enter a task before adding it.';
    validation.hidden = false;
    newTask.setAttribute('aria-invalid', 'true');
    return;
  }
  validation.hidden = true;
  newTask.removeAttribute('aria-invalid');
  tasks.push({ id: crypto.randomUUID(), text, completed: false });
  newTask.value = '';
  filter = 'all';
  saveAndRender();
  newTask.focus();
});
document.querySelectorAll('[data-filter]').forEach(button => button.addEventListener('click', () => { filter = button.dataset.filter; editingId = null; render(); }));
clearButton.addEventListener('click', () => { tasks = tasks.filter(task => !task.completed); saveAndRender(); });
document.querySelector('#get-tip').addEventListener('click', async () => {
  const tip = document.querySelector('#study-tip');
  tip.textContent = 'Loading study tip…';
  try {
    const response = await fetch('/api/study-tip');
    if (!response.ok) throw new Error('Study tip request failed');
    const data = await response.json();
    tip.textContent = data.tip;
  } catch { tip.textContent = 'Could not load a tip. Try again.'; }
});
render();
