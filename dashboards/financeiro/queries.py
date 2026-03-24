"""
Queries SQL para o dashboard financeiro.

Funções que retornam DataFrames com dados do banco de dados.
"""
from typing import Any, Union

import pandas as pd
from sqlalchemy import Engine, text


def get_monthly_cash_flow(engine: Union[Engine, Any]) -> pd.DataFrame:
    """Retorna fluxo de caixa mensal.
    
    Args:
        engine: Engine SQLAlchemy do banco de dados
        
    Returns:
        DataFrame com colunas: mes, receita, despesa, recebimentos, pagamentos
    """
    query = text("""
        SELECT 
            TO_CHAR(data, 'Mon') as mes,
            SUM(CASE WHEN tipo = 'receita' THEN valor ELSE 0 END) as receita,
            SUM(CASE WHEN tipo = 'despesa' THEN valor ELSE 0 END) as despesa,
            SUM(CASE WHEN tipo = 'recebimento' THEN valor ELSE 0 END) as recebimentos,
            SUM(CASE WHEN tipo = 'pagamento' THEN valor ELSE 0 END) as pagamentos
        FROM fluxo_caixa
        WHERE data >= DATE_TRUNC('year', CURRENT_DATE)
        GROUP BY TO_CHAR(data, 'YYYY-MM'), TO_CHAR(data, 'Mon')
        ORDER BY TO_CHAR(data, 'YYYY-MM')
    """)
    
    try:
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        return df
    except Exception:
        return pd.DataFrame()


def get_accounts_receivable(engine: Union[Engine, Any]) -> pd.DataFrame:
    """Retorna contas a receber vencidas.
    
    Args:
        engine: Engine SQLAlchemy
        
    Returns:
        DataFrame com colunas: cliente, valor, dias_atraso
    """
    query = text("""
        SELECT 
            c.nome as cliente,
            f.valor,
            CURRENT_DATE - f.data_vencimento as dias_atraso
        FROM fluxos f
        JOIN clientes c ON f.id_cliente = c.id
        WHERE f.tipo = 'receita'
          AND f.status = 'pendente'
          AND f.data_vencimento < CURRENT_DATE
        ORDER BY dias_atraso DESC
    """)
    
    try:
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        return df
    except Exception:
        return pd.DataFrame()


def get_projection(engine: Union[Engine, Any], months: int = 6) -> pd.DataFrame:
    """Retorna projeção de receita para os próximos meses.
    
    Args:
        engine: Engine SQLAlchemy
        months: Número de meses para projetar
        
    Returns:
        DataFrame com colunas: mes, projetado
    """
    query = text("""
        WITH mensal AS (
            SELECT 
                TO_CHAR(data, 'YYYY-MM') as ano_mes,
                SUM(valor) as receita
            FROM fluxos
            WHERE tipo = 'receita'
              AND data >= DATE_TRUNC('year', CURRENT_DATE - INTERVAL '1 year')
            GROUP BY TO_CHAR(data, 'YYYY-MM')
        )
        SELECT 
            AVG(receita) as media_mensal
        FROM mensal
    """)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(query)
            row = result.fetchone()
        
        if row:
            media = row[0] or 0
            crescimento = 1.05
            
            meses = ["Jul", "Ago", "Set", "Out", "Nov", "Dez"][:months]
            projecao = [media * (crescimento ** i) for i in range(months)]
            
            return pd.DataFrame({"mes": meses, "projetado": projecao})
    except Exception:
        pass
    
    return pd.DataFrame()
