"""
Log Viewer Utility for AI Agent
Provides tools to monitor and analyze logs in real-time
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
import argparse

class LogViewer:
    """
    Utility to view and analyze AI agent logs
    """
    
    def __init__(self, log_dir: str = "data/logs"):
        self.log_dir = Path(log_dir)
        
    def get_log_files(self) -> Dict[str, Path]:
        """Get all available log files"""
        log_files = {}
        if self.log_dir.exists():
            for log_file in self.log_dir.glob("*.log"):
                log_files[log_file.stem] = log_file
        return log_files
    
    def tail_log(self, log_file: str, lines: int = 50, follow: bool = False):
        """Tail a log file (like Unix tail command)"""
        log_path = self.log_dir / f"{log_file}.log"
        
        if not log_path.exists():
            print(f"❌ Log file not found: {log_path}")
            return
        
        # Read last N lines
        with open(log_path, 'r') as f:
            all_lines = f.readlines()
            last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            
        print(f"📋 Last {len(last_lines)} lines from {log_file}.log:")
        print("=" * 80)
        for line in last_lines:
            print(line.rstrip())
        
        if follow:
            print(f"\n🔄 Following {log_file}.log (Ctrl+C to stop)...")
            try:
                with open(log_path, 'r') as f:
                    # Go to end of file
                    f.seek(0, 2)
                    
                    while True:
                        line = f.readline()
                        if line:
                            print(line.rstrip())
                        else:
                            time.sleep(0.1)
            except KeyboardInterrupt:
                print("\n⏹️  Stopped following log")
    
    def search_logs(self, search_term: str, log_files: List[str] = None, 
                   case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """Search logs for specific terms"""
        results = []
        
        if log_files is None:
            log_files = list(self.get_log_files().keys())
        
        for log_file in log_files:
            log_path = self.log_dir / f"{log_file}.log"
            
            if not log_path.exists():
                continue
            
            with open(log_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    if not case_sensitive:
                        line_lower = line.lower()
                        search_lower = search_term.lower()
                        if search_lower in line_lower:
                            results.append({
                                'file': log_file,
                                'line_number': line_num,
                                'line': line.rstrip(),
                                'timestamp': self._extract_timestamp(line)
                            })
                    else:
                        if search_term in line:
                            results.append({
                                'file': log_file,
                                'line_number': line_num,
                                'line': line.rstrip(),
                                'timestamp': self._extract_timestamp(line)
                            })
        
        return results
    
    def _extract_timestamp(self, line: str) -> Optional[str]:
        """Extract timestamp from log line"""
        try:
            # Look for timestamp at beginning of line
            parts = line.split(' - ', 1)
            if len(parts) > 1:
                return parts[0]
        except:
            pass
        return None
    
    def get_recent_activity(self, hours: int = 1) -> Dict[str, List[Dict[str, Any]]]:
        """Get recent activity from all logs"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_activity = {}
        
        for log_file in self.get_log_files().keys():
            log_path = self.log_dir / f"{log_file}.log"
            
            if not log_path.exists():
                continue
            
            recent_activity[log_file] = []
            
            with open(log_path, 'r') as f:
                for line in f:
                    timestamp = self._extract_timestamp(line)
                    if timestamp:
                        try:
                            log_time = datetime.fromisoformat(timestamp.replace(' ', 'T'))
                            if log_time >= cutoff_time:
                                recent_activity[log_file].append({
                                    'timestamp': timestamp,
                                    'line': line.rstrip()
                                })
                        except:
                            pass
        
        return recent_activity
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary of errors in the last N hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        error_summary = {
            'total_errors': 0,
            'errors_by_type': {},
            'errors_by_file': {},
            'recent_errors': []
        }
        
        for log_file in self.get_log_files().keys():
            log_path = self.log_dir / f"{log_file}.log"
            
            if not log_path.exists():
                continue
            
            file_errors = 0
            
            with open(log_path, 'r') as f:
                for line in f:
                    if 'ERROR' in line or 'error' in line.lower():
                        timestamp = self._extract_timestamp(line)
                        if timestamp:
                            try:
                                log_time = datetime.fromisoformat(timestamp.replace(' ', 'T'))
                                if log_time >= cutoff_time:
                                    file_errors += 1
                                    error_summary['total_errors'] += 1
                                    
                                    # Extract error type
                                    if 'ERROR:' in line:
                                        error_type = line.split('ERROR:')[1].split('{')[0].strip()
                                    else:
                                        error_type = 'unknown'
                                    
                                    error_summary['errors_by_type'][error_type] = \
                                        error_summary['errors_by_type'].get(error_type, 0) + 1
                                    
                                    error_summary['recent_errors'].append({
                                        'timestamp': timestamp,
                                        'file': log_file,
                                        'line': line.rstrip(),
                                        'error_type': error_type
                                    })
                            except:
                                pass
            
            if file_errors > 0:
                error_summary['errors_by_file'][log_file] = file_errors
        
        return error_summary
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance metrics summary"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        performance_summary = {
            'total_metrics': 0,
            'metrics_by_type': {},
            'average_durations': {},
            'slowest_operations': []
        }
        
        log_path = self.log_dir / "performance.log"
        
        if not log_path.exists():
            return performance_summary
        
        with open(log_path, 'r') as f:
            for line in f:
                if 'PERFORMANCE_METRIC:' in line:
                    timestamp = self._extract_timestamp(line)
                    if timestamp:
                        try:
                            log_time = datetime.fromisoformat(timestamp.replace(' ', 'T'))
                            if log_time >= cutoff_time:
                                performance_summary['total_metrics'] += 1
                                
                                # Parse the JSON part
                                json_start = line.find('{')
                                if json_start != -1:
                                    json_str = line[json_start:]
                                    metric_data = json.loads(json_str)
                                    
                                    metric_name = metric_data.get('metric_name', 'unknown')
                                    value = metric_data.get('value', 0)
                                    unit = metric_data.get('unit', 'unknown')
                                    
                                    if metric_name not in performance_summary['metrics_by_type']:
                                        performance_summary['metrics_by_type'][metric_name] = {
                                            'count': 0,
                                            'total_value': 0,
                                            'unit': unit,
                                            'values': []
                                        }
                                    
                                    perf_type = performance_summary['metrics_by_type'][metric_name]
                                    perf_type['count'] += 1
                                    perf_type['total_value'] += value
                                    perf_type['values'].append(value)
                                    
                                    # Track slowest operations
                                    if 'duration' in metric_name.lower():
                                        performance_summary['slowest_operations'].append({
                                            'metric': metric_name,
                                            'value': value,
                                            'unit': unit,
                                            'timestamp': timestamp
                                        })
                                        
                                        # Keep only top 10 slowest
                                        performance_summary['slowest_operations'].sort(
                                            key=lambda x: x['value'], reverse=True
                                        )
                                        performance_summary['slowest_operations'] = \
                                            performance_summary['slowest_operations'][:10]
                                        
                        except:
                            pass
        
        # Calculate averages
        for metric_name, data in performance_summary['metrics_by_type'].items():
            if data['count'] > 0:
                data['average'] = data['total_value'] / data['count']
        
        return performance_summary
    
    def get_agent_activity_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary of AI agent activity"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        activity_summary = {
            'total_actions': 0,
            'actions_by_type': {},
            'tools_used': {},
            'decisions_made': 0,
            'recent_actions': []
        }
        
        log_path = self.log_dir / "agent_actions.log"
        
        if not log_path.exists():
            return activity_summary
        
        with open(log_path, 'r') as f:
            for line in f:
                if 'AGENT_ACTION:' in line or 'AGENT_DECISION:' in line:
                    timestamp = self._extract_timestamp(line)
                    if timestamp:
                        try:
                            log_time = datetime.fromisoformat(timestamp.replace(' ', 'T'))
                            if log_time >= cutoff_time:
                                # Parse the JSON part
                                json_start = line.find('{')
                                if json_start != -1:
                                    json_str = line[json_start:]
                                    action_data = json.loads(json_str)
                                    
                                    action = action_data.get('action', 'unknown')
                                    tool = action_data.get('tool', 'unknown')
                                    
                                    activity_summary['total_actions'] += 1
                                    activity_summary['actions_by_type'][action] = \
                                        activity_summary['actions_by_type'].get(action, 0) + 1
                                    activity_summary['tools_used'][tool] = \
                                        activity_summary['tools_used'].get(tool, 0) + 1
                                    
                                    if 'AGENT_DECISION:' in line:
                                        activity_summary['decisions_made'] += 1
                                    
                                    activity_summary['recent_actions'].append({
                                        'timestamp': timestamp,
                                        'action': action,
                                        'tool': tool,
                                        'confidence': action_data.get('confidence'),
                                        'reasoning': action_data.get('reasoning')
                                    })
                                    
                                    # Keep only recent 20 actions
                                    activity_summary['recent_actions'] = \
                                        activity_summary['recent_actions'][-20:]
                                        
                        except:
                            pass
        
        return activity_summary
    
    def print_summary(self, hours: int = 24):
        """Print a comprehensive summary of recent activity"""
        print(f"📊 AI Agent Activity Summary (Last {hours} hours)")
        print("=" * 80)
        
        # Error summary
        error_summary = self.get_error_summary(hours)
        print(f"🚨 Errors: {error_summary['total_errors']} total")
        if error_summary['errors_by_type']:
            print("   By type:")
            for error_type, count in error_summary['errors_by_type'].items():
                print(f"     {error_type}: {count}")
        
        # Performance summary
        perf_summary = self.get_performance_summary(hours)
        print(f"⚡ Performance Metrics: {perf_summary['total_metrics']} total")
        if perf_summary['metrics_by_type']:
            print("   Averages:")
            for metric_name, data in perf_summary['metrics_by_type'].items():
                if 'average' in data:
                    print(f"     {metric_name}: {data['average']:.2f} {data['unit']}")
        
        # Agent activity summary
        activity_summary = self.get_agent_activity_summary(hours)
        print(f"🤖 Agent Actions: {activity_summary['total_actions']} total")
        print(f"   Decisions Made: {activity_summary['decisions_made']}")
        if activity_summary['actions_by_type']:
            print("   Actions by type:")
            for action, count in activity_summary['actions_by_type'].items():
                print(f"     {action}: {count}")
        
        if activity_summary['tools_used']:
            print("   Tools used:")
            for tool, count in activity_summary['tools_used'].items():
                print(f"     {tool}: {count}")
        
        print("=" * 80)

def main():
    """Command line interface for log viewer"""
    parser = argparse.ArgumentParser(description="AI Agent Log Viewer")
    parser.add_argument("--log-dir", default="data/logs", help="Log directory path")
    parser.add_argument("--tail", help="Tail a specific log file")
    parser.add_argument("--lines", type=int, default=50, help="Number of lines to show")
    parser.add_argument("--follow", action="store_true", help="Follow log file")
    parser.add_argument("--search", help="Search for term in logs")
    parser.add_argument("--summary", action="store_true", help="Show activity summary")
    parser.add_argument("--hours", type=int, default=24, help="Hours to look back")
    
    args = parser.parse_args()
    
    viewer = LogViewer(args.log_dir)
    
    if args.tail:
        viewer.tail_log(args.tail, args.lines, args.follow)
    elif args.search:
        results = viewer.search_logs(args.search)
        print(f"🔍 Found {len(results)} matches for '{args.search}':")
        for result in results:
            print(f"  {result['file']}:{result['line_number']} - {result['line']}")
    elif args.summary:
        viewer.print_summary(args.hours)
    else:
        # Show available logs
        log_files = viewer.get_log_files()
        print("📁 Available log files:")
        for name, path in log_files.items():
            size = path.stat().st_size if path.exists() else 0
            print(f"  {name}.log ({size} bytes)")

if __name__ == "__main__":
    main()
