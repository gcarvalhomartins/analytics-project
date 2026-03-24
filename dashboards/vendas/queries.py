"""
Queries SQL para o dashboard de vendas.

Funções que retornam DataFrames com dados do banco de dados.
"""
from typing import Any, Union

import pandas as pd
from sqlalchemy import Engine, text


def get_monthly_sales(engine: Union[Engine, Any]) -> pd.DataFrame:
    """Retorna vendas mensais.
    
    Args:
        engine: Engine SQLAlchemy do banco de dados
        
    Returns:
        DataFrame com colunas: mes, vendas, pedidos, clientes_novos
    """
    query = text("""
        SELECT 
            TO_CHAR(data_venda, 'Mon') as mes,
            SUM(valor_total) as vendas,
            COUNT(DISTINCT id_pedido) as pedidos,
            COUNT(DISTINCT id_cliente) as clientes_novos
        FROM vendas
        WHERE data_venda >= DATE_TRUNC('year', CURRENT_DATE)
        GROUP BY TO_CHAR(data_venda, 'YYYY-MM'), TO_CHAR(data_venda, 'Mon')
        ORDER BY TO_CHAR(data_venda, 'YYYY-MM')
    """)
    
    try:
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        return df
    except Exception:
        return pd.DataFrame()


def get_top_products(engine: Union[Engine, Any], limit: int = 10) -> pd.DataFrame:
    """Retorna produtos mais vendidos.
    
    Args:
        engine: Engine SQLAlchemy
        limit: Número de produtos a retornar
        
    Returns:
        DataFrame com colunas: produto, quantidade, receita
    """
    query = text("""
        SELECT 
            p.nome as produto,
            SUM(iv.quantidade) as quantidade,
            SUM(iv.quantidade * iv.preco_unitario) as receita
        FROM itens_venda iv
        JOIN produtos p ON iv.id_produto = p.id
        JOIN vendas v ON iv.id_venda = v.id
        WHERE v.data_venda >= CURRENT_DATE - INTERVAL '30 days'
        GROUP BY p.id, p.nome
        ORDER BY receita DESC
        LIMIT :limit
    """)
    
    try:
        with engine.connect() as conn:
            df = pd.read_sql(query, conn, params={"limit": limit})
        return df
    except Exception:
        return pd.DataFrame()


def get_sales_by_region(engine: Union[Engine, Any]) -> pd.DataFrame:
    """Retorna vendas por região.
    
    Args:
        engine: Engine SQLAlchemy
        
    Returns:
        DataFrame com colunas: regiao, vendas
    """
    query = text("""
        SELECT 
            c.regiao,
            SUM(v.valor_total) as vendas
        FROM vendas v
        JOIN clientes c ON v.id_cliente = c.id
        WHERE v.data_venda >= DATE_TRUNC('year', CURRENT_DATE)
        GROUP BY c.regiao
        ORDER BY vendas DESC
    """)
    
    try:
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        return df
    except Exception:
        return pd.DataFrame()
