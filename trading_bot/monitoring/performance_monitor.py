"""Comprehensive performance monitoring and alerting system."""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics container."""
    component: str
    metric_name: str
    value: float
    timestamp: float
    unit: str = ""
    
    def age_seconds(self) -> float:
        """Get age of metric in seconds."""
        return time.time() - self.timestamp


@dataclass
class PerformanceAlert:
    """Performance alert container."""
    component: str
    metric_name: str
    alert_type: str  # "threshold", "trend", "anomaly"
    message: str
    severity: str  # "low", "medium", "high", "critical"
    timestamp: float
    value: Optional[float] = None
    threshold: Optional[float] = None


class PerformanceMonitor:
    """Comprehensive performance monitoring system."""
    
    def __init__(
        self,
        max_history: int = 1000,
        alert_cooldown: int = 300  # 5 minutes
    ):
        """Initialize performance monitor.
        
        Args:
            max_history: Maximum number of metrics to keep in history
            alert_cooldown: Minimum seconds between similar alerts
        """
        self.max_history = max_history
        self.alert_cooldown = alert_cooldown
        
        # Metrics storage
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self.current_metrics: Dict[str, PerformanceMetrics] = {}
        
        # Alerts
        self.alerts: List[PerformanceAlert] = []
        self.last_alert_time: Dict[str, float] = {}
        
        # Thresholds
        self.thresholds = {
            # Execution time thresholds (seconds)
            'api_call_latency': {'warning': 2.0, 'critical': 5.0},
            'decision_time': {'warning': 3.0, 'critical': 8.0},
            'analysis_time': {'warning': 5.0, 'critical': 15.0},
            'total_cycle_time': {'warning': 10.0, 'critical': 30.0},
            
            # Success rate thresholds (percentage)
            'api_success_rate': {'warning': 95.0, 'critical': 90.0},
            'cache_hit_rate': {'warning': 70.0, 'critical': 50.0},
            
            # Memory thresholds (MB)
            'memory_usage': {'warning': 200.0, 'critical': 500.0},
            'cache_size': {'warning': 40.0, 'critical': 50.0},
            
            # Trading thresholds
            'confidence_score': {'warning': 0.4, 'critical': 0.2},
            'portfolio_risk': {'warning': 1.8, 'critical': 2.0}
        }
    
    def record_metric(
        self,
        component: str,
        metric_name: str,
        value: float,
        unit: str = ""
    ) -> None:
        """Record a performance metric.
        
        Args:
            component: Component name (e.g., 'decision_engine', 'okx_connector')
            metric_name: Metric name (e.g., 'execution_time', 'success_rate')
            value: Metric value
            unit: Unit of measurement (optional)
        """
        metric = PerformanceMetrics(
            component=component,
            metric_name=metric_name,
            value=value,
            timestamp=time.time(),
            unit=unit
        )
        
        key = f"{component}.{metric_name}"
        self.metrics_history[key].append(metric)
        self.current_metrics[key] = metric
        
        # Check for threshold violations
        self._check_thresholds(key, metric)
    
    def record_execution_time(self, component: str, operation: str, start_time: float) -> float:
        """Record execution time for an operation.
        
        Args:
            component: Component name
            operation: Operation name
            start_time: Start time from time.time()
            
        Returns:
            Execution time in seconds
        """
        execution_time = time.time() - start_time
        self.record_metric(component, f"{operation}_time", execution_time, "seconds")
        return execution_time
    
    def record_success_rate(self, component: str, operation: str, success: bool) -> None:
        """Record success/failure for calculating success rates.
        
        Args:
            component: Component name
            operation: Operation name
            success: Whether operation was successful
        """
        key = f"{component}.{operation}_success"
        
        # Get recent successes/failures
        recent_metrics = list(self.metrics_history[key])[-100:]  # Last 100 operations
        
        if recent_metrics:
            recent_successes = sum(1 for m in recent_metrics if m.value == 1.0)
            success_rate = (recent_successes / len(recent_metrics)) * 100
        else:
            success_rate = 100.0 if success else 0.0
        
        # Record individual success/failure
        self.record_metric(component, f"{operation}_success", 1.0 if success else 0.0)
        
        # Record calculated success rate
        self.record_metric(component, f"{operation}_success_rate", success_rate, "percent")
    
    def _check_thresholds(self, key: str, metric: PerformanceMetrics) -> None:
        """Check metric against thresholds and generate alerts."""
        metric_name = metric.metric_name
        
        if metric_name not in self.thresholds:
            return
        
        thresholds = self.thresholds[metric_name]
        alert_key = f"{metric.component}.{metric_name}"
        
        # Check cooldown
        if alert_key in self.last_alert_time:
            if time.time() - self.last_alert_time[alert_key] < self.alert_cooldown:
                return
        
        # Check thresholds
        severity = None
        threshold_value = None
        
        if 'critical' in thresholds and self._exceeds_threshold(metric_name, metric.value, thresholds['critical']):
            severity = "critical"
            threshold_value = thresholds['critical']
        elif 'warning' in thresholds and self._exceeds_threshold(metric_name, metric.value, thresholds['warning']):
            severity = "warning"
            threshold_value = thresholds['warning']
        
        if severity:
            alert = PerformanceAlert(
                component=metric.component,
                metric_name=metric_name,
                alert_type="threshold",
                message=f"{metric.component}.{metric_name} = {metric.value:.2f}{metric.unit} exceeds {severity} threshold ({threshold_value})",
                severity=severity,
                timestamp=time.time(),
                value=metric.value,
                threshold=threshold_value
            )
            
            self.alerts.append(alert)
            self.last_alert_time[alert_key] = time.time()
            
            # Log alert
            log_func = logger.critical if severity == "critical" else logger.warning
            log_func("PERFORMANCE ALERT: %s", alert.message)
    
    def _exceeds_threshold(self, metric_name: str, value: float, threshold: float) -> bool:
        """Check if value exceeds threshold based on metric type."""
        # For success rates and confidence scores, lower is worse
        if metric_name in ['api_success_rate', 'cache_hit_rate', 'confidence_score']:
            return value < threshold
        
        # For everything else, higher is worse
        return value > threshold
    
    def get_current_metrics(self, component: Optional[str] = None) -> Dict[str, PerformanceMetrics]:
        """Get current metrics, optionally filtered by component."""
        if component:
            return {k: v for k, v in self.current_metrics.items() if v.component == component}
        return self.current_metrics.copy()
    
    def get_metric_history(self, component: str, metric_name: str, limit: int = 100) -> List[PerformanceMetrics]:
        """Get metric history for a specific metric."""
        key = f"{component}.{metric_name}"
        history = list(self.metrics_history.get(key, []))
        return history[-limit:] if limit else history
    
    def get_recent_alerts(self, severity: Optional[str] = None, limit: int = 50) -> List[PerformanceAlert]:
        """Get recent alerts, optionally filtered by severity."""
        alerts = self.alerts[-limit:] if limit else self.alerts
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)
    
    def calculate_average_metric(self, component: str, metric_name: str, minutes: int = 5) -> Optional[float]:
        """Calculate average metric value over specified time period."""
        key = f"{component}.{metric_name}"
        history = self.metrics_history.get(key, [])
        
        if not history:
            return None
        
        cutoff_time = time.time() - (minutes * 60)
        recent_metrics = [m for m in history if m.timestamp > cutoff_time]
        
        if not recent_metrics:
            return None
        
        return sum(m.value for m in recent_metrics) / len(recent_metrics)
    
    def get_performance_summary(self) -> Dict[str, any]:
        """Get comprehensive performance summary."""
        summary = {
            'timestamp': time.time(),
            'total_metrics': len(self.current_metrics),
            'components': list(set(m.component for m in self.current_metrics.values())),
            'recent_alerts': len([a for a in self.alerts if time.time() - a.timestamp < 3600]),  # Last hour
            'critical_alerts': len([a for a in self.alerts if a.severity == "critical" and time.time() - a.timestamp < 3600])
        }
        
        # Add key metrics
        key_metrics = {}
        for component in summary['components']:
            component_metrics = self.get_current_metrics(component)
            
            for key, metric in component_metrics.items():
                if any(important in metric.metric_name for important in ['time', 'rate', 'latency']):
                    key_metrics[key] = {
                        'value': metric.value,
                        'unit': metric.unit,
                        'age_seconds': metric.age_seconds()
                    }
        
        summary['key_metrics'] = key_metrics
        
        return summary
    
    def clear_old_data(self, max_age_hours: int = 24) -> None:
        """Clear old metrics and alerts."""
        cutoff_time = time.time() - (max_age_hours * 3600)
        
        # Clear old alerts
        self.alerts = [a for a in self.alerts if a.timestamp > cutoff_time]
        
        # Clear old metrics from current_metrics if stale
        stale_keys = [k for k, m in self.current_metrics.items() if m.timestamp < cutoff_time]
        for key in stale_keys:
            del self.current_metrics[key]
        
        logger.info("Cleared performance data older than %d hours", max_age_hours)
    
    def export_metrics(self, format: str = "dict") -> any:
        """Export metrics in specified format."""
        if format == "dict":
            return {
                'current_metrics': {k: {
                    'component': m.component,
                    'metric_name': m.metric_name,
                    'value': m.value,
                    'unit': m.unit,
                    'timestamp': m.timestamp
                } for k, m in self.current_metrics.items()},
                'recent_alerts': [{
                    'component': a.component,
                    'metric_name': a.metric_name,
                    'alert_type': a.alert_type,
                    'message': a.message,
                    'severity': a.severity,
                    'timestamp': a.timestamp,
                    'value': a.value,
                    'threshold': a.threshold
                } for a in self.get_recent_alerts(limit=100)]
            }
        else:
            raise ValueError(f"Unsupported export format: {format}")


# Global performance monitor instance
_global_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get or create global performance monitor."""
    global _global_monitor
    
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    
    return _global_monitor


def record_performance(component: str, metric_name: str, value: float, unit: str = "") -> None:
    """Convenience function to record performance metric."""
    monitor = get_performance_monitor()
    monitor.record_metric(component, metric_name, value, unit)


class PerformanceTimer:
    """Context manager for timing operations."""
    
    def __init__(self, component: str, operation: str):
        """Initialize performance timer.
        
        Args:
            component: Component name
            operation: Operation name
        """
        self.component = component
        self.operation = operation
        self.start_time = None
    
    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing and record metric."""
        if self.start_time:
            monitor = get_performance_monitor()
            monitor.record_execution_time(self.component, self.operation, self.start_time)
