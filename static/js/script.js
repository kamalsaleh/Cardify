function confirmDelete() {
  return confirm("Are you sure you want to delete it?");
}

addDeckEntries = async (deckId, flashcardIds, formID) => {
      
  // Save the current scroll position
  const scrollPosition = window.scrollY;
  sessionStorage.setItem('scrollPosition', scrollPosition);
  
  const url = `/add-deckentries/${deckId}/${flashcardIds.join(',')}`;
  
  const response = await fetch(url, {
    method: 'POST',
  });
  
  if (response.ok) {
    
    const form = document.getElementById(formID);
    
    if (form) {
      form.submit(); // Submit the form to reflect the changes
    } else {
      location.reload();
    }
  } else {
    alert('Failed to add deck entrie(s).');
  }
  
}

addDeckEntry = async (deckId, flashcardId, formID) => { addDeckEntries(deckId, [flashcardId], formID);}

deleteDeckEntries = async (deckId, flashcardIds, formID) => {
  
  // Save the current scroll position
  const scrollPosition = window.scrollY;
  sessionStorage.setItem('scrollPosition', scrollPosition);
  
  const url = `/delete-deckentries/${deckId}/${flashcardIds.join(',')}`;
  
  const response = await fetch(url, {
    method: 'POST',
  });
  
  if (response.ok) {
    
    const form = document.getElementById(formID);
    
    if (form) {
      form.submit(); // Submit the form to reflect the changes
    } else {
      location.reload();
    }
  } else {
    alert('Failed to delete deck entrie(s).');
  }
  
}

deleteDeckEntry = async (deckId, flashcardId, formID) => { deleteDeckEntries(deckId, [flashcardId], formID); }

deleteDeckTopicEntries = async (topicId, deckIds) => {
  
  // Save the current scroll position
  const scrollPosition = window.scrollY;
  sessionStorage.setItem('scrollPosition', scrollPosition);
  
  const url = `/delete-topicdeckentries/${topicId}/${deckIds.join(',')}`;
  
  const response = await fetch(url, {
    method: 'POST',
  });
  
  if (response.ok) {
    location.reload();
  } else {
    alert('Failed to delete topic tag entrie(s).');
  }
  
}

deleteDeckTopicEntry = async (topicId, deckId) => { deleteDeckTopicEntries(topicId, [deckId]); }

function toggleSearchForm() {
  const searchForm = document.getElementById("searchForm");
  
  // Toggle form visibility
  document.addEventListener("DOMContentLoaded", function () {
    const toggleFormBtn = document.getElementById("toggleFormBtn");
    
    toggleFormBtn.addEventListener("click", function () {
      // Toggle the form's visibility
      if (searchForm.style.display === "none") {
        searchForm.style.display = "block";
        // toggleFormBtn.textContent = "Hide Forms";
        toggleFormBtn.innerHTML = '<i class="fas fa-toggle-on"></i>'
      } else {
        searchForm.style.display = "none";
        //toggleFormBtn.textContent = "Show Forms";
        toggleFormBtn.innerHTML = '<i class="fas fa-toggle-off"></i>'
      }
    });
  });
}
