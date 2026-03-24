"""
Queries SQL para o dashboard de Borba.
"""
from typing import Any, Union

import pandas as pd
from sqlalchemy import Engine, text


def load_sasi_events(engine: Union[Engine, Any]) -> pd.DataFrame:
    """Carrega eventos do SASI.
    
    Args:
        engine: Engine SQLAlchemy
        
    Returns:
        DataFrame com colunas: id, created_at, alert_id, type, channel_id, app_id, secretaria, message, generated_at, mes
    """
    query = text("""
        SELECT
            id, created_at, alert_id, type, channel_id, app_id,
            data->'channel'->>'name'  AS secretaria,
            data->>'message'          AS message,
            data->>'generatedAt'      AS generated_at
        FROM public.sasi_events
    """)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(query)
            rows = result.fetchall()
            
        if not rows:
            return pd.DataFrame(columns=[
                'id', 'created_at', 'alert_id', 'type', 'channel_id',
                'app_id', 'secretaria', 'message', 'generated_at', 'mes'
            ])
        
        df = pd.DataFrame(rows)
        df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
        df['secretaria'] = df['secretaria'].fillna(df['channel_id'].astype(str))
        df['mes'] = df['created_at'].dt.to_period('M').astype(str)
        return df
    except Exception:
        return pd.DataFrame(columns=[
            'id', 'created_at', 'alert_id', 'type', 'channel_id',
            'app_id', 'secretaria', 'message', 'generated_at', 'mes'
        ])


def load_secretarias(engine: Union[Engine, Any]) -> pd.DataFrame:
    """Carrega dados das secretarias.
    
    Args:
        engine: Engine SQLAlchemy
        
    Returns:
        DataFrame com colunas: channel_id, secretaria, total_solicitacoes
    """
    query = text("""
        SELECT channel_id, secretaria, total_solicitacoes
        FROM public.secretarias_counts
        ORDER BY total_solicitacoes DESC
    """)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(query)
            rows = result.fetchall()
            
        if not rows:
            return pd.DataFrame(columns=['channel_id', 'secretaria', 'total_solicitacoes'])
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame(columns=['channel_id', 'secretaria', 'total_solicitacoes'])
