"""Compatibility shim: lazily load symbols from the sibling `apps.py` file.

There is both a module `chatbot/apps.py` and a package `chatbot/apps/` in
this repository. Importing the package directly during Django startup caused
an import cycle. To avoid that, this shim dynamically loads the sibling
`apps.py` file by path and exposes the expected symbols without triggering
the normal package import resolution.
"""
import importlib.util
import importlib.machinery
import os
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_apps_py = _HERE.parent / 'apps.py'

if _apps_py.exists():
	spec = importlib.util.spec_from_file_location('chatbot._apps_impl', str(_apps_py))
	_mod = importlib.util.module_from_spec(spec)
	loader = spec.loader
	if loader is not None:
		loader.exec_module(_mod)

	ChatbotConfig = getattr(_mod, 'ChatbotConfig')
	get_chat_agent = getattr(_mod, 'get_chat_agent')
	set_chat_agent = getattr(_mod, 'set_chat_agent')
	__all__ = ["ChatbotConfig", "get_chat_agent", "set_chat_agent"]
else:
	# Fallback: expose placeholders to avoid import errors during early startup
	ChatbotConfig = None
	def get_chat_agent():
		return None
	def set_chat_agent(agent):
		pass
	__all__ = ["ChatbotConfig", "get_chat_agent", "set_chat_agent"]
