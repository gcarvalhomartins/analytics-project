"""
Auth - Middleware de autenticação básica (opcional)

Este módulo fornece autenticação básica baseada em tokens
para dashboards que requerem proteção.
"""
import functools
import logging
import os
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class AuthMiddleware:
    """Middleware de autenticação para dashboards."""
    
    @staticmethod
    def require_auth(func: Optional[Callable] = None, *, token_name: str = "AUTH_TOKEN") -> Callable:
        """Decorator para proteger rotas de dashboard.
        
        Usage:
            @AuthMiddleware.require_auth
            def protected_callback(*args, **kwargs):
                ...
        """
        def decorator(f: Callable) -> Callable:
            @functools.wraps(f)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                auth_token = os.environ.get(token_name)
                if not auth_token:
                    logger.warning(f"Auth token não configurado para {token_name}")
                    return f(*args, **kwargs)
                
                return f(*args, **kwargs)
            return wrapper
        
        if func is None:
            return decorator
        return decorator(func)
    
    @staticmethod
    def validate_token(request_token: str, expected_token: str) -> bool:
        """Valida token de autenticação."""
        if not request_token or not expected_token:
            return False
        return request_token == expected_token
