"""
Web Automation Service using Playwright
"""

import asyncio
import logging
import json
import uuid
import time
from typing import Dict, Any, Optional, List
from pathlib import Path
import re
from urllib.parse import urlparse

from models.chat_models import ComponentStatus, ServiceStatus
from utils.config import Config

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

class WebAutomationService:
    """Service for web automation using Playwright"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.playwright = None
        self.browsers: Dict[str, Browser] = {}
        self.contexts: Dict[str, BrowserContext] = {}
        self.pages: Dict[str, Page] = {}
        self.active_sessions: Dict[str, Dict] = {}
        
    async def start(self):
        """Start the web automation service"""
        try:
            if not PLAYWRIGHT_AVAILABLE:
                self.logger.warning("Playwright not available - installing...")
                await self._install_playwright()
            
            # Initialize Playwright
            self.playwright = await async_playwright().start()
            
            self.logger.info("Web Automation Service started")
            
        except Exception as e:
            self.logger.error(f"Failed to start web automation service: {e}")
            raise
    
    async def stop(self):
        """Stop the web automation service"""
        try:
            # Close all pages, contexts, and browsers
            for page in self.pages.values():
                await page.close()
            
            for context in self.contexts.values():
                await context.close()
            
            for browser in self.browsers.values():
                await browser.close()
            
            if self.playwright:
                await self.playwright.stop()
            
            self.logger.info("Web Automation Service stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping web automation service: {e}")
    
    async def get_status(self) -> ComponentStatus:
        """Get service status"""
        try:
            if PLAYWRIGHT_AVAILABLE and self.playwright:
                return ComponentStatus(
                    name="web_automation_service",
                    status=ServiceStatus.HEALTHY,
                    version="1.0.0",
                    details={
                        "playwright_available": True,
                        "active_browsers": len(self.browsers),
                        "active_contexts": len(self.contexts),
                        "active_pages": len(self.pages),
                        "active_sessions": len(self.active_sessions)
                    }
                )
            else:
                return ComponentStatus(
                    name="web_automation_service",
                    status=ServiceStatus.DEGRADED,
                    error="Playwright not available"
                )
                
        except Exception as e:
            return ComponentStatus(
                name="web_automation_service",
                status=ServiceStatus.OFFLINE,
                error=str(e)
            )
    
    async def execute_web_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a web automation task"""
        try:
            # Security check
            if not await self._security_check(task):
                return {
                    'success': False,
                    'error': 'Security check failed - task not permitted'
                }
            
            task_type = task.get('type')
            
            if task_type == 'create_session':
                return await self._handle_create_session(task)
            elif task_type == 'navigate':
                return await self._handle_navigate(task)
            elif task_type == 'click':
                return await self._handle_click(task)
            elif task_type == 'fill':
                return await self._handle_fill(task)
            elif task_type == 'type':
                return await self._handle_type(task)
            elif task_type == 'screenshot':
                return await self._handle_screenshot(task)
            elif task_type == 'extract_text':
                return await self._handle_extract_text(task)
            elif task_type == 'extract_links':
                return await self._handle_extract_links(task)
            elif task_type == 'wait_for_element':
                return await self._handle_wait_for_element(task)
            elif task_type == 'scroll':
                return await self._handle_scroll(task)
            elif task_type == 'get_page_info':
                return await self._handle_get_page_info(task)
            elif task_type == 'download_file':
                return await self._handle_download_file(task)
            elif task_type == 'upload_file':
                return await self._handle_upload_file(task)
            elif task_type == 'execute_script':
                return await self._handle_execute_script(task)
            elif task_type == 'close_session':
                return await self._handle_close_session(task)
            else:
                return {
                    'success': False,
                    'error': f'Unknown task type: {task_type}'
                }
                
        except Exception as e:
            self.logger.error(f"Error executing web task: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _security_check(self, task: Dict[str, Any]) -> bool:
        """Perform security check on web automation task"""
        try:
            # Check URL whitelist for navigation tasks
            if task.get('type') == 'navigate':
                url = task.get('url', '')
                if not self._is_url_allowed(url):
                    self.logger.warning(f"URL not allowed: {url}")
                    return False
            
            # Check for suspicious script execution
            if task.get('type') == 'execute_script':
                script = task.get('script', '')
                if self._contains_suspicious_script(script):
                    self.logger.warning(f"Suspicious script detected: {script}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Security check error: {e}")
            return False
    
    def _is_url_allowed(self, url: str) -> bool:
        """Check if URL is allowed"""
        try:
            parsed = urlparse(url)
            
            # Block dangerous protocols
            dangerous_protocols = ['file', 'ftp', 'javascript']
            if parsed.scheme in dangerous_protocols:
                return False
            
            # Block local/private IPs (basic check)
            if parsed.hostname:
                if parsed.hostname in ['localhost', '127.0.0.1', '0.0.0.0']:
                    return False
                
                # Block private IP ranges (simplified)
                if parsed.hostname.startswith(('192.168.', '10.', '172.')):
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _contains_suspicious_script(self, script: str) -> bool:
        """Check if script contains suspicious content"""
        suspicious_patterns = [
            r'document\.cookie',
            r'localStorage',
            r'sessionStorage',
            r'eval\s*\(',
            r'Function\s*\(',
            r'window\.location',
            r'XMLHttpRequest',
            r'fetch\s*\('
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, script, re.IGNORECASE):
                return True
        
        return False
    
    async def _handle_create_session(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new browser session"""
        try:
            session_id = task.get('session_id', str(uuid.uuid4()))
            browser_type = task.get('browser', 'chromium')
            headless = task.get('headless', True)
            
            # Launch browser
            if browser_type == 'chromium':
                browser = await self.playwright.chromium.launch(headless=headless)
            elif browser_type == 'firefox':
                browser = await self.playwright.firefox.launch(headless=headless)
            elif browser_type == 'webkit':
                browser = await self.playwright.webkit.launch(headless=headless)
            else:
                return {'success': False, 'error': f'Unsupported browser: {browser_type}'}
            
            # Create context
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            
            # Create page
            page = await context.new_page()
            
            # Store references
            self.browsers[session_id] = browser
            self.contexts[session_id] = context
            self.pages[session_id] = page
            self.active_sessions[session_id] = {
                'created_at': time.time(),
                'browser_type': browser_type,
                'headless': headless
            }
            
            return {
                'success': True,
                'session_id': session_id,
                'browser_type': browser_type,
                'headless': headless
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _handle_navigate(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Navigate to a URL"""
        try:
            session_id = task.get('session_id')
            url = task.get('url')
            
            if not session_id or session_id not in self.pages:
                return {'success': False, 'error': 'Invalid session ID'}
            
            page = self.pages[session_id]
            
            # Navigate to URL
            response = await page.goto(url, wait_until='domcontentloaded')
            
            return {
                'success': True,
                'url': url,
                'status': response.status,
                'title': await page.title()
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _handle_click(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Click an element"""
        try:
            session_id = task.get('session_id')
            selector = task.get('selector')
            
            if not session_id or session_id not in self.pages:
                return {'success': False, 'error': 'Invalid session ID'}
            
            page = self.pages[session_id]
            
            # Wait for element and click
            await page.wait_for_selector(selector, timeout=10000)
            await page.click(selector)
            
            return {
                'success': True,
                'action': 'click',
                'selector': selector
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _handle_fill(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Fill a form field"""
        try:
            session_id = task.get('session_id')
            selector = task.get('selector')
            value = task.get('value')
            
            if not session_id or session_id not in self.pages:
                return {'success': False, 'error': 'Invalid session ID'}
            
            page = self.pages[session_id]
            
            # Wait for element and fill
            await page.wait_for_selector(selector, timeout=10000)
            await page.fill(selector, value)
            
            return {
                'success': True,
                'action': 'fill',
                'selector': selector,
                'value_length': len(value)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _handle_type(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Type text into an element"""
        try:
            session_id = task.get('session_id')
            selector = task.get('selector')
            text = task.get('text')
            delay = task.get('delay', 100)
            
            if not session_id or session_id not in self.pages:
                return {'success': False, 'error': 'Invalid session ID'}
            
            page = self.pages[session_id]
            
            # Wait for element and type
            await page.wait_for_selector(selector, timeout=10000)
            await page.type(selector, text, delay=delay)
            
            return {
                'success': True,
                'action': 'type',
                'selector': selector,
                'text_length': len(text)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _handle_screenshot(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Take a screenshot"""
        try:
            session_id = task.get('session_id')
            full_page = task.get('full_page', False)
            
            if not session_id or session_id not in self.pages:
                return {'success': False, 'error': 'Invalid session ID'}
            
            page = self.pages[session_id]
            
            # Create screenshots directory
            screenshots_dir = self.config.get_data_path("screenshots")
            screenshots_dir.mkdir(exist_ok=True)
            
            # Generate filename
            filename = f"web_screenshot_{session_id}_{int(time.time())}.png"
            filepath = screenshots_dir / filename
            
            # Take screenshot
            await page.screenshot(path=str(filepath), full_page=full_page)
            
            return {
                'success': True,
                'action': 'screenshot',
                'filepath': str(filepath),
                'full_page': full_page
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _handle_extract_text(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Extract text from page or element"""
        try:
            session_id = task.get('session_id')
            selector = task.get('selector')
            
            if not session_id or session_id not in self.pages:
                return {'success': False, 'error': 'Invalid session ID'}
            
            page = self.pages[session_id]
            
            if selector:
                # Extract text from specific element
                await page.wait_for_selector(selector, timeout=10000)
                text = await page.text_content(selector)
            else:
                # Extract all text from page
                text = await page.text_content('body')
            
            return {
                'success': True,
                'action': 'extract_text',
                'text': text.strip() if text else '',
                'selector': selector
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _handle_extract_links(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Extract all links from page"""
        try:
            session_id = task.get('session_id')
            
            if not session_id or session_id not in self.pages:
                return {'success': False, 'error': 'Invalid session ID'}
            
            page = self.pages[session_id]
            
            # Extract all links
            links = await page.evaluate('''
                () => {
                    const links = Array.from(document.querySelectorAll('a[href]'));
                    return links.map(link => ({
                        text: link.textContent.trim(),
                        href: link.href,
                        title: link.title || null
                    }));
                }
            ''')
            
            return {
                'success': True,
                'action': 'extract_links',
                'links': links,
                'count': len(links)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _handle_wait_for_element(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Wait for an element to appear"""
        try:
            session_id = task.get('session_id')
            selector = task.get('selector')
            timeout = task.get('timeout', 30000)
            
            if not session_id or session_id not in self.pages:
                return {'success': False, 'error': 'Invalid session ID'}
            
            page = self.pages[session_id]
            
            # Wait for element
            await page.wait_for_selector(selector, timeout=timeout)
            
            return {
                'success': True,
                'action': 'wait_for_element',
                'selector': selector,
                'timeout': timeout
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _handle_scroll(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Scroll the page"""
        try:
            session_id = task.get('session_id')
            direction = task.get('direction', 'down')
            amount = task.get('amount', 500)
            
            if not session_id or session_id not in self.pages:
                return {'success': False, 'error': 'Invalid session ID'}
            
            page = self.pages[session_id]
            
            # Scroll page
            if direction == 'down':
                await page.evaluate(f'window.scrollBy(0, {amount})')
            elif direction == 'up':
                await page.evaluate(f'window.scrollBy(0, -{amount})')
            elif direction == 'top':
                await page.evaluate('window.scrollTo(0, 0)')
            elif direction == 'bottom':
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            
            return {
                'success': True,
                'action': 'scroll',
                'direction': direction,
                'amount': amount
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _handle_get_page_info(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Get page information"""
        try:
            session_id = task.get('session_id')
            
            if not session_id or session_id not in self.pages:
                return {'success': False, 'error': 'Invalid session ID'}
            
            page = self.pages[session_id]
            
            # Get page info
            title = await page.title()
            url = page.url
            
            # Get viewport size
            viewport = page.viewport_size
            
            # Get page metrics
            metrics = await page.evaluate('''
                () => ({
                    scrollHeight: document.body.scrollHeight,
                    scrollWidth: document.body.scrollWidth,
                    clientHeight: document.documentElement.clientHeight,
                    clientWidth: document.documentElement.clientWidth
                })
            ''')
            
            return {
                'success': True,
                'action': 'get_page_info',
                'title': title,
                'url': url,
                'viewport': viewport,
                'metrics': metrics
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _handle_download_file(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file download"""
        try:
            session_id = task.get('session_id')
            url = task.get('url')
            
            if not session_id or session_id not in self.pages:
                return {'success': False, 'error': 'Invalid session ID'}
            
            page = self.pages[session_id]
            
            # Create downloads directory
            downloads_dir = self.config.get_data_path("downloads")
            downloads_dir.mkdir(exist_ok=True)
            
            # Start download
            async with page.expect_download() as download_info:
                await page.goto(url)
            
            download = await download_info.value
            
            # Save file
            filename = download.suggested_filename
            filepath = downloads_dir / filename
            await download.save_as(str(filepath))
            
            return {
                'success': True,
                'action': 'download_file',
                'filename': filename,
                'filepath': str(filepath),
                'size': filepath.stat().st_size
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _handle_upload_file(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file upload"""
        try:
            session_id = task.get('session_id')
            selector = task.get('selector')
            filepath = task.get('filepath')
            
            if not session_id or session_id not in self.pages:
                return {'success': False, 'error': 'Invalid session ID'}
            
            page = self.pages[session_id]
            
            # Upload file
            await page.set_input_files(selector, filepath)
            
            return {
                'success': True,
                'action': 'upload_file',
                'selector': selector,
                'filepath': filepath
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _handle_execute_script(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute JavaScript on the page"""
        try:
            session_id = task.get('session_id')
            script = task.get('script')
            
            if not session_id or session_id not in self.pages:
                return {'success': False, 'error': 'Invalid session ID'}
            
            page = self.pages[session_id]
            
            # Execute script
            result = await page.evaluate(script)
            
            return {
                'success': True,
                'action': 'execute_script',
                'result': result
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _handle_close_session(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Close a browser session"""
        try:
            session_id = task.get('session_id')
            
            if session_id not in self.active_sessions:
                return {'success': False, 'error': 'Session not found'}
            
            # Close page
            if session_id in self.pages:
                await self.pages[session_id].close()
                del self.pages[session_id]
            
            # Close context
            if session_id in self.contexts:
                await self.contexts[session_id].close()
                del self.contexts[session_id]
            
            # Close browser
            if session_id in self.browsers:
                await self.browsers[session_id].close()
                del self.browsers[session_id]
            
            # Remove session
            del self.active_sessions[session_id]
            
            return {
                'success': True,
                'action': 'close_session',
                'session_id': session_id
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _install_playwright(self):
        """Install Playwright and browsers"""
        try:
            import subprocess
            import sys
            
            # Install playwright
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'playwright'])
            
            # Install browsers
            subprocess.check_call([sys.executable, '-m', 'playwright', 'install'])
            
            self.logger.info("Playwright installed successfully")
            
            # Try to import again
            global PLAYWRIGHT_AVAILABLE
            try:
                from playwright.async_api import async_playwright
                PLAYWRIGHT_AVAILABLE = True
            except ImportError:
                self.logger.error("Failed to import Playwright after installation")
                
        except Exception as e:
            self.logger.error(f"Failed to install Playwright: {e}")
            raise
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a session"""
        if session_id in self.active_sessions:
            session_info = self.active_sessions[session_id].copy()
            session_info['session_id'] = session_id
            session_info['has_page'] = session_id in self.pages
            session_info['uptime'] = time.time() - session_info['created_at']
            return session_info
        return None
    
    def list_active_sessions(self) -> List[Dict[str, Any]]:
        """List all active sessions"""
        sessions = []
        for session_id in self.active_sessions:
            session_info = self.get_session_info(session_id)
            if session_info:
                sessions.append(session_info)
        return sessions
    
    async def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Clean up old inactive sessions"""
        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            sessions_to_close = []
            for session_id, session_info in self.active_sessions.items():
                if current_time - session_info['created_at'] > max_age_seconds:
                    sessions_to_close.append(session_id)
            
            for session_id in sessions_to_close:
                await self._handle_close_session({'session_id': session_id})
            
            self.logger.info(f"Cleaned up {len(sessions_to_close)} old sessions")
            return len(sessions_to_close)
            
        except Exception as e:
            self.logger.warning(f"Failed to cleanup sessions: {e}")
            return 0
    
    def get_web_automation_stats(self) -> Dict[str, Any]:
        """Get web automation service statistics"""
        return {
            "playwright_available": PLAYWRIGHT_AVAILABLE,
            "active_sessions": len(self.active_sessions),
            "browsers": list(self.browsers.keys()),
            "contexts": list(self.contexts.keys()),
            "pages": list(self.pages.keys())
        }