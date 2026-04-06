import numpy as np
from cryptography.fernet import Fernet
import base64

class DocumentEncryption:
    """Handles symmetric encryption of the actual document text using AES (Fernet)."""
    def __init__(self, key=None):
        self.key = key if key else Fernet.generate_key()
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
        self.M1 = self._generate_invertible_matrix(vector_dim)
        self.M2 = self._generate_invertible_matrix(vector_dim)
        self.S = np.random.choice([0, 1], size=vector_dim)

    def _generate_invertible_matrix(self, dim: int):
        while True:
            M = np.random.rand(dim, dim) * 10 - 5
            if np.abs(np.linalg.det(M)) > 0.1:
                return M

    def encrypt_index(self, p):
        """Encrypts a document vector (p)."""
        if len(p) != self.vector_dim:
            # Pad or truncate if dimensions changed due to new vocab
            new_p = np.zeros(self.vector_dim)
            min_dim = min(len(p), self.vector_dim)
            new_p[:min_dim] = p[:min_dim]
            p = new_p

        p_a = np.zeros(self.vector_dim)
        p_b = np.zeros(self.vector_dim)

        for i in range(self.vector_dim):
            if self.S[i] == 1:
                r = np.random.rand() * p[i] if p[i] != 0 else np.random.rand()
                p_a[i] = p[i] - r
                p_b[i] = r
            else:
                p_a[i] = p[i]
                p_b[i] = p[i]

        p_prime_a = np.dot(self.M1.T, p_a)
        p_prime_b = np.dot(self.M2.T, p_b)

        return (p_prime_a, p_prime_b)

    def encrypt_query(self, q):
        """Encrypts a query vector (q)."""
        if len(q) != self.vector_dim:
             # Pad if necessary
            new_q = np.zeros(self.vector_dim)
            min_dim = min(len(q), self.vector_dim)
            new_q[:min_dim] = q[:min_dim]
            q = new_q

        q_a = np.zeros(self.vector_dim)
        q_b = np.zeros(self.vector_dim)
        
        r = np.random.rand() * 5 + 1
        scaled_q = q * r

        for i in range(self.vector_dim):
            if self.S[i] == 1:
                q_a[i] = scaled_q[i]
                q_b[i] = scaled_q[i]
            else:
                split_val = np.random.rand() * scaled_q[i] if scaled_q[i] != 0 else np.random.rand()
                q_a[i] = scaled_q[i] - split_val
                q_b[i] = split_val

        M1_inv = np.linalg.inv(self.M1)
        M2_inv = np.linalg.inv(self.M2)

        q_prime_a = np.dot(M1_inv, q_a)
        q_prime_b = np.dot(M2_inv, q_b)

        return (q_prime_a, q_prime_b)

    @staticmethod
    def secure_dot_product(encrypted_p, encrypted_q):
        """
        Computes the dot product of encrypted index and encrypted query.
        """
        p_prime_a, p_prime_b = encrypted_p
        q_prime_a, q_prime_b = encrypted_q

        dot_a = np.dot(p_prime_a, q_prime_a)
        dot_b = np.dot(p_prime_b, q_prime_b)

        return dot_a + dot_b
