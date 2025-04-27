import os
import pickle

def get_storage_path(user_id):
    return f"storage_{user_id}.pkl"

def get_sent_links(user_id):
    path = get_storage_path(user_id)
    if os.path.exists(path):
        with open(path, 'rb') as f:
            return pickle.load(f)
    return set()

def save_sent_links(user_id, links):
    path = get_storage_path(user_id)
    with open(path, 'wb') as f:
        pickle.dump(links, f)
