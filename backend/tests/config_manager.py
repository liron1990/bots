import pytest
import os
import sys
import json
import yaml
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Now import your modules
from common.config_yaml_manager import ConfigYamlManager
from common.config import Config  # Adjust path as needed
from common.messages import TemplateMerger  # Adjust path as needed


@pytest.fixture
def temp_config_file():
    """Create a temporary config JSON file"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config_data = {
            "database": {
                "host": "localhost",
                "port": 5432
            },
            "api": {
                "key": "test_key",
                "timeout": 30
            }
        }
        json.dump(config_data, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    try:
        os.unlink(temp_path)
    except OSError:
        pass


@pytest.fixture
def temp_yaml_file():
    """Create a temporary YAML file"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        yaml_data = {
            "templates": {
                "greeting": "Hello {name}!",
                "farewell": "Goodbye {name}!"
            },
            "messages": {
                "success": "Operation completed successfully",
                "error": "An error occurred"
            }
        }
        yaml.dump(yaml_data, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    try:
        os.unlink(temp_path)
    except OSError:
        pass


@pytest.fixture
def config_yaml_manager(temp_config_file, temp_yaml_file):
    """Create a ConfigYamlManager instance with temp files"""
    manager = ConfigYamlManager(temp_config_file, temp_yaml_file)
    yield manager


class TestConfigYamlManager:
    
    def test_initialization(self, config_yaml_manager):
        """Test that manager initializes correctly"""
        assert config_yaml_manager._config is not None
        assert config_yaml_manager._yaml is not None
        assert config_yaml_manager._config_mtime is not None
        assert config_yaml_manager._yaml_mtime is not None

    def test_get_config_returns_config_object(self, config_yaml_manager):
        """Test that get_config returns a Config object"""
        config = config_yaml_manager.get_config()
        assert isinstance(config, Config)

    def test_get_yaml_returns_template_merger(self, config_yaml_manager):
        """Test that get_yaml returns a TemplateMerger object"""
        yaml_merger = config_yaml_manager.get_yaml()
        assert isinstance(yaml_merger, TemplateMerger)

    def test_config_file_change_detection(self, temp_config_file, temp_yaml_file):
        """Test that config file changes are detected and reloaded"""
        manager = ConfigYamlManager(temp_config_file, temp_yaml_file)
        
        # Get initial config
        initial_config = manager.get_config()
        initial_mtime = manager._config_mtime
        
        # Wait a bit to ensure different mtime
        time.sleep(0.1)
        
        # Modify config file
        new_config_data = {
            "database": {
                "host": "newhost",
                "port": 3306
            },
            "api": {
                "key": "new_key",
                "timeout": 60
            }
        }
        
        with open(temp_config_file, 'w') as f:
            json.dump(new_config_data, f)
        
        # Get config again - should reload
        updated_config = manager.get_config()
        
        # Verify reload happened
        assert manager._config_mtime != initial_mtime
        assert updated_config is not initial_config
        
    # Add more tests as needed...


if __name__ == "__main__":
    pytest.main([__file__, "-v"])