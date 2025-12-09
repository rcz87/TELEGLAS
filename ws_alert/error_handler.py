"""
Comprehensive Error Handling System (Poin 6)

Advanced error handling dengan circuit breaker pattern, graceful degradation,
dan comprehensive error reporting untuk seluruh WebSocket Alert Bot system.
"""

import time
import logging
import traceback
import threading
from typing import Dict, List, Optional, Callable, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Error categories for classification"""
    NETWORK = "network"
    API = "api"
    DATABASE = "database"
    WEBSOCKET = "websocket"
    AUTHENTICATION = "authentication"
    VALIDATION = "validation"
    SYSTEM = "system"
    BUSINESS = "business"

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing recovery

@dataclass
class ErrorInfo:
    """Comprehensive error information"""
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    exception: Optional[Exception] = None
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    module: str = ""
    function: str = ""
    line_number: int = 0
    stack_trace: str = ""
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    recovery_attempts: int = 0
    resolved: bool = False
    resolution_time: Optional[float] = None

@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    success_threshold: int = 3
    timeout: float = 30.0
    expected_exception: type = Exception

class CircuitBreaker:
    """Circuit breaker implementation for fault tolerance"""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.last_success_time = 0
        self.lock = threading.RLock()
        
        # Statistics
        self.total_requests = 0
        self.total_failures = 0
        self.total_successes = 0
        self.state_changes = []
        
    def __call__(self, func: Callable) -> Callable:
        """Decorator for circuit breaker protection"""
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)
        return wrapper
    
    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        with self.lock:
            self.total_requests += 1
            
            # Check circuit state
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.state_changes.append((time.time(), "half_open"))
                    logger.info(f"Circuit {self.name} entering HALF_OPEN state")
                else:
                    error = CircuitBreakerError(f"Circuit {self.name} is OPEN")
                    self.total_failures += 1
                    raise error
            
            try:
                # Execute function with timeout
                if asyncio.iscoroutinefunction(func):
                    result = asyncio.wait_for(func(*args, **kwargs), self.config.timeout)
                else:
                    result = func(*args, **kwargs)
                
                # Success path
                self._on_success()
                return result
                
            except Exception as e:
                # Failure path
                self._on_failure(e)
                raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt reset"""
        return time.time() - self.last_failure_time >= self.config.recovery_timeout
    
    def _on_success(self):
        """Handle successful execution"""
        with self.lock:
            self.total_successes += 1
            self.last_success_time = time.time()
            
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.success_count = 0
                    self.failure_count = 0
                    self.state_changes.append((time.time(), "closed"))
                    logger.info(f"Circuit {self.name} reset to CLOSED state")
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0
    
    def _on_failure(self, exception: Exception):
        """Handle failed execution"""
        with self.lock:
            self.total_failures += 1
            self.last_failure_time = time.time()
            
            # Check if this is an expected exception
            if isinstance(exception, self.config.expected_exception):
                if self.state == CircuitState.CLOSED:
                    self.failure_count += 1
                    if self.failure_count >= self.config.failure_threshold:
                        self.state = CircuitState.OPEN
                        self.state_changes.append((time.time(), "open"))
                        logger.warning(f"Circuit {self.name} opened due to {self.failure_count} failures")
                elif self.state == CircuitState.HALF_OPEN:
                    self.state = CircuitState.OPEN
                    self.state_changes.append((time.time(), "open"))
                    logger.warning(f"Circuit {self.name} re-opened from HALF_OPEN")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics"""
        with self.lock:
            return {
                'name': self.name,
                'state': self.state.value,
                'total_requests': self.total_requests,
                'total_failures': self.total_failures,
                'total_successes': self.total_successes,
                'failure_rate': self.total_failures / max(self.total_requests, 1),
                'current_failures': self.failure_count,
                'current_successes': self.success_count,
                'last_failure_time': self.last_failure_time,
                'last_success_time': self.last_success_time,
                'state_changes': self.state_changes[-10:]  # Last 10 changes
            }
    
    def reset(self):
        """Manually reset circuit breaker"""
        with self.lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.state_changes.append((time.time(), "manual_reset"))
            logger.info(f"Circuit {self.name} manually reset")

class CircuitBreakerError(Exception):
    """Circuit breaker specific error"""
    pass

class ErrorClassifier:
    """Error classification and severity assessment"""
    
    # Classification rules
    NETWORK_ERRORS = [
        'ConnectionError', 'TimeoutError', 'ConnectTimeoutError',
        'ReadTimeoutError', 'SSLError', 'HTTPError'
    ]
    
    API_ERRORS = [
        'APIError', 'RateLimitError', 'AuthenticationError',
        'PermissionError', 'NotFound', 'BadRequest'
    ]
    
    DATABASE_ERRORS = [
        'DatabaseError', 'ConnectionError', 'OperationalError',
        'IntegrityError', 'ProgrammingError'
    ]
    
    WEBSOCKET_ERRORS = [
        'WebSocketError', 'ConnectionClosed', 'ConnectionClosedOK',
        'ConnectionClosedError', 'InvalidHandshake'
    ]
    
    @classmethod
    def classify_error(cls, exception: Exception):
        """Classify error category and severity"""
        exception_name = exception.__class__.__name__
        error_message = str(exception).lower()
        
        # Determine category
        category = ErrorCategory.SYSTEM  # Default
        
        if exception_name in cls.NETWORK_ERRORS or 'network' in error_message:
            category = ErrorCategory.NETWORK
        elif exception_name in cls.API_ERRORS or 'api' in error_message:
            category = ErrorCategory.API
        elif exception_name in cls.DATABASE_ERRORS or 'database' in error_message:
            category = ErrorCategory.DATABASE
        elif exception_name in cls.WEBSOCKET_ERRORS or 'websocket' in error_message:
            category = ErrorCategory.WEBSOCKET
        elif 'auth' in error_message or 'permission' in error_message:
            category = ErrorCategory.AUTHENTICATION
        elif 'validation' in error_message or 'invalid' in error_message:
            category = ErrorCategory.VALIDATION
        
        # Determine severity
        severity = ErrorSeverity.MEDIUM  # Default
        
        # Critical indicators
        if any(keyword in error_message for keyword in ['critical', 'fatal', 'emergency']):
            severity = ErrorSeverity.CRITICAL
        # High severity indicators
        elif any(keyword in error_message for keyword in ['timeout', 'failed', 'error']):
            severity = ErrorSeverity.HIGH
        # Low severity indicators
        elif any(keyword in error_message for keyword in ['warning', 'deprecated', 'minor']):
            severity = ErrorSeverity.LOW
        
        # Category-specific severity adjustments
        if category == ErrorCategory.DATABASE:
            severity = max(severity, ErrorSeverity.HIGH)  # Database errors are at least high
        elif category == ErrorCategory.WEBSOCKET:
            severity = max(severity, ErrorSeverity.MEDIUM)  # WebSocket errors are at least medium
        
        return category, severity

class RecoveryManager:
    """Automatic recovery and retry logic"""
    
    def __init__(self):
        self.recovery_strategies = {}
        self.active_recoveries = {}
        self.lock = threading.RLock()
    
    def register_strategy(self, error_type: type, strategy: Callable):
        """Register recovery strategy for specific error type"""
        self.recovery_strategies[error_type] = strategy
    
    def attempt_recovery(self, error_info: ErrorInfo) -> bool:
        """Attempt automatic recovery for error"""
        error_type = type(error_info.exception) if error_info.exception else Exception
        
        with self.lock:
            # Check if recovery is already in progress
            if error_info.error_id in self.active_recoveries:
                return False
            
            # Get recovery strategy
            strategy = self.recovery_strategies.get(error_type)
            if not strategy:
                return False
            
            # Start recovery attempt
            self.active_recoveries[error_info.error_id] = {
                'start_time': time.time(),
                'strategy': strategy.__name__,
                'attempts': 0
            }
        
        try:
            # Execute recovery strategy
            success = strategy(error_info)
            
            with self.lock:
                if success:
                    error_info.resolved = True
                    error_info.resolution_time = time.time()
                    del self.active_recoveries[error_info.error_id]
                    logger.info(f"Successfully recovered from error {error_info.error_id}")
                else:
                    self.active_recoveries[error_info.error_id]['attempts'] += 1
                
                return success
                
        except Exception as e:
            logger.error(f"Recovery strategy failed for {error_info.error_id}: {e}")
            with self.lock:
                if error_info.error_id in self.active_recoveries:
                    self.active_recoveries[error_info.error_id]['attempts'] += 1
            return False

class GracefulDegradation:
    """Graceful degradation for system resilience"""
    
    def __init__(self):
        self.degradation_levels = {
            'full': self._full_operation,
            'degraded': self._degraded_operation,
            'minimal': self._minimal_operation,
            'emergency': self._emergency_operation
        }
        self.current_level = 'full'
        self.level_history = deque(maxlen=100)
        self.lock = threading.RLock()
    
    def set_degradation_level(self, level: str, reason: str = ""):
        """Set degradation level"""
        with self.lock:
            if level in self.degradation_levels:
                old_level = self.current_level
                self.current_level = level
                self.level_history.append({
                    'timestamp': time.time(),
                    'level': level,
                    'reason': reason
                })
                logger.warning(f"Degradation level changed: {old_level} -> {level} ({reason})")
            else:
                logger.error(f"Invalid degradation level: {level}")
    
    def execute_with_degradation(self, func: Callable, *args, **kwargs):
        """Execute function with current degradation level"""
        return self.degradation_levels[self.current_level](func, *args, **kwargs)
    
    def _full_operation(self, func: Callable, *args, **kwargs):
        """Full operation mode"""
        return func(*args, **kwargs)
    
    def _degraded_operation(self, func: Callable, *args, **kwargs):
        """Degraded operation mode - reduced functionality"""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Degraded mode fallback for {func.__name__}: {e}")
            return None
    
    def _minimal_operation(self, func: Callable, *args, **kwargs):
        """Minimal operation mode - essential functions only"""
        # Only allow critical functions
        if hasattr(func, '_critical'):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Critical function failed in minimal mode: {e}")
        return None
    
    def _emergency_operation(self, func: Callable, *args, **kwargs):
        """Emergency operation mode - minimal survival"""
        # Only allow emergency functions
        if hasattr(func, '_emergency'):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.critical(f"Emergency function failed: {e}")
        return None

def critical_function(func: Callable) -> Callable:
    """Decorator to mark function as critical"""
    func._critical = True
    return func

def emergency_function(func: Callable) -> Callable:
    """Decorator to mark function as emergency-only"""
    func._emergency = True
    return func

class ComprehensiveErrorHandler:
    """Main error handling system"""
    
    def __init__(self):
        self.error_log = deque(maxlen=10000)  # Keep last 10k errors
        self.error_stats = defaultdict(lambda: defaultdict(int))
        self.circuit_breakers = {}
        self.classifier = ErrorClassifier()
        self.recovery_manager = RecoveryManager()
        self.degradation = GracefulDegradation()
        self.lock = threading.RLock()
        
        # Error callbacks
        self.error_callbacks = []
        
        # Setup default recovery strategies
        self._setup_default_recoveries()
    
    def _setup_default_recoveries(self):
        """Setup default recovery strategies"""
        # Network recovery
        def recover_network(error_info: ErrorInfo) -> bool:
            logger.info("Attempting network recovery...")
            time.sleep(2)  # Wait for network to recover
            return True
        
        # API recovery
        def recover_api(error_info: ErrorInfo) -> bool:
            logger.info("Attempting API recovery...")
            time.sleep(5)  # Wait for API rate limit to reset
            return True
        
        # WebSocket recovery
        def recover_websocket(error_info: ErrorInfo) -> bool:
            logger.info("Attempting WebSocket recovery...")
            time.sleep(3)  # Wait before reconnect
            return True
        
        self.recovery_manager.register_strategy(ConnectionError, recover_network)
        self.recovery_manager.register_strategy(TimeoutError, recover_network)
        self.recovery_manager.register_strategy(Exception, recover_api)  # Generic API errors
        self.recovery_manager.register_strategy(Exception, recover_websocket)  # Generic WebSocket errors
    
    def handle_error(self, 
                    exception: Exception,
                    module: str = "",
                    function: str = "",
                    context: Dict[str, Any] = None,
                    user_id: str = None,
                    request_id: str = None) -> ErrorInfo:
        """Handle error with comprehensive processing"""
        
        # Generate error ID
        error_id = f"ERR_{int(time.time() * 1000)}_{id(exception)}"
        
        # Classify error
        category, severity = self.classifier.classify_error(exception)
        
        # Extract stack trace
        stack_trace = traceback.format_exc()
        
        # Get calling context if not provided
        if not context:
            context = {}
        
        # Create error info
        error_info = ErrorInfo(
            error_id=error_id,
            category=category,
            severity=severity,
            message=str(exception),
            exception=exception,
            context=context,
            module=module,
            function=function,
            stack_trace=stack_trace,
            user_id=user_id,
            request_id=request_id
        )
        
        # Store error
        with self.lock:
            self.error_log.append(error_info)
            self.error_stats[category.value][severity.value] += 1
        
        # Log error
        self._log_error(error_info)
        
        # Trigger callbacks
        self._trigger_callbacks(error_info)
        
        # Attempt recovery
        if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            self.recovery_manager.attempt_recovery(error_info)
        
        # Adjust degradation level if needed
        self._adjust_degradation_level(error_info)
        
        return error_info
    
    def _log_error(self, error_info: ErrorInfo):
        """Log error with appropriate level"""
        log_message = f"[{error_info.error_id}] {error_info.category.value.upper()} - {error_info.message}"
        if error_info.module:
            log_message += f" (in {error_info.module}.{error_info.function})"
        
        if error_info.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message)
        elif error_info.severity == ErrorSeverity.HIGH:
            logger.error(log_message)
        elif error_info.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)
    
    def _trigger_callbacks(self, error_info: ErrorInfo):
        """Trigger error callbacks"""
        for callback in self.error_callbacks:
            try:
                callback(error_info)
            except Exception as e:
                logger.error(f"Error callback failed: {e}")
    
    def _adjust_degradation_level(self, error_info: ErrorInfo):
        """Adjust degradation level based on error patterns"""
        recent_errors = [e for e in self.error_log 
                        if time.time() - e.timestamp < 300]  # Last 5 minutes
        
        # Count critical errors in last 5 minutes
        critical_count = sum(1 for e in recent_errors 
                            if e.severity == ErrorSeverity.CRITICAL)
        
        # Count total errors in last minute
        recent_minute_errors = [e for e in recent_errors 
                               if time.time() - e.timestamp < 60]
        
        # Adjust degradation level
        if critical_count >= 3:
            self.degradation.set_degradation_level('emergency', f'{critical_count} critical errors')
        elif len(recent_minute_errors) >= 20:
            self.degradation.set_degradation_level('minimal', f'{len(recent_minute_errors)} errors/minute')
        elif len(recent_minute_errors) >= 10:
            self.degradation.set_degradation_level('degraded', f'{len(recent_minute_errors)} errors/minute')
        elif len(recent_minute_errors) >= 5:
            self.degradation.set_degradation_level('degraded', f'{len(recent_minute_errors)} errors/minute')
        else:
            self.degradation.set_degradation_level('full', 'Error rate normal')
    
    def get_circuit_breaker(self, name: str, config: CircuitBreakerConfig = None) -> CircuitBreaker:
        """Get or create circuit breaker"""
        if config is None:
            config = CircuitBreakerConfig()
        
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker(name, config)
        
        return self.circuit_breakers[name]
    
    def add_error_callback(self, callback: Callable[[ErrorInfo], None]):
        """Add error callback"""
        self.error_callbacks.append(callback)
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics"""
        with self.lock:
            recent_errors = [e for e in self.error_log 
                            if time.time() - e.timestamp < 3600]  # Last hour
            
            # Calculate error rates
            error_rate_1h = len(recent_errors) / 3600  # Errors per hour
            error_rate_5m = len([e for e in recent_errors 
                               if time.time() - e.timestamp < 300]) / 300  # Errors per 5 min
            
            # Error distribution by category and severity
            category_distribution = defaultdict(lambda: defaultdict(int))
            severity_distribution = defaultdict(int)
            
            for error in recent_errors:
                category_distribution[error.category.value][error.severity.value] += 1
                severity_distribution[error.severity.value] += 1
            
            # Circuit breaker statistics
            circuit_stats = {name: cb.get_stats() 
                           for name, cb in self.circuit_breakers.items()}
            
            # Recovery statistics
            recovery_stats = {
                'active_recoveries': len(self.recovery_manager.active_recoveries),
                'recovery_strategies': len(self.recovery_manager.recovery_strategies)
            }
            
            return {
                'error_rate_per_hour': error_rate_1h,
                'error_rate_per_5min': error_rate_5m,
                'total_errors_last_hour': len(recent_errors),
                'category_distribution': dict(category_distribution),
                'severity_distribution': dict(severity_distribution),
                'circuit_breakers': circuit_stats,
                'degradation_level': self.degradation.current_level,
                'degradation_history': list(self.degradation.level_history),
                'recovery_stats': recovery_stats,
                'total_errors_in_log': len(self.error_log)
            }
    
    def get_recent_errors(self, limit: int = 100, severity: ErrorSeverity = None) -> List[ErrorInfo]:
        """Get recent errors with optional severity filter"""
        with self.lock:
            errors = list(self.error_log)
            
            if severity:
                errors = [e for e in errors if e.severity == severity]
            
            return sorted(errors, key=lambda x: x.timestamp, reverse=True)[:limit]
    
    def reset_statistics(self):
        """Reset error statistics"""
        with self.lock:
            self.error_log.clear()
            self.error_stats.clear()
            
            # Reset circuit breakers
            for cb in self.circuit_breakers.values():
                cb.reset()
            
            # Reset degradation
            self.degradation.current_level = 'full'
            self.degradation.level_history.clear()
            
            logger.info("Error handling statistics reset")

# Global error handler instance
global_error_handler = ComprehensiveErrorHandler()

def handle_error(exception: Exception, 
                module: str = "",
                function: str = "",
                context: Dict[str, Any] = None,
                user_id: str = None,
                request_id: str = None) -> ErrorInfo:
    """Global error handling function"""
    return global_error_handler.handle_error(
        exception, module, function, context, user_id, request_id
    )

def get_error_handler() -> ComprehensiveErrorHandler:
    """Get global error handler instance"""
    return global_error_handler
