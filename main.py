import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from cryptography.fernet import Fernet
import json
import base64

class DocumentEncryption:
    """Handles symmetric encryption of the actual document text using AES (Fernet)."""
    def __init__(self):
        self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)

    def encrypt(self, text: str) -> bytes:
        return self.cipher.encrypt(text.encode('utf-8'))

    def decrypt(self, encrypted_text: bytes) -> str:
        return self.cipher.decrypt(encrypted_text).decode('utf-8')

class SecureKNNEncryption:
    """
    Implements the Secure k-NN scalar-product-preserving encryption scheme
    by Wong et al. (2009).
    """
    def __init__(self, vector_dim: int):
        self.vector_dim = vector_dim
        # Generate the secret key: (M1, M2, S)
        # M1 and M2 are random invertible matrices
        self.M1 = self._generate_invertible_matrix(vector_dim)
        self.M2 = self._generate_invertible_matrix(vector_dim)
        # S is a binary splitting vector
        self.S = np.random.choice([0, 1], size=vector_dim)

    def _generate_invertible_matrix(self, dim: int):
        while True:
            M = np.random.rand(dim, dim) * 10 - 5 # Random values between -5 and 5
            if np.abs(np.linalg.det(M)) > 0.1: # Ensure it's reasonably invertible
                return M

    def encrypt_index(self, p):
        """Encrypts a document vector (p)."""
        if len(p) != self.vector_dim:
            raise ValueError("Vector dimension mismatch")

        p_a = np.zeros(self.vector_dim)
        p_b = np.zeros(self.vector_dim)

        for i in range(self.vector_dim):
            if self.S[i] == 1:
                # If S[i] == 1, split p[i] into two random numbers that sum to p[i]
                r = np.random.rand() * p[i] if p[i] != 0 else np.random.rand()
                p_a[i] = p[i] - r
                p_b[i] = r
            else:
                # If S[i] == 0, duplicate p[i]
                p_a[i] = p[i]
                p_b[i] = p[i]

        # Encrypt: M1^T * p_a, M2^T * p_b
        p_prime_a = np.dot(self.M1.T, p_a)
        p_prime_b = np.dot(self.M2.T, p_b)

        return (p_prime_a, p_prime_b)

    def encrypt_query(self, q):
        """Encrypts a query vector (q)."""
        if len(q) != self.vector_dim:
            raise ValueError("Vector dimension mismatch")

        q_a = np.zeros(self.vector_dim)
        q_b = np.zeros(self.vector_dim)
        
        # Determine r - a random positive scalar
        r = np.random.rand() * 5 + 1

        # Multiply query vector by r to prevent revealing exact vector
        # (Since dot product is relative, scaling query by positive r maintains ranking)
        scaled_q = q * r

        for i in range(self.vector_dim):
            if self.S[i] == 1:
                # If S[i] == 1, duplicate q[i]
                q_a[i] = scaled_q[i]
                q_b[i] = scaled_q[i]
            else:
                # If S[i] == 0, split q[i] into two random numbers that sum to q[i]
                split_val = np.random.rand() * scaled_q[i] if scaled_q[i] != 0 else np.random.rand()
                q_a[i] = scaled_q[i] - split_val
                q_b[i] = split_val

        # Encrypt: M1^-1 * q_a, M2^-1 * q_b
        M1_inv = np.linalg.inv(self.M1)
        M2_inv = np.linalg.inv(self.M2)

        q_prime_a = np.dot(M1_inv, q_a)
        q_prime_b = np.dot(M2_inv, q_b)

        return (q_prime_a, q_prime_b)

    @staticmethod
    def secure_dot_product(encrypted_p, encrypted_q):
        """
        Computes the dot product of encrypted index and encrypted query.
        (M1^T * p_a) * (M1^-1 * q_a) + (M2^T * p_b) * (M2^-1 * q_b)
        = p_a * q_a + p_b * q_b
        = p * q * r
        """
        p_prime_a, p_prime_b = encrypted_p
        q_prime_a, q_prime_b = encrypted_q

        dot_a = np.dot(p_prime_a, q_prime_a)
        dot_b = np.dot(p_prime_b, q_prime_b)

        return dot_a + dot_b

def main():
    print("--- Privacy-Preserving Encrypted Document Retrieval System ---")
    print("Scenario: Hospital Secure Medical Records Search\n")

    # 1. Initialize Hospital Document Corpus
    documents = [
        "Patient John Doe. Diagnosis: Type 2 Diabetes. Prescription: Metformin 500mg daily. Advice: Diet and exercise.",
        "Patient Jane Smith. Diagnosis: Hypertension. Blood pressure 140/90. Prescription: Lisinopril 10mg.",
        "Patient Michael Johnson. Diagnosis: Severe Migraine. Prescription: Sumatriptan 50mg. Note: Avoid bright light.",
        "Patient Emily Davis. Routine checkup. All vitals normal. No medication prescribed. Clear for sports.",
        "Patient Robert Brown. Diagnosis: Seasonal Allergies. Prescription: Cetirizine 10mg daily. Advice: Avoid pollen.",
        "Patient Sarah Connor. Diagnosis: Broken Arm (Radius fracture). Treatment: Cast applied, pain medication prescribed (Ibuprofen 400mg)."
    ]

    print("\n[DATA ENTRY PHASE]")
    print("You can add your own custom medical records to the database.")
    print("Type your record and press Enter. Leave blank and press Enter to finish adding.")
    while True:
        new_doc = input("Enter a new patient record (or press Enter to skip): ").strip()
        if not new_doc:
            break
        documents.append(new_doc)
        print(f"  -> Added! Total records: {len(documents)}")

    print(f"\n[*] Initialized {len(documents)} plain text hospital records.")

    # 2. Vectorize Documents (TF-IDF)
    print("\n[*] Vectorizing documents using TF-IDF...")
    vectorizer = TfidfVectorizer(stop_words='english')
    doc_vectors = vectorizer.fit_transform(documents).toarray()
    vector_dim = doc_vectors.shape[1]
    
    # 3. Initialize Security Modules (Keys are kept strictly by the Data Owner/Client, NOT the Cloud Server)
    print(f"[*] Initializing Secure k-NN scheme (Dimension: {vector_dim})...")
    sknn = SecureKNNEncryption(vector_dim)
    
    print("[*] Initializing AES Document Encryption...")
    doc_encryptor = DocumentEncryption()

    # 4. Upload Phase: Encrypt Documents and Vectors
    print("\n[UPLOAD PHASE] Encrypting text and vectors (Simulating upload to Cloud)...")
    encrypted_database = []
    
    for i, (doc_text, doc_vec) in enumerate(zip(documents, doc_vectors)):
        # Encrypt the text
        enc_text = doc_encryptor.encrypt(doc_text)
        # Encrypt the vector representation
        enc_vec = sknn.encrypt_index(doc_vec)
        
        encrypted_database.append({
            'id': i,
            'encrypted_text': enc_text,
            'encrypted_vector': enc_vec
        })
        
    print(f"[✓] {len(encrypted_database)} records securely uploaded to Cloud.")
    print("\n--- COMPLETE CLOUD DATABASE CONTENTS ---")
    for record in encrypted_database:
        print(f"  [Record ID: {record['id']}]")
        print(f"    - Encrypted Text: {record['encrypted_text'][:60]}... (truncated)")
        print(f"    - Encrypted Vector (Part A): [{record['encrypted_vector'][0][0]:.4f}, {record['encrypted_vector'][0][1]:.4f}, ...]")
        print(f"    - Encrypted Vector (Part B): [{record['encrypted_vector'][1][0]:.4f}, {record['encrypted_vector'][1][1]:.4f}, ...]")
    print("----------------------------------------\n")
    print(f"   (Example Client-Side Matrix M1 shape: {sknn.M1.shape})")
    print(f"   (Example Encrypted Text snippets hold no readable info)")

    # 5. Query Phase: Create Encrypted Search Query
    print("\n[QUERY PHASE]")
    query_text = input("Enter your search query (e.g., 'blood pressure', 'allergies'): ")
    print(f"Searching for: '{query_text}'")
    
    # Vectorize query
    query_vec = vectorizer.transform([query_text]).toarray()[0]
    
    # Encrypt query
    print("[*] Encrypting query vector locally...")
    enc_query_vec = sknn.encrypt_query(query_vec)

    # 6. Search Phase: Cloud Calculates secure dot product
    print("\n[SEARCH PHASE] Cloud Server computing similarity scores securely...")
    # The cloud server ONLY has `encrypted_database` and `enc_query_vec`
    # It does NOT have `M1`, `M2`, `S`, `doc_encryptor.key`, or `doc_vectors`
    
    scores = []
    for record in encrypted_database:
        score = SecureKNNEncryption.secure_dot_product(record['encrypted_vector'], enc_query_vec)
        scores.append((record['id'], score))

    # Sort to find highest score
    scores.sort(key=lambda x: x[1], reverse=True)
    best_match_id = scores[0][0]
    best_match_score = scores[0][1]
    
    print(f"[✓] Cloud found highest encrypted similarity score: {best_match_score:.4f} (Record ID: {best_match_id})")

    # 7. Retrieval Phase: Decrypt the result text
    print("\n[RETRIEVAL PHASE] Cloud returns the encrypted document to Doctor.")
    print("[*] Decrypting the downloaded text...")
    
    returned_encrypted_text = encrypted_database[best_match_id]['encrypted_text']
    decrypted_text = doc_encryptor.decrypt(returned_encrypted_text)

    # Display Output
    print("\n================== FULL PLEDGE OUTPUT ==================")
    print(f"Search Query  : {query_text}")
    print(f"Best Match ID : {best_match_id}")
    print(f"Plain Text    : {decrypted_text}")
    print("========================================================")

if __name__ == "__main__":
    main()
