import os
import sys
import platform
import time
from pathlib import Path
from loguru import logger

# Platform-specific imports
if platform.system() == 'Windows':
    import msvcrt
    try:
        import psutil
    except ImportError:
        psutil = None
else:
    import fcntl


class ProcessLock:
    """Process lock to prevent multiple instances of the bot from running"""

    def __init__(self, lock_file_path: str = None):
        if lock_file_path is None:
            # Default to a lock file in the project root
            lock_file_path = Path(__file__).parent.parent / ".bot.lock"
        
        self.lock_file_path = Path(lock_file_path)
        self.lock_file = None
        self.acquired = False

    def acquire(self) -> bool:
        """Acquire the process lock"""
        try:
            # Create lock file if it doesn't exist
            self.lock_file = open(self.lock_file_path, 'w')
            
            # Platform-specific locking
            if platform.system() == 'Windows':
                # Windows-specific locking using msvcrt
                try:
                    msvcrt.locking(self.lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                except (OSError, IOError):
                    # Lock is held by another process
                    self.lock_file.close()
                    self.lock_file = None
                    return False
            else:
                # Unix/Linux locking using fcntl
                try:
                    fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    # Lock is held by another process
                    self.lock_file.close()
                    self.lock_file = None
                    return False
            
            # Write our PID to the lock file
            self.lock_file.write(f"{os.getpid()}\n")
            self.lock_file.flush()
            self.acquired = True
            
            logger.info(f"[LOCK] Process lock acquired for PID {os.getpid()}")
            return True
            
        except Exception as e:
            logger.error(f"[LOCK] Failed to acquire process lock: {e}")
            if self.lock_file:
                self.lock_file.close()
                self.lock_file = None
            return False

    def release(self):
        """Release the process lock"""
        if self.acquired and self.lock_file:
            try:
                # Platform-specific unlocking
                if platform.system() == 'Windows':
                    # Windows-specific unlocking
                    msvcrt.locking(self.lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    # Unix/Linux unlocking using fcntl
                    fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                
                self.lock_file.close()
                
                # Remove the lock file
                if self.lock_file_path.exists():
                    self.lock_file_path.unlink()
                
                self.acquired = False
                logger.info(f"[LOCK] Process lock released for PID {os.getpid()}")
                
            except Exception as e:
                logger.error(f"[LOCK] Failed to release process lock: {e}")

    def is_locked_by_other_process(self) -> bool:
        """Check if the lock is held by another process"""
        if not self.lock_file_path.exists():
            return False
        
        try:
            # Try to read the PID from the lock file
            with open(self.lock_file_path, 'r') as f:
                pid_str = f.read().strip()
                if pid_str:
                    pid = int(pid_str)
                    
                    # Check if the process is still running
                    if self._is_process_running(pid):
                        return True  # Process is still running
                    else:
                        # Process doesn't exist, remove stale lock file
                        self.lock_file_path.unlink()
                        return False
        except (ValueError, IOError):
            # Invalid lock file, remove it
            try:
                self.lock_file_path.unlink()
            except:
                pass
            return False
        
        return False

    def _is_process_running(self, pid: int) -> bool:
        """Check if a process with the given PID is running"""
        try:
            if platform.system() == 'Windows':
                if psutil:
                    return psutil.pid_exists(pid)
                else:
                    # Fallback for Windows without psutil
                    import ctypes
                    kernel32 = ctypes.windll.kernel32
                    handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
                    if handle:
                        kernel32.CloseHandle(handle)
                        return True
                    return False
            else:
                # Unix/Linux: send signal 0 to check if process exists
                os.kill(pid, 0)
                return True
        except (OSError, ProcessLookupError):
            return False

    def __enter__(self):
        """Context manager entry"""
        if not self.acquire():
            logger.error("[LOCK] Another instance is already running. Exiting.")
            sys.exit(1)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.release()


def check_existing_instances():
    """Check for existing bot instances and provide guidance"""
    lock_file = Path(__file__).parent.parent / ".bot.lock"
    
    if lock_file.exists():
        try:
            with open(lock_file, 'r') as f:
                pid_str = f.read().strip()
                if pid_str:
                    pid = int(pid_str)
                    
                    # Check if process is still running
                    if platform.system() == 'Windows':
                        if psutil:
                            process_exists = psutil.pid_exists(pid)
                        else:
                            # Simple check for Windows
                            process_exists = True  # Assume exists if we can't check
                    else:
                        try:
                            os.kill(pid, 0)
                            process_exists = True
                        except OSError:
                            process_exists = False
                    
                    if process_exists:
                        logger.error(f"[CONFLICT] Bot instance already running with PID {pid}")
                        logger.error("[CONFLICT] Please stop the existing instance first:")
                        
                        if platform.system() == 'Windows':
                            logger.error(f"  taskkill /PID {pid} /F")
                            logger.error("[CONFLICT] Or use: taskkill /IM python.exe /F")
                        else:
                            logger.error(f"  kill {pid}")
                            logger.error("[CONFLICT] Or use: pkill -f 'python.*main.py'")
                        return True
                    else:
                        logger.info("[CLEANUP] Removing stale lock file (process no longer exists)")
                        lock_file.unlink()
                        return False
        except (ValueError, IOError):
            logger.warning("[CLEANUP] Invalid lock file found, removing it")
            try:
                lock_file.unlink()
            except:
                pass
    
    return False
