from flask import Flask, request, jsonify, render_template
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import base64
from core import DocumentEncryption, SecureKNNEncryption

app = Flask(__name__)

# Global Application State (Simulating Client Key Store and Cloud Server)
class AppState:
    def __init__(self):
        self.reset()
        
    def reset(self):
        # Client-Side Secrets
        self.doc_encryptor = DocumentEncryption()
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.sknn = None # Will be initialized when first document is added to fix dimensions
        self.vector_dim = 100 # Fixed max dimension for simplicity in this demo to avoid matrix resizing
        self.sknn = SecureKNNEncryption(self.vector_dim)
        
        # Cloud-Side Database
        self.encrypted_database = []
        self.raw_documents_for_vocab = []

    def get_database_json(self):
        """Returns safe JSON representation of what the cloud holds."""
        output = []
        for record in self.encrypted_database:
            # Convert bytes to string for JSON, and numpy arrays to lists
            safe_text = base64.b64encode(record['encrypted_text']).decode('utf-8')
            part_a = record['encrypted_vector'][0][:5].tolist() # Just sending first 5 for UI display
            part_b = record['encrypted_vector'][1][:5].tolist()
            
            output.append({
                'id': record['id'],
                'encrypted_text_preview': safe_text[:30] + "...",
                'vector_a_preview': [round(v, 4) for v in part_a],
                'vector_b_preview': [round(v, 4) for v in part_b]
            })
        return output

state = AppState()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/reset', methods=['POST'])
def api_reset():
    state.reset()
    return jsonify({"status": "success", "message": "Database and keys reset."})

@app.route('/api/upload', methods=['POST'])
def api_upload():
    data = request.json
    doc_text = data.get('text', '').strip()
    
    if not doc_text:
        return jsonify({"error": "No text provided"}), 400

    # 1. Update Client Vocab (in real system, vocab would be fixed or periodically updated)
    state.raw_documents_for_vocab.append(doc_text)
    state.vectorizer.fit(state.raw_documents_for_vocab)
    
    # Vectorize
    doc_vec = state.vectorizer.transform([doc_text]).toarray()[0]
    
    # 2. Encrypt Text
    enc_text = state.doc_encryptor.encrypt(doc_text)
    
    # 3. Encrypt Vector
    enc_vec = state.sknn.encrypt_index(doc_vec)
    
    # 4. Upload to "Cloud"
    doc_id = len(state.encrypted_database)
    state.encrypted_database.append({
        'id': doc_id,
        'encrypted_text': enc_text,
        'encrypted_vector': enc_vec
    })
    
    return jsonify({"status": "success", "id": doc_id})

@app.route('/api/database', methods=['GET'])
def api_database():
    return jsonify({"database": state.get_database_json()})

@app.route('/api/search', methods=['POST'])
def api_search():
    data = request.json
    query_text = data.get('query', '').strip()
    
    if not query_text or not state.encrypted_database:
        return jsonify({"error": "No query provided or database is empty"}), 400

    # 1. Vectorize Query (Client Side)
    try:
        query_vec = state.vectorizer.transform([query_text]).toarray()[0]
    except Exception as e:
        # Happens if query words don't exist in vocab
        return jsonify({"error": "Query terms not found in corpus"}), 400
        
    # 2. Encrypt Query (Client Side)
    enc_query_vec = state.sknn.encrypt_query(query_vec)
    
    # 3. Secure Search (Cloud Side)
    scores = []
    for record in state.encrypted_database:
        score = SecureKNNEncryption.secure_dot_product(record['encrypted_vector'], enc_query_vec)
        scores.append((record['id'], score))
        
    # Sort
    scores.sort(key=lambda x: x[1], reverse=True)
    best_match_id = scores[0][0]
    best_match_score = float(scores[0][1]) # Convert numpy float to standard float for JSON
    
    if best_match_score == 0:
         return jsonify({"error": "No matches found"}), 404
    
    # 4. Retrieval & Decryption (Client Side)
    returned_encrypted_text = state.encrypted_database[best_match_id]['encrypted_text']
    decrypted_text = state.doc_encryptor.decrypt(returned_encrypted_text)
    
    return jsonify({
        "status": "success",
        "best_match_id": best_match_id,
        "score": round(best_match_score, 4),
        "decrypted_text": decrypted_text
    })

if __name__ == '__main__':
    app.run(debug=True)
