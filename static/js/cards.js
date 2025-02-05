const card = document.getElementById('card');
let angle = 0;

// Left click event
card.addEventListener('click', () => {
    angle += 120;
    card.style.transform = `rotateX(${angle}deg)`;
});

// Right click event
card.addEventListener('contextmenu', (event) => {
    event.preventDefault(); // Prevent the context menu from appearing
    angle -= 120;
    card.style.transform = `rotateX(${angle}deg)`;
});

document.addEventListener('keydown', function(event) {
    // Check if the key pressed is "ctrl + ArrowUp"
    if ( (event.altKey) && event.key === 'ArrowUp') {
      event.preventDefault(); // Prevent any default behavior (if any)
      document.getElementById('card').click();
    }
    
    const right_click = new MouseEvent('contextmenu', {
      bubbles: true,      // Allows the event to bubble up through the DOM
      cancelable: true,   // Allows the event to be canceled
      view: window,       // Sets the event’s view to the current window
      button: 2           // Indicates the right mouse button
    });
    
    // Check if the key pressed is "ctrl + ArrowDown"
    if ( (event.altKey) && event.key === 'ArrowDown') {
      event.preventDefault(); // Prevent any default behavior (if any)
      document.getElementById('card').dispatchEvent(right_click);
    }
});