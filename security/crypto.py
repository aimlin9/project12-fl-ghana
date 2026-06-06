from phe import paillier
import numpy as np

def generate_keys(key_length=2048):
    """Generate a Paillier key pair."""
    public_key, private_key = paillier.generate_paillier_keypair(n_length=key_length)
    return public_key, private_key

def encrypt_weights(public_key, weights):
    """
    Encrypt a list of float weights using the Paillier public key.
    weights can be a 1D numpy array or list of floats.
    """
    return [public_key.encrypt(float(w)) for w in weights]

def decrypt_weights(private_key, encrypted_weights):
    """
    Decrypt a list of encrypted weights using the Paillier private key.
    """
    return [private_key.decrypt(ew) for ew in encrypted_weights]

def homomorphic_sum(encrypted_weights_list):
    """
    Sum multiple lists of encrypted weights homomorphically.
    encrypted_weights_list: List of lists of EncryptedNumber.
    Returns: A single list of EncryptedNumber representing the element-wise sum.
    """
    num_params = len(encrypted_weights_list[0])
    summed = []
    for i in range(num_params):
        param_sum = encrypted_weights_list[0][i]
        for client_idx in range(1, len(encrypted_weights_list)):
            param_sum = param_sum + encrypted_weights_list[client_idx][i]
        summed.append(param_sum)
    return summed

def serialize_encrypted(encrypted_weights):
    """
    Serialize a list of EncryptedNumber to a list of dicts.
    """
    return [{"c": str(ew.ciphertext()), "e": int(ew.exponent)} for ew in encrypted_weights]

def deserialize_encrypted(public_key, serialized_weights):
    """
    Deserialize a list of dicts back into a list of EncryptedNumber.
    """
    return [paillier.EncryptedNumber(public_key, int(item["c"]), int(item["e"])) for item in serialized_weights]

def serialize_public_key(public_key):
    """Serialize PaillierPublicKey to a string n."""
    return str(public_key.n)

def deserialize_public_key(n_str):
    """Deserialize n back to PaillierPublicKey."""
    return paillier.PaillierPublicKey(int(n_str))
