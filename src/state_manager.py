"""
State Manager
Handles job state persistence and recovery
"""

import os
import json
import time
import uuid
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any

class ProcessingStage(Enum):
    """Processing pipeline stages"""
    CREATED = 0
    VALIDATING = 1
    ANALYZING = 2
    CHUNKING = 3
    CONNECTING = 4
    UPLOADING = 5
    INITIALIZING = 6
    GENERATING = 7
    DOWNLOADING = 8
    MERGING = 9
    FINALIZING = 10
    COMPLETED = 11
    FAILED = -1

@dataclass
class JobState:
    """Job state representation"""
    job_id: str
    video_path: str
    video_name: str
    languages: List[str]
    enable_sdh: bool
    current_stage: ProcessingStage = ProcessingStage.CREATED
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    output_dir: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['current_stage'] = self.current_stage.value
        return data
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JobState':
        """Create from dictionary"""
        data['current_stage'] = ProcessingStage(data.get('current_stage', 0))
        return cls(**data)

class StateManager:
    """Manages job state persistence"""
    
    def __init__(self, state_dir: str = "jobs"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
    def create_job(self, video_path: str, languages: List[str], enable_sdh: bool) -> JobState:
        """Create a new job"""
        job_id = f"job_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        video_name = Path(video_path).stem
        
        job = JobState(
            job_id=job_id,
            video_path=video_path,
            video_name=video_name,
            languages=languages,
            enable_sdh=enable_sdh
        )
        
        self.save_job(job)
        return job
        
    def save_job(self, job: JobState) -> None:
        """Save job state to disk"""
        job.updated_at = time.time()
        job_file = self.state_dir / f"{job.job_id}.json"
        
        # Create backup of existing file
        if job_file.exists():
            backup_file = self.state_dir / f"{job.job_id}.json.bak"
            try:
                job_file.rename(backup_file)
            except:
                pass
        
        try:
            with open(job_file, 'w', encoding='utf-8') as f:
                json.dump(job.to_dict(), f, indent=2, ensure_ascii=False)
                
            # Remove backup if save successful
            backup_file = self.state_dir / f"{job.job_id}.json.bak"
            if backup_file.exists():
                backup_file.unlink()
                
        except Exception as e:
            # Restore backup if save failed
            backup_file = self.state_dir / f"{job.job_id}.json.bak"
            if backup_file.exists():
                backup_file.rename(job_file)
            raise e
            
    def load_job(self, job_id: str) -> Optional[JobState]:
        """Load job from disk"""
        job_file = self.state_dir / f"{job_id}.json"
        
        if not job_file.exists():
            # Try partial match
            matching_files = list(self.state_dir.glob(f"*{job_id}*.json"))
            if matching_files:
                job_file = matching_files[0]
            else:
                return None
                
        try:
            with open(job_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            return JobState.from_dict(data)
        except Exception as e:
            print(f"Error loading job {job_id}: {e}")
            return None
            
    def list_jobs(self) -> List[JobState]:
        """List all jobs"""
        jobs = []
        
        for job_file in self.state_dir.glob("job_*.json"):
            if job_file.name.endswith('.bak'):
                continue
                
            try:
                with open(job_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                jobs.append(JobState.from_dict(data))
            except:
                continue
                
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)
        
    def delete_job(self, job_id: str) -> bool:
        """Delete a job and its files"""
        job_file = self.state_dir / f"{job_id}.json"
        
        if job_file.exists():
            try:
                job_file.unlink()
                
                # Also remove backup if exists
                backup_file = self.state_dir / f"{job_id}.json.bak"
                if backup_file.exists():
                    backup_file.unlink()
                    
                return True
            except:
                pass
                
        return False
        
    def get_job_by_video(self, video_path: str) -> Optional[JobState]:
        """Find job by video path"""
        video_path = str(Path(video_path).resolve())
        
        for job in self.list_jobs():
            if job.video_path == video_path:
                return job
                
        return None
        
    def cleanup_old_jobs(self, days: int = 30) -> int:
        """Remove jobs older than specified days"""
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        removed = 0
        
        for job in self.list_jobs():
            if job.created_at < cutoff_time:
                if self.delete_job(job.job_id):
                    removed += 1
                    
        return removed
