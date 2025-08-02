
document.addEventListener('click', function(event) {
  const el = event.target;
  const locators = {
    'data-testid': el.getAttribute('data-testid'),
    'id': el.id,
    'class': el.className,
    'role': el.getAttribute('role'),
    'name': el.getAttribute('name'),
    'text': el.textContent.trim()
  };
  window.__recordedLocators = window.__recordedLocators || [];
  window.__recordedLocators.push(locators);
});
