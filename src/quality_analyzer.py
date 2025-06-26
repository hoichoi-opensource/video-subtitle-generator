"""
Quality Analyzer
Analyzes and compares subtitle quality
"""

import re
from typing import List, Dict, Tuple, Optional
from config_manager import ConfigManager

class QualityAnalyzer:
    def __init__(self, config: ConfigManager):
        self.config = config
        
    def analyze_subtitle(self, srt_content: str) -> Dict[str, Any]:
        """Analyze subtitle quality metrics"""
        metrics = {
            'total_subtitles': 0,
            'total_words': 0,
            'total_characters': 0,
            'avg_words_per_subtitle': 0,
            'avg_chars_per_subtitle': 0,
            'avg_duration': 0,
            'reading_speed': 0,  # Characters per second
            'timing_issues': 0,
            'empty_subtitles': 0,
            'overlapping_subtitles': 0
        }
        
        # Parse SRT content
        entries = self._parse_srt(srt_content)
        
        if not entries:
            return metrics
            
        metrics['total_subtitles'] = len(entries)
        
        total_duration = 0
        previous_end = None
        
        for i, entry in enumerate(entries):
            # Word and character count
            text = entry['text']
            words = len(text.split())
            chars = len(text)
            
            metrics['total_words'] += words
            metrics['total_characters'] += chars
            
            # Check for empty subtitles
            if not text.strip():
                metrics['empty_subtitles'] += 1
                
            # Duration analysis
            duration = entry['duration']
            total_duration += duration
            
            # Reading speed (characters per second)
            if duration > 0:
                cps = chars / duration
                if cps > 25:  # Industry standard is ~20-25 CPS
                    metrics['timing_issues'] += 1
                    
            # Check for overlapping subtitles
            if previous_end and entry['start'] < previous_end:
                metrics['overlapping_subtitles'] += 1
                
            previous_end = entry['end']
            
        # Calculate averages
        if metrics['total_subtitles'] > 0:
            metrics['avg_words_per_subtitle'] = metrics['total_words'] / metrics['total_subtitles']
            metrics['avg_chars_per_subtitle'] = metrics['total_characters'] / metrics['total_subtitles']
            metrics['avg_duration'] = total_duration / metrics['total_subtitles']
            
        if total_duration > 0:
            metrics['reading_speed'] = metrics['total_characters'] / total_duration
            
        return metrics
        
    def compare_subtitles(self, srt1: str, srt2: str) -> Dict[str, any]:
        """Compare two subtitle versions"""
        metrics1 = self.analyze_subtitle(srt1)
        metrics2 = self.analyze_subtitle(srt2)
        
        comparison = {
            'subtitle1': metrics1,
            'subtitle2': metrics2,
            'differences': {},
            'recommendation': ''
        }
        
        # Calculate differences
        for key in metrics1:
            if isinstance(metrics1[key], (int, float)):
                diff = metrics2[key] - metrics1[key]
                comparison['differences'][key] = diff
                
        # Make recommendation based on quality metrics
        score1 = self._calculate_quality_score(metrics1)
        score2 = self._calculate_quality_score(metrics2)
        
        if score1 > score2:
            comparison['recommendation'] = 'subtitle1'
        elif score2 > score1:
            comparison['recommendation'] = 'subtitle2'
        else:
            comparison['recommendation'] = 'equal'
            
        comparison['scores'] = {
            'subtitle1': score1,
            'subtitle2': score2
        }
        
        return comparison
        
    def _parse_srt(self, content: str) -> List[Dict[str, any]]:
        """Parse SRT content into entries with timing info"""
        entries = []
        blocks = re.split(r'\n\s*\n', content.strip())
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                try:
                    # Parse timestamp
                    timestamp_match = re.match(
                        r'(\d{1,2}:\d{2}:\d{2}[,\.]\d{1,3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,\.]\d{1,3})',
                        lines[1]
                    )
                    
                    if timestamp_match:
                        start = self._timestamp_to_seconds(timestamp_match.group(1))
                        end = self._timestamp_to_seconds(timestamp_match.group(2))
                        text = '\n'.join(lines[2:])
                        
                        entries.append({
                            'start': start,
                            'end': end,
                            'duration': end - start,
                            'text': text
                        })
                except:
                    continue
                    
        return entries
        
    def _timestamp_to_seconds(self, timestamp: str) -> float:
        """Convert SRT timestamp to seconds"""
        timestamp = timestamp.replace(',', '.')
        parts = timestamp.split(':')
        
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        
        return hours * 3600 + minutes * 60 + seconds
        
    def _calculate_quality_score(self, metrics: Dict[str, any]) -> float:
        """Calculate overall quality score"""
        score = 100.0
        
        # Penalties
        if metrics['total_subtitles'] == 0:
            return 0.0
            
        # Reading speed penalty (ideal is 15-20 CPS)
        reading_speed = metrics['reading_speed']
        if reading_speed > 25:
            score -= (reading_speed - 25) * 2
        elif reading_speed < 10:
            score -= (10 - reading_speed) * 2
            
        # Timing issues penalty
        timing_issue_rate = metrics['timing_issues'] / metrics['total_subtitles']
        score -= timing_issue_rate * 20
        
        # Empty subtitles penalty
        empty_rate = metrics['empty_subtitles'] / metrics['total_subtitles']
        score -= empty_rate * 30
        
        # Overlapping subtitles penalty
        overlap_rate = metrics['overlapping_subtitles'] / metrics['total_subtitles']
        score -= overlap_rate * 25
        
        # Average subtitle length (ideal is 10-15 words)
        avg_words = metrics['avg_words_per_subtitle']
        if avg_words > 20:
            score -= (avg_words - 20) * 1
        elif avg_words < 5:
            score -= (5 - avg_words) * 2
            
        return max(0.0, min(100.0, score))
        
    def generate_quality_report(self, srt_content: str, language: str) -> str:
        """Generate a quality report for subtitles"""
        metrics = self.analyze_subtitle(srt_content)
        score = self._calculate_quality_score(metrics)
        
        report = f"""
Subtitle Quality Report - {language.upper()}
{'=' * 40}

Overall Score: {score:.1f}/100

Metrics:
- Total Subtitles: {metrics['total_subtitles']}
- Total Words: {metrics['total_words']}
- Average Words per Subtitle: {metrics['avg_words_per_subtitle']:.1f}
- Reading Speed: {metrics['reading_speed']:.1f} CPS
- Average Duration: {metrics['avg_duration']:.1f}s

Issues Found:
- Timing Issues: {metrics['timing_issues']}
- Empty Subtitles: {metrics['empty_subtitles']}
- Overlapping Subtitles: {metrics['overlapping_subtitles']}

Recommendations:
"""
        
        if metrics['reading_speed'] > 25:
            report += "- Reading speed is too high. Consider splitting long subtitles.\n"
        elif metrics['reading_speed'] < 10:
            report += "- Reading speed is too low. Consider combining short subtitles.\n"
            
        if metrics['timing_issues'] > 0:
            report += "- Some subtitles have timing issues. Review and adjust durations.\n"
            
        if metrics['empty_subtitles'] > 0:
            report += "- Empty subtitles detected. Remove or fill with content.\n"
            
        if metrics['overlapping_subtitles'] > 0:
            report += "- Overlapping subtitles detected. Adjust timings to prevent overlap.\n"
            
        return report
