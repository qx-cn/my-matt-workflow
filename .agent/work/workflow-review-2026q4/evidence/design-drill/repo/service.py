"""Existing shared contract and process coordination."""
LOCK_KEY = 'invoice:v1'
def read_invoice(store, key):
    # All existing consumers use try/except KeyError for absence.
    return store[key]
def write_invoice(store, key, value, lock_service):
    with lock_service.acquire(LOCK_KEY):
        store[key] = value
