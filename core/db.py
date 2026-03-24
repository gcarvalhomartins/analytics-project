"""
Database Factory - Factory de conexões múltiplas fontes de dados

Suporta:
- PostgreSQL
- MySQL
- SQLite
- CSV (arquivos locais)
"""
import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, Optional, Union

import pandas as pd
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)


class DatabaseFactory:
    """Factory para criar e gerenciar conexões de dados."""
    
    _engines: Dict[str, Engine] = {}
    _csv_cache: Dict[str, pd.DataFrame] = {}
    
    @classmethod
    def get_data_source(cls, config: Dict[str, Any]) -> pd.DataFrame:
        """Obtém dados de acordo com o tipo de fonte configurada.
        
        Args:
            config: Dicionário com configuração da fonte de dados
                - type: postgresql, mysql, sqlite, csv
                - Para bancos: host, port, name, user, password, etc.
                - Para CSV: path (caminho do arquivo)
        
        Returns:
            DataFrame com os dados
        """
        if not config:
            return pd.DataFrame()
        
        data_type = config.get("type", "csv").lower()
        
        if data_type == "csv":
            return cls._read_csv(config)
        
        return cls._query_database(config)
    
    @classmethod
    def test_connection(cls, config: Dict[str, Any]) -> bool:
        """Testa conexão com a fonte de dados."""
        if not config:
            return False
        
        data_type = config.get("type", "csv").lower()
        
        if data_type == "csv":
            path = config.get("path", "")
            if not path:
                return False
            resolved_path = cls._resolve_env_vars({"path": path})["path"]
            return Path(resolved_path).exists()
        
        try:
            cls._get_engine(config)
            return True
        except Exception as e:
            logger.error(f"Erro ao testar conexão: {e}")
            return False
    
    @classmethod
    def _read_csv(cls, config: Dict[str, Any]) -> pd.DataFrame:
        """Lê dados de um arquivo CSV.
        
        Args:
            config: Dicionário com configuração
                - path: caminho do arquivo CSV (suporta variáveis de ambiente)
                - delimiter: delimitador padrão é vírgula
                - encoding: encoding padrão utf-8
        
        Returns:
            DataFrame com os dados do CSV
        """
        resolved = cls._resolve_env_vars(config)
        
        path = resolved.get("path", "")
        if not path:
            logger.warning("CSV path não especificado")
            return pd.DataFrame()
        
        file_path = Path(path)
        if not file_path.exists():
            logger.warning(f"Arquivo CSV não encontrado: {path}")
            return pd.DataFrame()
        
        cache_key = str(file_path.absolute())
        if cache_key in cls._csv_cache:
            return cls._csv_cache[cache_key].copy()
        
        try:
            delimiter = resolved.get("delimiter", ",")
            encoding = resolved.get("encoding", "utf-8")
            
            df = pd.read_csv(
                file_path,
                delimiter=delimiter,
                encoding=encoding,
            )
            
            cls._csv_cache[cache_key] = df.copy()
            logger.info(f"CSV carregado: {path} ({len(df)} linhas)")
            return df
            
        except Exception as e:
            logger.error(f"Erro ao ler CSV {path}: {e}")
            return pd.DataFrame()
    
    @classmethod
    def _query_database(cls, config: Dict[str, Any]) -> pd.DataFrame:
        """Executa query no banco de dados.
        
        Args:
            config: Dicionário com configuração do banco
        
        Returns:
            DataFrame com os resultados
        """
        engine = cls._get_engine(config)
        
        query = config.get("query", "")
        table = config.get("table", "")
        
        if query:
            sql = text(query)
        elif table:
            sql = text(f"SELECT * FROM {table}")
        else:
            logger.warning("Nenhuma query ou tabela especificada")
            return pd.DataFrame()
        
        try:
            with engine.connect() as conn:
                df = pd.read_sql(sql, conn)
            return df
        except Exception as e:
            logger.error(f"Erro ao executar query: {e}")
            return pd.DataFrame()
    
    @classmethod
    def _get_engine(cls, db_config: Dict[str, Any]) -> Engine:
        """Cria ou retorna engine do banco de dados."""
        if not db_config:
            raise ValueError("Configuração de banco não fornecida")
        
        db_type = db_config.get("type", "sqlite")
        cache_key = cls._get_cache_key(db_config)
        
        if cache_key in cls._engines:
            return cls._engines[cache_key]
        
        engine = cls._create_engine(db_config)
        cls._engines[cache_key] = engine
        
        return engine
    
    @classmethod
    def _get_cache_key(cls, db_config: Dict[str, Any]) -> str:
        """Gera chave única para cache de engines."""
        db_type = db_config.get("type", "sqlite")
        name = db_config.get("name", db_config.get("path", ""))
        host = db_config.get("host", "localhost")
        return f"{db_type}:{host}:{name}"
    
    @classmethod
    def _create_engine(cls, db_config: Dict[str, Any]) -> Engine:
        """Cria nova engine SQLAlchemy."""
        db_type = db_config.get("type", "sqlite")
        
        resolved_config = cls._resolve_env_vars(db_config)
        
        url = cls._build_connection_url(db_type, resolved_config)
        
        engine = create_engine(
            url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            echo=False,
        )
        
        logger.info(f"Criada engine para {db_type}: {resolved_config.get('name', resolved_config.get('path', 'unknown'))}")
        
        return engine
    
    @classmethod
    def _resolve_env_vars(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve variáveis de ambiente no formato ${VAR}."""
        resolved = {}
        for key, value in config.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                var_name = value[2:-1]
                resolved[key] = os.environ.get(var_name, value)
            else:
                resolved[key] = value
        return resolved
    
    @classmethod
    def _build_connection_url(cls, db_type: str, config: Dict[str, Any]) -> str:
        """Constrói URL de conexão baseada no tipo de banco."""
        if db_type == "sqlite":
            db_path = config.get("path", ":memory:")
            return f"sqlite:///{db_path}"
        
        host = config.get("host", "localhost")
        port = config.get("port", 5432)
        name = config.get("name", "")
        user = config.get("user", "")
        password = config.get("password", "")
        
        if db_type == "postgresql":
            return f"postgresql://{user}:{password}@{host}:{port}/{name}"
        
        if db_type == "mysql":
            return f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}"
        
        if db_type == "mssql":
            return f"mssql+pyodbc://{user}:{password}@{host}:{port}/{name}"
        
        raise ValueError(f"Tipo de banco não suportado: {db_type}")
    
    @classmethod
    @contextmanager
    def get_session(cls, db_config: Dict[str, Any]) -> Generator:
        """Context manager para obter sessão do banco."""
        engine = cls._get_engine(db_config)
        connection = engine.connect()
        transaction = connection.begin()
        
        try:
            yield connection
            transaction.commit()
        except Exception:
            transaction.rollback()
            raise
        finally:
            connection.close()
    
    @classmethod
    def clear_cache(cls) -> None:
        """Limpa o cache de CSVs e engines."""
        cls._csv_cache.clear()
        cls._engines.clear()
        logger.info("Cache limpo")
