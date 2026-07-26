"""
LockManager and LockType implementation.
"""

import threading
import time
from enum import Enum
from typing import Dict, List, Optional, Set
from graph_storage.exceptions import GraphStorageError
from graph_storage.model import TransactionId


class LockType(Enum):
    SHARED = "SHARED"
    EXCLUSIVE = "EXCLUSIVE"
    INTENT_EXCLUSIVE = "INTENT_EXCLUSIVE"


class LockManager:
    """Thread-safe lock manager for transaction isolation."""

    def __init__(self):
        self._lock = threading.RLock()
        self._key_locks: Dict[str, LockType] = {}
        self._owner_map: Dict[str, TransactionId] = {}
        self._shared_owners: Dict[str, Set[TransactionId]] = {}

    def acquire(self, tx_id: TransactionId, key: str, lock_type: LockType = LockType.EXCLUSIVE, timeout_sec: float = 1.0) -> bool:
        """Acquire a lock on a key."""
        start_t = time.time()
        while True:
            with self._lock:
                current_type = self._key_locks.get(key)
                if current_type is None:
                    self._key_locks[key] = lock_type
                    if lock_type == LockType.SHARED:
                        self._shared_owners[key] = {tx_id}
                    else:
                        self._owner_map[key] = tx_id
                    return True
                elif current_type == LockType.SHARED and lock_type == LockType.SHARED:
                    self._shared_owners[key].add(tx_id)
                    return True
                elif self._owner_map.get(key) == tx_id:
                    return True

            if (time.time() - start_t) > timeout_sec:
                return False
            time.sleep(0.01)

    def release(self, tx_id: TransactionId, key: str) -> bool:
        """Release lock held by tx_id on key."""
        with self._lock:
            if key not in self._key_locks:
                return False

            lock_type = self._key_locks[key]
            if lock_type == LockType.SHARED:
                if key in self._shared_owners and tx_id in self._shared_owners[key]:
                    self._shared_owners[key].remove(tx_id)
                    if not self._shared_owners[key]:
                        del self._shared_owners[key]
                        del self._key_locks[key]
                    return True
            else:
                if self._owner_map.get(key) == tx_id:
                    del self._owner_map[key]
                    del self._key_locks[key]
                    return True
            return False

    def release_all(self, tx_id: TransactionId) -> None:
        """Release all locks held by a transaction."""
        with self._lock:
            keys_to_release = [k for k, owner in self._owner_map.items() if owner == tx_id]
            for k in keys_to_release:
                self.release(tx_id, k)

            shared_keys = [k for k, owners in self._shared_owners.items() if tx_id in owners]
            for k in shared_keys:
                self.release(tx_id, k)

    def is_locked(self, key: str) -> bool:
        with self._lock:
            return key in self._key_locks
