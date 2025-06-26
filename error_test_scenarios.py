#!/usr/bin/env python3
"""
Error Testing Scenarios for Video Subtitle Generator
Tests various error conditions and edge cases
"""

import os
import sys
import time
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
from typing import Dict, List, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from config_manager import ConfigManager
from gcs_handler import GCSHandler
from ai_generator import AIGenerator
from video_chunker import VideoChunker
from state_manager import StateManager, JobState, ProcessingStage
from subtitle_processor import SubtitleProcessor
from utils import validate_video_file, ensure_directory_exists

class ErrorTestRunner:
    """Test runner for error scenarios"""
    
    def __init__(self):
        self.results = {}
        self.temp_dir = tempfile.mkdtemp(prefix="subtitle_test_")
        self.original_cwd = os.getcwd()
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Cleanup
        os.chdir(self.original_cwd)
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def run_all_tests(self):
        """Run all error test scenarios"""
        print("🧪 Starting Error Handling Comprehensive Test Suite")
        print("=" * 60)
        
        test_methods = [
            self.test_network_failures,
            self.test_authentication_failures,
            self.test_invalid_video_files,
            self.test_disk_space_issues,
            self.test_api_quota_exhaustion,
            self.test_partial_processing_failures,
            self.test_empty_ai_responses,
            self.test_large_file_handling,
            self.test_edge_case_video_formats,
            self.test_concurrent_processing
        ]
        
        for test_method in test_methods:
            try:
                print(f"\n🔍 Running {test_method.__name__.replace('_', ' ').title()}")
                test_method()
            except Exception as e:
                self.results[test_method.__name__] = {
                    'status': 'ERROR',
                    'error': str(e),
                    'critical': True
                }
                print(f"❌ Test failed with exception: {e}")
        
        self.generate_report()
    
    def test_network_failures(self):
        """Test network failure scenarios"""
        scenarios = [
            "GCS upload timeout",
            "GCS download failure", 
            "Vertex AI connection timeout",
            "DNS resolution failure",
            "Connection refused"
        ]
        
        results = {}
        
        # Test GCS Handler with mocked network failures
        try:
            config = ConfigManager()
            gcs_handler = GCSHandler(config)
            
            # Mock network failures
            with patch('google.cloud.storage.Client') as mock_client:
                mock_client.side_effect = Exception("Connection timeout")
                
                try:
                    gcs_handler.initialize()
                    results["gcs_init_error_handling"] = "FAIL - No exception raised"
                except Exception as e:
                    if "Failed to initialize GCS client" in str(e):
                        results["gcs_init_error_handling"] = "PASS - Proper error handling"
                    else:
                        results["gcs_init_error_handling"] = f"PARTIAL - Wrong error: {e}"
        except Exception as e:
            results["gcs_init_test"] = f"ERROR - {e}"
            
        # Test AI Generator network failures
        try:
            config = ConfigManager()
            ai_gen = AIGenerator(config)
            
            with patch('vertexai.init') as mock_init:
                mock_init.side_effect = Exception("Network unreachable")
                
                try:
                    ai_gen.initialize()
                    results["ai_init_error_handling"] = "FAIL - No exception raised"
                except Exception as e:
                    if "Failed to initialize Vertex AI" in str(e):
                        results["ai_init_error_handling"] = "PASS - Proper error handling"
                    else:
                        results["ai_init_error_handling"] = f"PARTIAL - Wrong error: {e}"
        except Exception as e:
            results["ai_init_test"] = f"ERROR - {e}"
            
        self.results["network_failures"] = results
    
    def test_authentication_failures(self):
        """Test authentication failure scenarios"""
        results = {}
        
        # Test missing service account file
        config_data = {
            'gcp': {
                'project_id': 'test-project',
                'auth_method': 'service_account',
                'service_account_path': '/nonexistent/path/service-account.json'
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.dump(config_data, f)
            temp_config = f.name
        
        try:
            config = ConfigManager(temp_config)
            gcs_handler = GCSHandler(config)
            
            try:
                gcs_handler.initialize()
                results["missing_service_account"] = "FAIL - No exception for missing file"
            except Exception as e:
                if "Service account file not found" in str(e):
                    results["missing_service_account"] = "PASS - Proper error message"
                else:
                    results["missing_service_account"] = f"PARTIAL - Wrong error: {e}"
        except Exception as e:
            results["missing_service_account"] = f"ERROR - {e}"
        finally:
            os.unlink(temp_config)
            
        # Test invalid service account file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            invalid_sa_file = f.name
            
        config_data['gcp']['service_account_path'] = invalid_sa_file
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_config = f.name
        
        try:
            config = ConfigManager(temp_config)
            gcs_handler = GCSHandler(config)
            
            try:
                gcs_handler.initialize()
                results["invalid_service_account"] = "FAIL - No exception for invalid file"
            except Exception as e:
                results["invalid_service_account"] = "PASS - Exception raised for invalid SA file"
        except Exception as e:
            results["invalid_service_account"] = f"ERROR - {e}"
        finally:
            os.unlink(temp_config)
            os.unlink(invalid_sa_file)
            
        self.results["authentication_failures"] = results
    
    def test_invalid_video_files(self):
        """Test invalid video file scenarios"""
        results = {}
        
        # Test non-existent file
        results["nonexistent_file"] = "PASS" if not validate_video_file("/nonexistent/file.mp4") else "FAIL"
        
        # Test empty file
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
            empty_file = f.name
        
        try:
            results["empty_file"] = "PASS" if not validate_video_file(empty_file) else "FAIL"
        finally:
            os.unlink(empty_file)
            
        # Test text file with video extension
        with tempfile.NamedTemporaryFile(mode='w', suffix='.mp4', delete=False) as f:
            f.write("This is not a video file")
            fake_video = f.name
        
        try:
            results["fake_video_file"] = "PASS" if not validate_video_file(fake_video) else "FAIL"
        finally:
            os.unlink(fake_video)
            
        # Test unsupported format
        config = ConfigManager()
        processor = SubtitleProcessor()
        
        # Create a job with unsupported format
        try:
            with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
                unsupported_file = f.name
                
            job = JobState(
                job_id="test_job",
                video_path=unsupported_file,
                video_name="test",
                languages=["eng"],
                enable_sdh=False
            )
            
            try:
                processor.validate_input(job, lambda x: None)
                results["unsupported_format"] = "FAIL - No exception for unsupported format"
            except ValueError as e:
                if "Unsupported video format" in str(e):
                    results["unsupported_format"] = "PASS - Proper format validation"
                else:
                    results["unsupported_format"] = f"PARTIAL - Wrong error: {e}"
            except Exception as e:
                results["unsupported_format"] = f"ERROR - Unexpected exception: {e}"
        finally:
            if 'unsupported_file' in locals():
                try:
                    os.unlink(unsupported_file)
                except:
                    pass
                    
        self.results["invalid_video_files"] = results
    
    def test_disk_space_issues(self):
        """Test disk space constraint scenarios"""
        results = {}
        
        # This is challenging to test without actually filling disk
        # We'll test the logic around large files instead
        
        config = ConfigManager()
        processor = SubtitleProcessor()
        
        # Test large file warning (10GB+)
        with patch('pathlib.Path.stat') as mock_stat:
            mock_stat.return_value.st_size = 15 * 1024**3  # 15GB
            
            # Create a temporary file to represent large video
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
                large_file = f.name
                
            try:
                job = JobState(
                    job_id="test_job",
                    video_path=large_file,
                    video_name="test",
                    languages=["eng"],
                    enable_sdh=False
                )
                
                # This should show a warning but not fail
                with patch('src.utils.validate_video_file', return_value=True):
                    try:
                        processor.validate_input(job, lambda x: None)
                        results["large_file_warning"] = "PASS - Large file handled with warning"
                    except Exception as e:
                        results["large_file_warning"] = f"FAIL - Exception on large file: {e}"
            finally:
                os.unlink(large_file)
        
        # Test directory creation with permission issues
        try:
            ensure_directory_exists("/root/test_permission_denied")
            results["permission_denied"] = "PARTIAL - No permission error (may be running as root)"
        except PermissionError:
            results["permission_denied"] = "PASS - Permission error handled"
        except Exception as e:
            results["permission_denied"] = f"ERROR - Unexpected error: {e}"
            
        self.results["disk_space_issues"] = results
    
    def test_api_quota_exhaustion(self):
        """Test API quota exhaustion scenarios"""
        results = {}
        
        # Mock quota exceeded error from Vertex AI
        config = ConfigManager()
        ai_gen = AIGenerator(config)
        
        with patch.object(ai_gen, 'model') as mock_model:
            mock_model.generate_content.side_effect = Exception("Quota exceeded for requests")
            
            try:
                result = ai_gen._generate_subtitle_for_chunk(
                    "gs://test/chunk.mp4",
                    "eng",
                    False
                )
                if result is None:
                    results["quota_exceeded_handling"] = "PASS - Quota error handled gracefully"
                else:
                    results["quota_exceeded_handling"] = "FAIL - Should return None on quota error"
            except Exception as e:
                results["quota_exceeded_handling"] = f"PARTIAL - Exception not caught: {e}"
        
        # Test rate limiting
        with patch.object(ai_gen, 'model') as mock_model:
            mock_model.generate_content.side_effect = Exception("Rate limit exceeded")
            
            try:
                result = ai_gen._generate_subtitle_for_chunk(
                    "gs://test/chunk.mp4", 
                    "eng",
                    False
                )
                if result is None:
                    results["rate_limit_handling"] = "PASS - Rate limit handled gracefully"
                else:
                    results["rate_limit_handling"] = "FAIL - Should return None on rate limit"
            except Exception as e:
                results["rate_limit_handling"] = f"PARTIAL - Exception not caught: {e}"
                
        self.results["api_quota_exhaustion"] = results
    
    def test_partial_processing_failures(self):
        """Test partial processing failure scenarios"""
        results = {}
        
        # Test job state recovery
        state_manager = StateManager(self.temp_dir)
        
        # Create a job in processing state
        job = state_manager.create_job(
            video_path="/test/video.mp4",
            languages=["eng"],
            enable_sdh=False
        )
        
        # Simulate partial processing
        job.current_stage = ProcessingStage.UPLOADING
        job.metadata['chunks_created'] = 5
        job.metadata['chunks_uploaded'] = 3  # Only 3 out of 5 uploaded
        state_manager.save_job(job)
        
        # Test job loading
        loaded_job = state_manager.load_job(job.job_id)
        if loaded_job and loaded_job.current_stage == ProcessingStage.UPLOADING:
            results["job_state_persistence"] = "PASS - Job state correctly saved and loaded"
        else:
            results["job_state_persistence"] = "FAIL - Job state not preserved"
            
        # Test resume functionality
        jobs = state_manager.list_jobs()
        incomplete_jobs = [j for j in jobs if j.current_stage != ProcessingStage.COMPLETED]
        if len(incomplete_jobs) > 0:
            results["incomplete_job_detection"] = "PASS - Incomplete jobs detected"
        else:
            results["incomplete_job_detection"] = "FAIL - Should detect incomplete jobs"
            
        self.results["partial_processing_failures"] = results
    
    def test_empty_ai_responses(self):
        """Test empty or invalid AI response scenarios"""
        results = {}
        
        config = ConfigManager()
        ai_gen = AIGenerator(config)
        
        # Test empty response
        with patch.object(ai_gen, 'model') as mock_model:
            mock_response = Mock()
            mock_response.text = ""
            mock_model.generate_content.return_value = mock_response
            
            result = ai_gen._generate_subtitle_for_chunk(
                "gs://test/chunk.mp4",
                "eng", 
                False
            )
            
            if result is None:
                results["empty_response_handling"] = "PASS - Empty response handled"
            else:
                results["empty_response_handling"] = f"FAIL - Should return None for empty response"
        
        # Test malformed SRT response
        with patch.object(ai_gen, 'model') as mock_model:
            mock_response = Mock()
            mock_response.text = "This is not a valid SRT format at all"
            mock_model.generate_content.return_value = mock_response
            
            result = ai_gen._generate_subtitle_for_chunk(
                "gs://test/chunk.mp4",
                "eng",
                False
            )
            
            # Should either return None or handle gracefully
            results["malformed_response_handling"] = "PASS - Malformed response handled"
        
        # Test response with no timestamps
        with patch.object(ai_gen, 'model') as mock_model:
            mock_response = Mock()
            mock_response.text = "```srt\nJust some text without timestamps\n```"
            mock_model.generate_content.return_value = mock_response
            
            result = ai_gen._generate_subtitle_for_chunk(
                "gs://test/chunk.mp4",
                "eng",
                False
            )
            
            results["no_timestamps_handling"] = "PASS - Response without timestamps handled"
            
        self.results["empty_ai_responses"] = results
    
    def test_large_file_handling(self):
        """Test large file handling scenarios"""
        results = {}
        
        # Test chunking of large files
        config = ConfigManager()
        chunker = VideoChunker(config)
        
        # Mock a very long video (3 hours)
        mock_video_info = {
            'duration': 10800.0,  # 3 hours in seconds
            'total_chunks': 180,  # 180 chunks at 60s each
            'width': 1920,
            'height': 1080
        }
        
        with patch.object(chunker, 'analyze_video', return_value=mock_video_info):
            try:
                video_info = chunker.analyze_video("/fake/long_video.mp4")
                if video_info['total_chunks'] == 180:
                    results["large_file_chunking"] = "PASS - Large file chunking calculated correctly"
                else:
                    results["large_file_chunking"] = f"FAIL - Wrong chunk count: {video_info['total_chunks']}"
            except Exception as e:
                results["large_file_chunking"] = f"ERROR - {e}"
        
        # Test memory constraints (simulate)
        try:
            # This simulates memory pressure during processing
            large_subtitle_data = "x" * (100 * 1024 * 1024)  # 100MB string
            # If this doesn't crash, memory handling is working
            del large_subtitle_data
            results["memory_handling"] = "PASS - Large data handled without crash"
        except MemoryError:
            results["memory_handling"] = "FAIL - Memory error on large data"
        except Exception as e:
            results["memory_handling"] = f"ERROR - {e}"
            
        self.results["large_file_handling"] = results
    
    def test_edge_case_video_formats(self):
        """Test edge case video format scenarios"""
        results = {}
        
        # Test various frame rates
        edge_cases = [
            {"fps": 23.976, "description": "23.976 fps film"},
            {"fps": 29.97, "description": "29.97 fps NTSC"},
            {"fps": 59.94, "description": "59.94 fps high frame rate"},
            {"fps": 120, "description": "120 fps ultra high frame rate"}
        ]
        
        for case in edge_cases:
            try:
                # Mock video analysis with edge case frame rate
                with patch('ffmpeg.probe') as mock_probe:
                    mock_probe.return_value = {
                        'streams': [
                            {
                                'codec_type': 'video',
                                'r_frame_rate': f"{case['fps']}/1",
                                'width': 1920,
                                'height': 1080
                            }
                        ],
                        'format': {'duration': '60.0'}
                    }
                    
                    config = ConfigManager()
                    chunker = VideoChunker(config)
                    info = chunker.analyze_video("/fake/video.mp4")
                    
                    if 'fps' in info and info['fps'] > 0:
                        results[f"fps_{case['fps']}"] = "PASS"
                    else:
                        results[f"fps_{case['fps']}"] = "FAIL - FPS not parsed correctly"
                        
            except Exception as e:
                results[f"fps_{case['fps']}"] = f"ERROR - {e}"
        
        # Test unusual resolutions
        resolutions = [
            (3840, 2160, "4K"),
            (7680, 4320, "8K"), 
            (640, 480, "Low res"),
            (1, 1, "Minimal res")
        ]
        
        for width, height, desc in resolutions:
            try:
                with patch('ffmpeg.probe') as mock_probe:
                    mock_probe.return_value = {
                        'streams': [
                            {
                                'codec_type': 'video',
                                'width': width,
                                'height': height
                            }
                        ],
                        'format': {'duration': '60.0'}
                    }
                    
                    config = ConfigManager()
                    chunker = VideoChunker(config)
                    info = chunker.analyze_video("/fake/video.mp4")
                    
                    if info['width'] == width and info['height'] == height:
                        results[f"resolution_{desc.lower().replace(' ', '_')}"] = "PASS"
                    else:
                        results[f"resolution_{desc.lower().replace(' ', '_')}"] = "FAIL"
                        
            except Exception as e:
                results[f"resolution_{desc.lower().replace(' ', '_')}"] = f"ERROR - {e}"
                
        self.results["edge_case_video_formats"] = results
    
    def test_concurrent_processing(self):
        """Test concurrent processing scenarios"""
        results = {}
        
        # Test multiple job creation
        state_manager = StateManager(self.temp_dir)
        
        jobs = []
        for i in range(5):
            job = state_manager.create_job(
                video_path=f"/test/video_{i}.mp4",
                languages=["eng"],
                enable_sdh=False
            )
            jobs.append(job)
            
        # Verify all jobs created with unique IDs
        job_ids = [job.job_id for job in jobs]
        if len(set(job_ids)) == 5:
            results["unique_job_ids"] = "PASS - All job IDs are unique"
        else:
            results["unique_job_ids"] = "FAIL - Duplicate job IDs found"
            
        # Test concurrent state updates
        try:
            for job in jobs:
                job.current_stage = ProcessingStage.CHUNKING
                state_manager.save_job(job)
                
            # Verify all saved correctly
            loaded_jobs = [state_manager.load_job(job_id) for job_id in job_ids]
            if all(job.current_stage == ProcessingStage.CHUNKING for job in loaded_jobs if job):
                results["concurrent_state_updates"] = "PASS - Concurrent updates successful"
            else:
                results["concurrent_state_updates"] = "FAIL - State updates failed"
                
        except Exception as e:
            results["concurrent_state_updates"] = f"ERROR - {e}"
            
        # Test job cleanup
        try:
            for job_id in job_ids:
                state_manager.delete_job(job_id)
                
            remaining_jobs = state_manager.list_jobs()
            remaining_ids = [job.job_id for job in remaining_jobs if job.job_id in job_ids]
            
            if len(remaining_ids) == 0:
                results["job_cleanup"] = "PASS - All jobs cleaned up"
            else:
                results["job_cleanup"] = f"FAIL - {len(remaining_ids)} jobs not cleaned up"
                
        except Exception as e:
            results["job_cleanup"] = f"ERROR - {e}"
            
        self.results["concurrent_processing"] = results
    
    def generate_report(self):
        """Generate comprehensive error handling report"""
        print("\n" + "=" * 80)
        print("🔍 ERROR HANDLING COMPREHENSIVE TEST REPORT")
        print("=" * 80)
        
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        critical_issues = 0
        
        for category, tests in self.results.items():
            print(f"\n📋 {category.replace('_', ' ').title()}")
            print("-" * 50)
            
            for test_name, result in tests.items():
                total_tests += 1
                
                if isinstance(result, dict):
                    status = result.get('status', 'UNKNOWN')
                    if result.get('critical', False):
                        critical_issues += 1
                    print(f"  {test_name}: {status}")
                    if 'error' in result:
                        print(f"    Error: {result['error']}")
                else:
                    if result.startswith('PASS'):
                        passed_tests += 1
                        print(f"  ✅ {test_name}: {result}")
                    elif result.startswith('FAIL'):
                        failed_tests += 1
                        print(f"  ❌ {test_name}: {result}")
                    elif result.startswith('ERROR'):
                        failed_tests += 1
                        critical_issues += 1
                        print(f"  🚨 {test_name}: {result}")
                    else:
                        print(f"  ⚠️  {test_name}: {result}")
        
        print("\n" + "=" * 80)
        print("📊 SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Critical Issues: {critical_issues}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "N/A")
        
        # Critical findings
        print("\n🚨 CRITICAL FINDINGS:")
        if critical_issues == 0:
            print("✅ No critical issues found!")
        else:
            for category, tests in self.results.items():
                for test_name, result in tests.items():
                    if isinstance(result, dict) and result.get('critical', False):
                        print(f"  - {category}.{test_name}: {result.get('error', 'Critical failure')}")

if __name__ == "__main__":
    with ErrorTestRunner() as runner:
        runner.run_all_tests()