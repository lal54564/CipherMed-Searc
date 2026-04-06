document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const uploadBtn = document.getElementById('upload-btn');
    const uploadText = document.getElementById('upload-text');
    const searchBtn = document.getElementById('search-btn');
    const searchQuery = document.getElementById('search-query');
    const resetBtn = document.getElementById('reset-btn');
    
    const dbTable = document.getElementById('db-table');
    const dbBody = document.getElementById('db-body');
    const emptyState = document.getElementById('empty-state');
    
    const resultBox = document.getElementById('result-box');
    const resId = document.getElementById('res-id');
    const resScore = document.getElementById('res-score');
    const resText = document.getElementById('res-text');

    // Fetch and display Database
    const fetchDatabase = async () => {
        try {
            const res = await fetch('/api/database');
            const data = await res.json();
            
            dbBody.innerHTML = '';
            
            if (data.database.length === 0) {
                dbTable.style.display = 'none';
                emptyState.style.display = 'block';
            } else {
                dbTable.style.display = 'table';
                emptyState.style.display = 'none';
                
                data.database.forEach(record => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${record.id}</td>
                        <td title="AES Encrypted Blob">${record.encrypted_text_preview}</td>
                        <td title="Part A Vector Weights">[${record.vector_a_preview.join(', ')}...]</td>
                        <td title="Part B Vector Weights">[${record.vector_b_preview.join(', ')}...]</td>
                    `;
                    dbBody.appendChild(row);
                });
            }
        } catch (error) {
            console.error('Error fetching db:', error);
        }
    };

    // Upload Document
    uploadBtn.addEventListener('click', async () => {
        const text = uploadText.value.trim();
        if (!text) return;
        
        uploadBtn.disabled = true;
        uploadBtn.innerText = 'Encrypting & Uploading...';
        
        try {
             const res = await fetch('/api/upload', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ text })
             });
             
             if (res.ok) {
                 uploadText.value = '';
                 await fetchDatabase();
             } else {
                 alert('Error uploading document');
             }
        } catch (error) {
             console.error(error);
        } finally {
             uploadBtn.disabled = false;
             uploadBtn.innerText = 'Encrypt & Upload to Cloud';
        }
    });

    // Search Documents securely
    searchBtn.addEventListener('click', async () => {
         const query = searchQuery.value.trim();
         if (!query) return;
         
         searchBtn.disabled = true;
         searchBtn.innerText = 'Computing...';
         resultBox.style.display = 'none';
         
         try {
             const res = await fetch('/api/search', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ query })
             });
             
             const data = await res.json();
             
             if (res.ok) {
                 resId.innerText = `Match ID: ${data.best_match_id}`;
                 resScore.innerText = `Secure Similarity Score: ${data.score}`;
                 resText.innerText = data.decrypted_text;
                 resultBox.style.display = 'block';
                 // Flash animation on result box
                 resultBox.style.animation = 'none';
                 resultBox.offsetHeight; /* trigger reflow */
                 resultBox.style.animation = null; 
             } else {
                 alert(data.error || 'Search failed');
             }
         } catch (error) {
              console.error(error);
              alert('Error performing secure search.');
         } finally {
              searchBtn.disabled = false;
              searchBtn.innerText = 'Compute Secure Dot Product';
         }
    });

    // Reset All
    resetBtn.addEventListener('click', async () => {
        if (!confirm("Are you sure? This will delete the entire simulated cloud database and regenerate fresh client keys.")) return;
        
        try {
             await fetch('/api/reset', { method: 'POST' });
             resultBox.style.display = 'none';
             searchQuery.value = '';
             uploadText.value = '';
             await fetchDatabase();
        } catch (error) {
             console.error(error);
        }
    });

    // Initial Load
    fetchDatabase();
});
