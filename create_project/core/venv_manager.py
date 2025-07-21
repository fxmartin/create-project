# ABOUTME: Virtual environment management with multiple tool support
# ABOUTME: Handles venv creation with automatic tool detection and fallback

"""
Virtual environment manager for project generation.

This module provides the VenvManager class which handles virtual environment
creation using multiple tools (uv, virtualenv, venv) with automatic detection,
fallback mechanisms, and cross-platform compatibility.
"""

import subprocess
import shutil
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum
from structlog import get_logger

from .exceptions import VirtualEnvError, ProjectGenerationError


class VenvTool(Enum):
    """Supported virtual environment tools."""
    UV = "uv"
    VIRTUALENV = "virtualenv"  
    VENV = "venv"


class VenvManager:
    """Virtual environment manager with multiple tool support.
    
    This class handles virtual environment creation using multiple tools
    with the following priority order: uv > virtualenv > venv (standard library).
    It provides automatic tool detection, fallback mechanisms, and cross-platform
    compatibility.
    
    Attributes:
        logger: Structured logger for operations
        available_tools: Dictionary of available tools and their paths
        preferred_tool: Currently preferred tool for creation
    """
    
    # Tool priority order (first available will be preferred)
    TOOL_PRIORITY = [VenvTool.UV, VenvTool.VIRTUALENV, VenvTool.VENV]
    
    def __init__(self) -> None:
        """Initialize the VenvManager."""
        self.logger = get_logger(__name__)
        self.available_tools: Dict[VenvTool, Optional[str]] = {}
        self.preferred_tool: Optional[VenvTool] = None
        
        # Detect available tools
        self._detect_available_tools()
        self._select_preferred_tool()
        
        self.logger.info(
            "VenvManager initialized",
            available_tools=[tool.value for tool, path in self.available_tools.items() if path],
            preferred_tool=self.preferred_tool.value if self.preferred_tool else None
        )
    
    def create_venv(
        self,
        project_path: Path,
        venv_name: str = ".venv",
        python_version: Optional[str] = None,
        requirements_file: Optional[Path] = None
    ) -> Dict[str, Any]:
        """Create virtual environment in project directory.
        
        Args:
            project_path: Path to project directory
            venv_name: Name of virtual environment directory
            python_version: Specific Python version (e.g., "3.11")
            requirements_file: Optional requirements file to install
            
        Returns:
            Dictionary with creation result and environment information
            
        Raises:
            VirtualEnvError: If no tools are available or creation fails
        """
        if not self.preferred_tool:
            raise VirtualEnvError(
                "No virtual environment tools available",
                details={
                    "project_path": str(project_path),
                    "checked_tools": [tool.value for tool in VenvTool]
                }
            )
        
        if not project_path.exists():
            raise VirtualEnvError(
                f"Project directory does not exist: {project_path}",
                details={"project_path": str(project_path)}
            )
        
        venv_path = project_path / venv_name
        
        if venv_path.exists():
            raise VirtualEnvError(
                f"Virtual environment already exists: {venv_path}",
                details={
                    "project_path": str(project_path),
                    "venv_path": str(venv_path)
                }
            )
        
        self.logger.info(
            "Creating virtual environment",
            project_path=str(project_path),
            venv_name=venv_name,
            tool=self.preferred_tool.value,
            python_version=python_version
        )
        
        try:
            # Try creating with preferred tool first
            result = self._create_with_tool(
                self.preferred_tool,
                project_path,
                venv_name,
                python_version
            )
            
            if result["success"]:
                # Optionally install requirements
                if requirements_file and requirements_file.exists():
                    self._install_requirements(venv_path, requirements_file)
                
                self.logger.info(
                    "Virtual environment created successfully",
                    project_path=str(project_path),
                    venv_path=str(venv_path),
                    tool=self.preferred_tool.value
                )
                
                return result
            
            # Try fallback tools if preferred failed
            for tool in self.TOOL_PRIORITY:
                if tool == self.preferred_tool or tool not in self.available_tools:
                    continue
                
                if not self.available_tools[tool]:
                    continue
                
                self.logger.warning(
                    "Trying fallback tool for virtual environment creation",
                    fallback_tool=tool.value,
                    failed_tool=self.preferred_tool.value
                )
                
                try:
                    result = self._create_with_tool(
                        tool,
                        project_path,
                        venv_name,
                        python_version
                    )
                    
                    if result["success"]:
                        if requirements_file and requirements_file.exists():
                            self._install_requirements(venv_path, requirements_file)
                        
                        self.logger.info(
                            "Virtual environment created with fallback tool",
                            project_path=str(project_path),
                            venv_path=str(venv_path),
                            tool=tool.value
                        )
                        
                        return result
                
                except Exception as fallback_error:
                    self.logger.warning(
                        "Fallback tool also failed",
                        tool=tool.value,
                        error=str(fallback_error)
                    )
                    continue
            
            # All tools failed
            raise VirtualEnvError(
                "All virtual environment tools failed to create environment",
                details={
                    "project_path": str(project_path),
                    "venv_path": str(venv_path),
                    "tried_tools": [tool.value for tool in self.available_tools.keys()]
                }
            )
            
        except Exception as e:
            # Cleanup failed creation attempt
            if venv_path.exists():
                try:
                    shutil.rmtree(venv_path)
                    self.logger.debug("Cleaned up failed venv creation", venv_path=str(venv_path))
                except Exception as cleanup_error:
                    self.logger.warning(
                        "Failed to cleanup failed venv",
                        venv_path=str(venv_path),
                        error=str(cleanup_error)
                    )
            
            if isinstance(e, VirtualEnvError):
                raise
            
            raise VirtualEnvError(
                f"Failed to create virtual environment: {e}",
                details={
                    "project_path": str(project_path),
                    "venv_path": str(venv_path),
                    "tool": self.preferred_tool.value if self.preferred_tool else None
                },
                original_error=e
            ) from e
    
    def get_activation_instructions(
        self,
        project_path: Path,
        venv_name: str = ".venv"
    ) -> Dict[str, str]:
        """Get platform-specific activation instructions.
        
        Args:
            project_path: Path to project directory
            venv_name: Name of virtual environment directory
            
        Returns:
            Dictionary with activation instructions for different platforms
        """
        venv_path = project_path / venv_name
        
        if not venv_path.exists():
            return {
                "error": f"Virtual environment not found: {venv_path}"
            }
        
        # Determine activation script paths
        if sys.platform == "win32":
            activate_script = venv_path / "Scripts" / "activate.bat"
            activate_ps1 = venv_path / "Scripts" / "Activate.ps1"
            
            return {
                "windows_cmd": f"{activate_script}",
                "windows_powershell": f"& '{activate_ps1}'",
                "deactivate": "deactivate"
            }
        else:
            activate_script = venv_path / "bin" / "activate"
            
            return {
                "bash_zsh": f"source {activate_script}",
                "fish": f"source {activate_script}.fish",
                "csh": f"source {activate_script}.csh",
                "deactivate": "deactivate"
            }
    
    def _detect_available_tools(self) -> None:
        """Detect which virtual environment tools are available."""
        # Check uv
        uv_path = shutil.which('uv')
        if uv_path:
            try:
                result = subprocess.run(
                    [uv_path, '--version'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    self.available_tools[VenvTool.UV] = uv_path
                    self.logger.debug(
                        "uv detected",
                        path=uv_path,
                        version=result.stdout.strip()
                    )
            except (subprocess.TimeoutExpired, Exception) as e:
                self.logger.debug("uv detection failed", error=str(e))
        
        # Check virtualenv
        virtualenv_path = shutil.which('virtualenv')
        if virtualenv_path:
            try:
                result = subprocess.run(
                    [virtualenv_path, '--version'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    self.available_tools[VenvTool.VIRTUALENV] = virtualenv_path
                    self.logger.debug(
                        "virtualenv detected",
                        path=virtualenv_path,
                        version=result.stdout.strip()
                    )
            except (subprocess.TimeoutExpired, Exception) as e:
                self.logger.debug("virtualenv detection failed", error=str(e))
        
        # Check venv (standard library)
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'venv', '--help'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                self.available_tools[VenvTool.VENV] = sys.executable
                self.logger.debug(
                    "venv detected",
                    python_executable=sys.executable
                )
        except (subprocess.TimeoutExpired, Exception) as e:
            self.logger.debug("venv detection failed", error=str(e))
    
    def _select_preferred_tool(self) -> None:
        """Select preferred tool based on priority and availability."""
        for tool in self.TOOL_PRIORITY:
            if tool in self.available_tools and self.available_tools[tool]:
                self.preferred_tool = tool
                self.logger.debug("Selected preferred tool", tool=tool.value)
                return
        
        self.logger.warning("No virtual environment tools available")
    
    def _create_with_tool(
        self,
        tool: VenvTool,
        project_path: Path,
        venv_name: str,
        python_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create virtual environment with specific tool.
        
        Args:
            tool: Tool to use for creation
            project_path: Project directory path
            venv_name: Virtual environment directory name
            python_version: Optional Python version
            
        Returns:
            Dictionary with creation result
        """
        venv_path = project_path / venv_name
        tool_path = self.available_tools.get(tool)
        
        if not tool_path:
            return {
                "success": False,
                "error": f"Tool {tool.value} not available",
                "tool": tool.value
            }
        
        try:
            if tool == VenvTool.UV:
                return self._create_with_uv(tool_path, venv_path, python_version)
            elif tool == VenvTool.VIRTUALENV:
                return self._create_with_virtualenv(tool_path, venv_path, python_version)
            elif tool == VenvTool.VENV:
                return self._create_with_venv(tool_path, venv_path, python_version)
            else:
                return {
                    "success": False,
                    "error": f"Unsupported tool: {tool.value}",
                    "tool": tool.value
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "tool": tool.value
            }
    
    def _create_with_uv(
        self,
        uv_path: str,
        venv_path: Path,
        python_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create virtual environment with uv."""
        command = [uv_path, 'venv', str(venv_path)]
        
        if python_version:
            command.extend(['--python', python_version])
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=venv_path.parent
        )
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": f"uv venv failed: {result.stderr}",
                "tool": VenvTool.UV.value,
                "command": ' '.join(command)
            }
        
        return {
            "success": True,
            "venv_path": str(venv_path),
            "tool": VenvTool.UV.value,
            "python_version": python_version,
            "activation_instructions": self.get_activation_instructions(venv_path.parent, venv_path.name)
        }
    
    def _create_with_virtualenv(
        self,
        virtualenv_path: str,
        venv_path: Path,
        python_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create virtual environment with virtualenv."""
        command = [virtualenv_path, str(venv_path)]
        
        if python_version:
            command.extend(['--python', f'python{python_version}'])
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=venv_path.parent
        )
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": f"virtualenv failed: {result.stderr}",
                "tool": VenvTool.VIRTUALENV.value,
                "command": ' '.join(command)
            }
        
        return {
            "success": True,
            "venv_path": str(venv_path),
            "tool": VenvTool.VIRTUALENV.value,
            "python_version": python_version,
            "activation_instructions": self.get_activation_instructions(venv_path.parent, venv_path.name)
        }
    
    def _create_with_venv(
        self,
        python_path: str,
        venv_path: Path,
        python_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create virtual environment with venv (standard library)."""
        # For venv, we use the current Python executable
        # Python version selection would require finding different Python installations
        command = [python_path, '-m', 'venv', str(venv_path)]
        
        if python_version:
            # Try to find specific Python version
            python_exe = shutil.which(f'python{python_version}')
            if python_exe:
                command = [python_exe, '-m', 'venv', str(venv_path)]
            else:
                self.logger.warning(
                    "Specific Python version not found, using current Python",
                    requested_version=python_version,
                    current_python=python_path
                )
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=venv_path.parent
        )
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": f"venv failed: {result.stderr}",
                "tool": VenvTool.VENV.value,
                "command": ' '.join(command)
            }
        
        return {
            "success": True,
            "venv_path": str(venv_path),
            "tool": VenvTool.VENV.value,
            "python_version": python_version,
            "activation_instructions": self.get_activation_instructions(venv_path.parent, venv_path.name)
        }
    
    def _install_requirements(
        self,
        venv_path: Path,
        requirements_file: Path
    ) -> None:
        """Install requirements in virtual environment.
        
        Args:
            venv_path: Path to virtual environment
            requirements_file: Path to requirements file
        """
        try:
            # Determine pip executable path
            if sys.platform == "win32":
                pip_path = venv_path / "Scripts" / "pip.exe"
            else:
                pip_path = venv_path / "bin" / "pip"
            
            if not pip_path.exists():
                self.logger.warning(
                    "pip not found in virtual environment",
                    venv_path=str(venv_path),
                    expected_pip_path=str(pip_path)
                )
                return
            
            self.logger.info(
                "Installing requirements",
                requirements_file=str(requirements_file),
                venv_path=str(venv_path)
            )
            
            result = subprocess.run(
                [str(pip_path), 'install', '-r', str(requirements_file)],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes for installations
            )
            
            if result.returncode != 0:
                self.logger.error(
                    "Requirements installation failed",
                    requirements_file=str(requirements_file),
                    stderr=result.stderr
                )
            else:
                self.logger.info(
                    "Requirements installed successfully",
                    requirements_file=str(requirements_file)
                )
        
        except Exception as e:
            self.logger.error(
                "Failed to install requirements",
                requirements_file=str(requirements_file),
                error=str(e)
            )