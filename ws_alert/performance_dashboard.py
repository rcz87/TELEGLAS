"""
Performance Dashboard for WS Alert System - Poin 4

Module ini menyediakan real-time performance monitoring dashboard
dengan visualisasi metrics dan alerts.

Author: TELEGLAS Team
Version: Poin 4.3.0
"""

import time
import logging
import json
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import deque

from .performance_optimizer import get_performance_optimizer, PerformanceMetrics
from .enhanced_event_aggregator import get_enhanced_event_aggregator

logger = logging.getLogger("ws_alert.performance_dashboard")


@dataclass
class DashboardMetrics:
    """Comprehensive dashboard metrics"""
    timestamp: float
    cpu_usage: float
    memory_usage_mb: float
    memory_percent: float
    active_events: int
    processed_events: int
    events_per_second: float
    active_symbols: int
    total_buffers: int
    buffer_efficiency: float
    avg_processing_time_ms: float
    memory_pressure: str
    performance_level: str


@dataclass
class AlertRule:
    """Alert rule configuration"""
    name: str
    metric: str
    operator: str  # '>', '<', '>=', '<='
    threshold: float
    severity: str  # 'info', 'warning', 'critical'
    enabled: bool = True
    cooldown_minutes: int = 5
    last_triggered: float = 0.0


class PerformanceAlert:
    """Performance alert with context"""
    
    def __init__(self, rule: AlertRule, current_value: float, timestamp: float):
        self.rule = rule
        self.current_value = current_value
        self.timestamp = timestamp
        self.message = self._generate_message()
    
    def _generate_message(self) -> str:
        """Generate alert message"""
        return (f"[{self.rule.severity.upper()}] {self.rule.name}: "
                f"{self.rule.metric} {self.rule.operator} {self.rule.threshold} "
                f"(current: {self.current_value:.2f})")


class PerformanceDashboard:
    """
    Real-time Performance Dashboard
    
    Features:
    - Live metrics collection and visualization
    - Alert rules and notifications
    - Historical data tracking
    - Performance trend analysis
    """
    
    def __init__(self, history_size: int = 100):
        self.history_size = history_size
        self.lock = threading.Lock()
        
        # Data storage
        self.metrics_history: deque = deque(maxlen=history_size)
        self.alerts_history: List[PerformanceAlert] = []
        self.current_metrics: Optional[DashboardMetrics] = None
        
        # Performance components
        self.performance_optimizer = get_performance_optimizer()
        self.enhanced_aggregator = get_enhanced_event_aggregator()
        
        # Alert system
        self.alert_rules: List[AlertRule] = []
        self.alert_cooldowns: Dict[str, float] = {}
        
        # Dashboard configuration
        self.update_interval = 5.0  # seconds
        self.max_alerts_history = 50
        self.is_running = False
        self.update_thread = None
        
        # Initialize default alert rules
        self._initialize_default_alert_rules()
        
        logger.info("[DASHBOARD] Performance Dashboard initialized")
    
    def _initialize_default_alert_rules(self):
        """Initialize default alert rules"""
        default_rules = [
            AlertRule(
                name="High CPU Usage",
                metric="cpu_usage",
                operator=">",
                threshold=80.0,
                severity="warning"
            ),
            AlertRule(
                name="Critical CPU Usage",
                metric="cpu_usage",
                operator=">",
                threshold=95.0,
                severity="critical"
            ),
            AlertRule(
                name="High Memory Usage",
                metric="memory_percent",
                operator=">",
                threshold=85.0,
                severity="warning"
            ),
            AlertRule(
                name="Critical Memory Usage",
                metric="memory_percent",
                operator=">",
                threshold=95.0,
                severity="critical"
            ),
            AlertRule(
                name="High Event Rate",
                metric="events_per_second",
                operator=">",
                threshold=1000.0,
                severity="warning"
            ),
            AlertRule(
                name="Slow Processing",
                metric="avg_processing_time_ms",
                operator=">",
                threshold=100.0,
                severity="warning"
            ),
            AlertRule(
                name="Critical Memory Pressure",
                metric="memory_pressure",
                operator="==",
                threshold="critical",
                severity="critical"
            ),
            AlertRule(
                name="Low Buffer Efficiency",
                metric="buffer_efficiency",
                operator="<",
                threshold=0.5,
                severity="warning"
            )
        ]
        
        self.alert_rules.extend(default_rules)
        logger.info(f"[DASHBOARD] Initialized {len(default_rules)} default alert rules")
    
    def start_monitoring(self):
        """Start real-time monitoring"""
        if self.is_running:
            return
        
        self.is_running = True
        self.update_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.update_thread.start()
        
        logger.info("[DASHBOARD] Real-time monitoring started")
    
    def stop_monitoring(self):
        """Stop real-time monitoring"""
        self.is_running = False
        if self.update_thread:
            self.update_thread.join(timeout=10.0)
        
        logger.info("[DASHBOARD] Real-time monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                # Collect current metrics
                metrics = self._collect_current_metrics()
                
                if metrics:
                    with self.lock:
                        self.current_metrics = metrics
                        self.metrics_history.append(metrics)
                    
                    # Check alert rules
                    self._check_alert_rules(metrics)
                
                time.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"[DASHBOARD] Error in monitoring loop: {e}")
                time.sleep(self.update_interval)
    
    def _collect_current_metrics(self) -> Optional[DashboardMetrics]:
        """Collect current performance metrics"""
        try:
            # Get performance optimizer metrics
            perf_dashboard = self.performance_optimizer.get_performance_dashboard()
            perf_metrics = perf_dashboard.get('performance_metrics', {}).get('current', {})
            memory_stats = perf_dashboard.get('memory_stats', {})
            
            # Get enhanced aggregator stats
            agg_stats = self.enhanced_aggregator.get_enhanced_stats()
            system_health = agg_stats.get('system_health', {})
            basic_stats = agg_stats.get('basic_stats', {})
            
            # Calculate buffer efficiency
            buffer_efficiency = self._calculate_buffer_efficiency(agg_stats.get('buffer_stats', {}))
            
            # Determine performance level
            performance_level = self._determine_performance_level(perf_metrics, memory_stats)
            
            # Create dashboard metrics
            metrics = DashboardMetrics(
                timestamp=time.time(),
                cpu_usage=perf_metrics.get('cpu_usage', 0.0),
                memory_usage_mb=perf_metrics.get('memory_usage_mb', 0.0),
                memory_percent=perf_metrics.get('memory_percent', 0.0),
                active_events=system_health.get('total_events', 0),
                processed_events=basic_stats.get('events_processed', 0),
                events_per_second=perf_metrics.get('events_per_second', 0.0),
                active_symbols=system_health.get('total_buffers', 0),
                total_buffers=system_health.get('total_buffers', 0),
                buffer_efficiency=buffer_efficiency,
                avg_processing_time_ms=basic_stats.get('avg_processing_time_ms', 0.0),
                memory_pressure=memory_stats.get('memory_pressure_level', 'low'),
                performance_level=performance_level
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"[DASHBOARD] Error collecting metrics: {e}")
            return None
    
    def _calculate_buffer_efficiency(self, buffer_stats: Dict[str, Any]) -> float:
        """Calculate average buffer efficiency"""
        if not buffer_stats:
            return 0.0
        
        total_efficiency = 0.0
        count = 0
        
        for stats in buffer_stats.values():
            if isinstance(stats, dict) and 'buffer_efficiency' in stats:
                total_efficiency += stats['buffer_efficiency']
                count += 1
        
        return total_efficiency / max(count, 1)
    
    def _determine_performance_level(self, perf_metrics: Dict, memory_stats: Dict) -> str:
        """Determine overall performance level"""
        cpu_usage = perf_metrics.get('cpu_usage', 0.0)
        memory_percent = perf_metrics.get('memory_percent', 0.0)
        memory_pressure = memory_stats.get('memory_pressure_level', 'low')
        
        if (cpu_usage > 90 or memory_percent > 90 or memory_pressure == 'critical'):
            return 'critical'
        elif (cpu_usage > 70 or memory_percent > 80 or memory_pressure == 'high'):
            return 'degraded'
        elif (cpu_usage > 50 or memory_percent > 60):
            return 'moderate'
        else:
            return 'optimal'
    
    def _check_alert_rules(self, metrics: DashboardMetrics):
        """Check alert rules against current metrics"""
        current_time = time.time()
        
        for rule in self.alert_rules:
            if not rule.enabled:
                continue
            
            # Check cooldown
            last_triggered = self.alert_cooldowns.get(rule.name, 0.0)
            if current_time - last_triggered < (rule.cooldown_minutes * 60):
                continue
            
            # Get metric value
            metric_value = getattr(metrics, rule.metric, None)
            if metric_value is None:
                continue
            
            # Check threshold
            triggered = False
            if rule.operator == '>':
                triggered = metric_value > rule.threshold
            elif rule.operator == '>=':
                triggered = metric_value >= rule.threshold
            elif rule.operator == '<':
                triggered = metric_value < rule.threshold
            elif rule.operator == '<=':
                triggered = metric_value <= rule.threshold
            elif rule.operator == '==':
                triggered = str(metric_value) == str(rule.threshold)
            
            if triggered:
                # Create alert
                alert = PerformanceAlert(rule, metric_value, current_time)
                
                # Add to history
                self.alerts_history.append(alert)
                if len(self.alerts_history) > self.max_alerts_history:
                    self.alerts_history.pop(0)
                
                # Update cooldown
                self.alert_cooldowns[rule.name] = current_time
                
                # Log alert
                logger.warning(f"[DASHBOARD] ALERT: {alert.message}")
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        with self.lock:
            # Current metrics
            current = asdict(self.current_metrics) if self.current_metrics else {}
            
            # Historical data
            history = [asdict(m) for m in self.metrics_history]
            
            # Active alerts
            recent_alerts = []
            current_time = time.time()
            for alert in self.alerts_history:
                if current_time - alert.timestamp < 3600:  # Last hour
                    recent_alerts.append({
                        'message': alert.message,
                        'severity': alert.rule.severity,
                        'timestamp': alert.timestamp,
                        'rule_name': alert.rule.name
                    })
            
            # Performance summary
            performance_summary = self._generate_performance_summary()
            
            return {
                'current_metrics': current,
                'historical_data': history,
                'recent_alerts': recent_alerts,
                'performance_summary': performance_summary,
                'alert_rules': [asdict(rule) for rule in self.alert_rules],
                'dashboard_info': {
                    'is_monitoring': self.is_running,
                    'update_interval': self.update_interval,
                    'history_size': len(self.metrics_history),
                    'total_alerts': len(self.alerts_history)
                }
            }
    
    def _generate_performance_summary(self) -> Dict[str, Any]:
        """Generate performance summary statistics"""
        if not self.metrics_history:
            return {}
        
        # Calculate averages
        cpu_values = [m.cpu_usage for m in self.metrics_history]
        memory_values = [m.memory_percent for m in self.metrics_history]
        event_rates = [m.events_per_second for m in self.metrics_history]
        
        return {
            'avg_cpu_usage': sum(cpu_values) / len(cpu_values),
            'max_cpu_usage': max(cpu_values),
            'avg_memory_percent': sum(memory_values) / len(memory_values),
            'max_memory_percent': max(memory_values),
            'avg_event_rate': sum(event_rates) / len(event_rates),
            'max_event_rate': max(event_rates),
            'uptime_minutes': len(self.metrics_history) * self.update_interval / 60,
            'total_alerts_last_hour': len([
                a for a in self.alerts_history 
                if time.time() - a.timestamp < 3600
            ])
        }
    
    def add_alert_rule(self, rule: AlertRule):
        """Add custom alert rule"""
        with self.lock:
            self.alert_rules.append(rule)
            logger.info(f"[DASHBOARD] Added alert rule: {rule.name}")
    
    def remove_alert_rule(self, rule_name: str):
        """Remove alert rule by name"""
        with self.lock:
            original_count = len(self.alert_rules)
            self.alert_rules = [r for r in self.alert_rules if r.name != rule_name]
            removed = original_count - len(self.alert_rules)
            if removed > 0:
                logger.info(f"[DASHBOARD] Removed {removed} alert rule(s): {rule_name}")
    
    def get_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate performance report for specified time period"""
        cutoff_time = time.time() - (hours * 3600)
        
        with self.lock:
            # Filter metrics by time
            period_metrics = [
                m for m in self.metrics_history 
                if m.timestamp >= cutoff_time
            ]
            
            if not period_metrics:
                return {'error': f'No data available for the last {hours} hours'}
            
            # Calculate statistics
            cpu_values = [m.cpu_usage for m in period_metrics]
            memory_values = [m.memory_percent for m in period_metrics]
            event_rates = [m.events_per_second for m in period_metrics]
            
            # Alerts in period
            period_alerts = [
                a for a in self.alerts_history 
                if a.timestamp >= cutoff_time
            ]
            
            # Alert severity breakdown
            alert_breakdown = {}
            for alert in period_alerts:
                severity = alert.rule.severity
                alert_breakdown[severity] = alert_breakdown.get(severity, 0) + 1
            
            return {
                'period_hours': hours,
                'data_points': len(period_metrics),
                'time_range': {
                    'start': min(m.timestamp for m in period_metrics),
                    'end': max(m.timestamp for m in period_metrics)
                },
                'performance_stats': {
                    'cpu': {
                        'avg': sum(cpu_values) / len(cpu_values),
                        'min': min(cpu_values),
                        'max': max(cpu_values)
                    },
                    'memory': {
                        'avg': sum(memory_values) / len(memory_values),
                        'min': min(memory_values),
                        'max': max(memory_values)
                    },
                    'events_per_second': {
                        'avg': sum(event_rates) / len(event_rates),
                        'min': min(event_rates),
                        'max': max(event_rates)
                    }
                },
                'alerts': {
                    'total': len(period_alerts),
                    'by_severity': alert_breakdown,
                    'rate_per_hour': len(period_alerts) / hours
                }
            }
    
    def export_metrics(self, filename: str, format: str = 'json'):
        """Export metrics to file"""
        try:
            dashboard_data = self.get_dashboard_data()
            
            if format.lower() == 'json':
                with open(filename, 'w') as f:
                    json.dump(dashboard_data, f, indent=2, default=str)
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            logger.info(f"[DASHBOARD] Metrics exported to {filename}")
            
        except Exception as e:
            logger.error(f"[DASHBOARD] Error exporting metrics: {e}")
    
    def reset_metrics(self):
        """Reset all metrics and history"""
        with self.lock:
            self.metrics_history.clear()
            self.alerts_history.clear()
            self.alert_cooldowns.clear()
            self.current_metrics = None
            
            logger.info("[DASHBOARD] Metrics reset")


# Global dashboard instance
_performance_dashboard = None


def get_performance_dashboard() -> PerformanceDashboard:
    """Get global performance dashboard instance"""
    global _performance_dashboard
    if _performance_dashboard is None:
        _performance_dashboard = PerformanceDashboard()
    return _performance_dashboard
