"""
Hit Rate Tracker - Sistema de tracking de performance das previsões
Monitora acurácia das análises vs. movimento real do DXY
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import asyncio
import aiohttp
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class PredictionRecord:
    """Registro de uma previsão"""
    timestamp: datetime
    event_type: str
    usd_score: float
    classification: str
    dxy_30m: Optional[float]
    dxy_60m: Optional[float]
    dxy_120m: Optional[float]
    hit_30m: Optional[bool]
    hit_60m: Optional[bool]
    hit_120m: Optional[bool]

class HitRateTracker:
    """Sistema de tracking da taxa de acerto das previsões"""
    
    def __init__(self, db_path: str = "macro_bot.db"):
        self.db_path = db_path
        self.setup_database()
        
    def setup_database(self):
        """Inicializa banco de dados SQLite"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create predictions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    usd_score REAL NOT NULL,
                    classification TEXT NOT NULL,
                    dxy_30m REAL,
                    dxy_60m REAL,
                    dxy_120m REAL,
                    hit_30m INTEGER,
                    hit_60m INTEGER,
                    hit_120m INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create index for faster queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON predictions(timestamp)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_event_type 
                ON predictions(event_type)
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info("Database setup completed")
            
        except Exception as e:
            logger.error(f"Erro ao configurar database: {e}")
    
    def log_prediction(self, event_type: str, usd_score: float, 
                      classification: str, timestamp: datetime = None):
        """Registra uma nova previsão"""
        try:
            if timestamp is None:
                timestamp = datetime.now()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO predictions 
                (timestamp, event_type, usd_score, classification)
                VALUES (?, ?, ?, ?)
            ''', (timestamp.isoformat(), event_type, usd_score, classification))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Prediction logged: {event_type} - Score: {usd_score:.2f}")
            
            # Schedule DXY data collection for later
            asyncio.create_task(self._schedule_dxy_collection(timestamp, event_type))
            
        except Exception as e:
            logger.error(f"Erro ao registrar previsão: {e}")
    
    async def _schedule_dxy_collection(self, prediction_time: datetime, event_type: str):
        """Agenda coleta de dados DXY para diferentes janelas temporais"""
        try:
            # Wait for different intervals and collect DXY data
            intervals = [30, 60, 120]  # minutes
            
            for interval in intervals:
                await asyncio.sleep(interval * 60)  # Convert to seconds
                
                dxy_return = await self._get_dxy_return(prediction_time, interval)
                if dxy_return is not None:
                    await self._update_prediction_with_dxy(
                        prediction_time, event_type, interval, dxy_return
                    )
                    
        except Exception as e:
            logger.error(f"Erro no agendamento DXY: {e}")
    
    async def _get_dxy_return(self, start_time: datetime, minutes: int) -> Optional[float]:
        """Calcula retorno do DXY em uma janela de tempo específica"""
        try:
            end_time = start_time + timedelta(minutes=minutes)
            
            # Get DXY data from Yahoo Finance
            symbol = 'DX-Y.NYB'
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            
            params = {
                'interval': '1m',
                'period1': int(start_time.timestamp()),
                'period2': int(end_time.timestamp())
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        result = data.get('chart', {}).get('result', [])
                        
                        if result:
                            quotes = result[0].get('indicators', {}).get('quote', [{}])[0]
                            closes = [c for c in quotes.get('close', []) if c is not None]
                            
                            if len(closes) >= 2:
                                start_price = closes[0]
                                end_price = closes[-1]
                                
                                return_pct = ((end_price - start_price) / start_price) * 100
                                return return_pct
                    
            return None
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados DXY: {e}")
            return None
    
    async def _update_prediction_with_dxy(self, timestamp: datetime, event_type: str,
                                        interval: int, dxy_return: float):
        """Atualiza previsão com dados do DXY e calcula hit rate"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get the prediction
            cursor.execute('''
                SELECT id, usd_score, classification FROM predictions
                WHERE timestamp = ? AND event_type = ?
            ''', (timestamp.isoformat(), event_type))
            
            result = cursor.fetchone()
            if not result:
                conn.close()
                return
            
            pred_id, usd_score, classification = result
            
            # Calculate hit
            hit = self._calculate_hit(usd_score, dxy_return)
            
            # Update database
            column_name = f"dxy_{interval}m"
            hit_column = f"hit_{interval}m"
            
            cursor.execute(f'''
                UPDATE predictions 
                SET {column_name} = ?, {hit_column} = ?
                WHERE id = ?
            ''', (dxy_return, 1 if hit else 0, pred_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Updated prediction {pred_id}: {interval}m DXY={dxy_return:.2f}%, Hit={hit}")
            
        except Exception as e:
            logger.error(f"Erro ao atualizar previsão com DXY: {e}")
    
    def _calculate_hit(self, usd_score: float, dxy_return: float) -> bool:
        """Calcula se a previsão foi correta"""
        # Hit criteria:
        # - Score > +0.5 and DXY > 0 = Hit
        # - Score < -0.5 and DXY < 0 = Hit  
        # - |Score| <= 0.5 = Neutral (always hit for now)
        
        if abs(usd_score) <= 0.5:
            return True  # Neutral predictions are considered hits
        
        if usd_score > 0.5 and dxy_return > 0:
            return True
        
        if usd_score < -0.5 and dxy_return < 0:
            return True
        
        return False
    
    def get_performance_metrics(self, days_back: int = 30) -> Dict[str, Any]:
        """Calcula métricas de performance dos últimos N dias"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all predictions with complete data
            cursor.execute('''
                SELECT event_type, usd_score, classification,
                       hit_30m, hit_60m, hit_120m
                FROM predictions
                WHERE timestamp >= ?
                AND (hit_30m IS NOT NULL OR hit_60m IS NOT NULL OR hit_120m IS NOT NULL)
            ''', (cutoff_date.isoformat(),))
            
            results = cursor.fetchall()
            conn.close()
            
            if not results:
                return {}
            
            # Calculate overall metrics
            overall_30m = []
            overall_60m = []
            overall_120m = []
            
            by_indicator = {}
            
            for event_type, usd_score, classification, hit_30m, hit_60m, hit_120m in results:
                
                if hit_30m is not None:
                    overall_30m.append(hit_30m)
                if hit_60m is not None:
                    overall_60m.append(hit_60m)
                if hit_120m is not None:
                    overall_120m.append(hit_120m)
                
                # By indicator
                if event_type not in by_indicator:
                    by_indicator[event_type] = {
                        'hits': [],
                        'total': 0
                    }
                
                # Use average of available timeframes for indicator metrics
                available_hits = [h for h in [hit_30m, hit_60m, hit_120m] if h is not None]
                if available_hits:
                    avg_hit = sum(available_hits) / len(available_hits)
                    by_indicator[event_type]['hits'].append(avg_hit)
                    by_indicator[event_type]['total'] += 1
            
            # Calculate final metrics
            metrics = {
                'overall': {
                    '30m': sum(overall_30m) / len(overall_30m) if overall_30m else 0,
                    '60m': sum(overall_60m) / len(overall_60m) if overall_60m else 0,
                    '120m': sum(overall_120m) / len(overall_120m) if overall_120m else 0
                },
                'by_indicator': {},
                'total_predictions': len(results),
                'period_days': days_back
            }
            
            for indicator, data in by_indicator.items():
                if data['hits']:
                    metrics['by_indicator'][indicator] = {
                        'hit_rate': sum(data['hits']) / len(data['hits']),
                        'count': data['total']
                    }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Erro ao calcular métricas: {e}")
            return {}
    
    def get_recent_predictions(self, limit: int = 10) -> List[PredictionRecord]:
        """Retorna previsões recentes"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT timestamp, event_type, usd_score, classification,
                       dxy_30m, dxy_60m, dxy_120m,
                       hit_30m, hit_60m, hit_120m
                FROM predictions
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            
            results = cursor.fetchall()
            conn.close()
            
            records = []
            for row in results:
                record = PredictionRecord(
                    timestamp=datetime.fromisoformat(row[0]),
                    event_type=row[1],
                    usd_score=row[2],
                    classification=row[3],
                    dxy_30m=row[4],
                    dxy_60m=row[5],
                    dxy_120m=row[6],
                    hit_30m=bool(row[7]) if row[7] is not None else None,
                    hit_60m=bool(row[8]) if row[8] is not None else None,
                    hit_120m=bool(row[9]) if row[9] is not None else None
                )
                records.append(record)
            
            return records
            
        except Exception as e:
            logger.error(f"Erro ao buscar previsões recentes: {e}")
            return []
    
    def cleanup_old_data(self, days_to_keep: int = 90):
        """Remove dados antigos para manter database otimizado"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM predictions
                WHERE timestamp < ?
            ''', (cutoff_date.isoformat(),))
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info(f"Cleaned up {deleted_count} old prediction records")
            
        except Exception as e:
            logger.error(f"Erro na limpeza de dados: {e}")
    
    def export_data(self, filepath: str, days_back: int = 30):
        """Exporta dados para CSV"""
        try:
            import csv
            
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM predictions
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
            ''', (cutoff_date.isoformat(),))
            
            results = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            
            conn.close()
            
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(columns)
                writer.writerows(results)
            
            logger.info(f"Data exported to {filepath}: {len(results)} records")
            
        except Exception as e:
            logger.error(f"Erro na exportação: {e}")