"""
Scoring Engine - Sistema de interpretação e scoring dos indicadores
Implementa regras determinísticas para calcular USD Score
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import statistics

from data_ingestor import EconomicDataPoint
from config import Config

logger = logging.getLogger(__name__)

@dataclass 
class ComponentScore:
    """Score de um componente individual"""
    indicator: str
    actual: Optional[float]
    consensus: Optional[float]
    previous: Optional[float]
    surprise_pct: float
    component_score: float  # -2 to +2
    weight: float
    confidence_factor: float

@dataclass
class USDAnalysis:
    """Análise completa do USD"""
    timestamp: datetime
    indicators: List[ComponentScore]
    raw_score: float
    score: float  # Weighted average
    classification: str
    confidence: str
    base_scenario: Dict[str, Any]
    alternative_scenario: Dict[str, Any]
    directional_suggestion: str
    suggested_pairs: List[str]

class ScoringEngine:
    """Motor de scoring para análise macroeconômica"""
    
    def __init__(self):
        self.config = Config()
        
        # Classification thresholds
        self.classification_thresholds = {
            'USD Forte': 1.5,
            'Levemente Forte': 0.5,
            'Neutro': (-0.5, 0.5),
            'Levemente Fraco': -0.5,
            'USD Fraco': -1.5
        }
        
        # Directional mapping
        self.directional_mapping = {
            'USD Forte': 'VENDA EUR/USD, GBP/USD; COMPRA USD/JPY',
            'Levemente Forte': 'Viés de venda EUR/USD, aguardar confirmação',
            'Neutro': 'Aguardar confirmação direcional, foco em ranges',
            'Levemente Fraco': 'Viés de compra EUR/USD, aguardar confirmação', 
            'USD Fraco': 'COMPRA EUR/USD, GBP/USD; VENDA USD/JPY'
        }
        
        # Currency pairs by scenario
        self.pairs_mapping = {
            'USD Forte': ['EUR/USD', 'GBP/USD', 'AUD/USD', 'USD/JPY', 'USD/CHF'],
            'Levemente Forte': ['EUR/USD', 'GBP/USD', 'USD/JPY'],
            'Neutro': ['EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD'],
            'Levemente Fraco': ['EUR/USD', 'GBP/USD', 'USD/JPY'],
            'USD Fraco': ['EUR/USD', 'GBP/USD', 'AUD/USD', 'NZD/USD', 'USD/JPY']
        }
    
    def calculate_usd_score(self, data_points: List[EconomicDataPoint]) -> USDAnalysis:
        """Calcula USD Score baseado nos dados econômicos"""
        try:
            if not data_points:
                return self._create_empty_analysis()
            
            # Calculate component scores
            component_scores = []
            
            for data_point in data_points:
                component = self._calculate_component_score(data_point)
                if component:
                    component_scores.append(component)
            
            if not component_scores:
                return self._create_empty_analysis()
            
            # Calculate weighted USD score
            weighted_sum = sum(comp.component_score * comp.weight for comp in component_scores)
            total_weight = sum(comp.weight for comp in component_scores)
            
            raw_score = sum(comp.component_score for comp in component_scores) / len(component_scores)
            usd_score = weighted_sum / total_weight if total_weight > 0 else 0
            
            # Classify score
            classification = self._classify_score(usd_score)
            confidence = self._calculate_confidence(component_scores, usd_score)
            
            # Generate scenarios
            base_scenario, alt_scenario = self._generate_scenarios(
                component_scores, usd_score, classification
            )
            
            # Directional suggestion
            directional = self.directional_mapping.get(classification, 'Aguardar dados')
            pairs = self.pairs_mapping.get(classification, ['EUR/USD', 'USD/JPY'])
            
            return USDAnalysis(
                timestamp=datetime.now(),
                indicators=component_scores,
                raw_score=raw_score,
                score=usd_score,
                classification=classification,
                confidence=confidence,
                base_scenario=base_scenario,
                alternative_scenario=alt_scenario,
                directional_suggestion=directional,
                suggested_pairs=pairs
            )
            
        except Exception as e:
            logger.error(f"Erro ao calcular USD score: {e}")
            return self._create_empty_analysis()
    
    def _calculate_component_score(self, data_point: EconomicDataPoint) -> Optional[ComponentScore]:
        """Calcula score de um componente individual"""
        try:
            indicator_name = self._normalize_indicator_name(data_point.indicator)
            indicator_config = self.config.get_indicator_config(indicator_name)
            
            if not indicator_config:
                logger.warning(f"Configuração não encontrada para {indicator_name}")
                return None
            
            # Calculate surprise if needed
            surprise_pct = data_point.surprise_pct or 0
            
            if data_point.actual is not None and data_point.consensus is not None:
                if data_point.consensus != 0:
                    surprise_pct = ((data_point.actual - data_point.consensus) / abs(data_point.consensus)) * 100
                else:
                    # Use YoY or previous if consensus is 0
                    if data_point.previous is not None and data_point.previous != 0:
                        surprise_pct = ((data_point.actual - data_point.previous) / abs(data_point.previous)) * 100
            
            # Calculate component score (-2 to +2)
            component_score = self._map_surprise_to_score(
                indicator_name, surprise_pct, data_point.actual, data_point.consensus
            )
            
            # Apply inversion if needed (e.g., unemployment)
            if indicator_config.get('inversion', False):
                component_score *= -1
            
            # Weight and confidence
            weight = indicator_config.get('weight', 1.0)
            confidence_factor = self._calculate_component_confidence(data_point, indicator_config)
            
            # Reduce weight if no consensus
            if data_point.consensus is None:
                weight *= 0.5
                logger.info(f"Peso reduzido para {indicator_name} (sem consenso): {weight}")
            
            return ComponentScore(
                indicator=indicator_name,
                actual=data_point.actual,
                consensus=data_point.consensus,
                previous=data_point.previous,
                surprise_pct=surprise_pct,
                component_score=component_score,
                weight=weight,
                confidence_factor=confidence_factor
            )
            
        except Exception as e:
            logger.error(f"Erro ao calcular component score para {data_point.indicator}: {e}")
            return None
    
    def _map_surprise_to_score(self, indicator: str, surprise_pct: float, 
                               actual: Optional[float], consensus: Optional[float]) -> float:
        """Mapeia surpresa para score (-2 a +2)"""
        
        # Special handling for different indicator types
        if indicator in ['CPI', 'CORE_CPI', 'PCE', 'CORE_PCE']:
            # Inflation: delta in percentage points
            if actual is not None and consensus is not None:
                delta_pp = actual - consensus
                
                if delta_pp <= -0.20:
                    return -2
                elif delta_pp <= -0.10:
                    return -1
                elif -0.09 <= delta_pp <= 0.09:
                    return 0
                elif delta_pp <= 0.19:
                    return 1
                else:
                    return 2
        
        elif indicator in ['NFP', 'ADP']:
            # Employment: surprise percentage
            if surprise_pct <= -30:
                return -2
            elif surprise_pct <= -10:
                return -1
            elif -10 <= surprise_pct <= 10:
                return 0
            elif surprise_pct <= 30:
                return 1
            else:
                return 2
        
        elif indicator == 'UNEMPLOYMENT':
            # Unemployment: delta vs consensus (inverted later)
            if actual is not None and consensus is not None:
                delta_pp = actual - consensus
                
                if delta_pp <= -0.20:
                    return 2  # Lower unemployment = positive
                elif delta_pp <= -0.10:
                    return 1
                elif -0.09 <= delta_pp <= 0.09:
                    return 0
                elif delta_pp <= 0.19:
                    return -1
                else:
                    return -2
        
        elif indicator == 'AHE':
            # Average Hourly Earnings: delta in pp
            if actual is not None and consensus is not None:
                delta_pp = actual - consensus
                
                if delta_pp <= -0.20:
                    return -2
                elif delta_pp <= -0.10:
                    return -1
                elif -0.09 <= delta_pp <= 0.09:
                    return 0
                elif delta_pp <= 0.19:
                    return 1
                else:
                    return 2
        
        elif indicator in ['ISM_MFG', 'ISM_SERVICES']:
            # ISM: delta in points
            if actual is not None and consensus is not None:
                delta_pts = actual - consensus
                
                if delta_pts < -2:
                    return -1
                elif -2 <= delta_pts <= 2:
                    return 0
                else:
                    return 1
        
        elif indicator == 'CLAIMS':
            # Claims: higher claims = negative (inverted later)
            if surprise_pct >= 20:  # 20k+ above consensus
                return -1
            elif surprise_pct <= -20:  # 20k+ below consensus  
                return 1
            else:
                return 0
        
        # Default: use surprise percentage thresholds
        if surprise_pct <= -20:
            return -2
        elif surprise_pct <= -5:
            return -1
        elif -5 <= surprise_pct <= 5:
            return 0
        elif surprise_pct <= 20:
            return 1
        else:
            return 2
    
    def _normalize_indicator_name(self, indicator: str) -> str:
        """Normaliza nome do indicador"""
        mapping = {
            'Nonfarm Payrolls': 'NFP',
            'Unemployment Rate': 'UNEMPLOYMENT',
            'Average Hourly Earnings': 'AHE',
            'ADP Employment Change': 'ADP',
            'Consumer Price Index': 'CPI',
            'Core CPI': 'CORE_CPI',
            'Personal Consumption Expenditures': 'PCE',
            'Core PCE': 'CORE_PCE',
            'ISM Manufacturing PMI': 'ISM_MFG',
            'ISM Services PMI': 'ISM_SERVICES',
            'Initial Jobless Claims': 'CLAIMS',
            'FOMC Rate Decision': 'FOMC'
        }
        
        return mapping.get(indicator, indicator)
    
    def _classify_score(self, score: float) -> str:
        """Classifica o USD score"""
        if score >= 1.5:
            return 'USD Forte'
        elif score >= 0.5:
            return 'Levemente Forte'
        elif -0.5 <= score <= 0.5:
            return 'Neutro'
        elif score >= -1.5:
            return 'Levemente Fraco'
        else:
            return 'USD Fraco'
    
    def _calculate_confidence(self, components: List[ComponentScore], score: float) -> str:
        """Calcula nível de confiança da análise"""
        if not components:
            return 'Baixa'
        
        # High confidence criteria
        if abs(score) >= 1.5 and len(components) >= 3:
            # Check for conflicting signals
            positive_components = sum(1 for c in components if c.component_score > 0)
            negative_components = sum(1 for c in components if c.component_score < 0)
            
            if min(positive_components, negative_components) <= 1:
                return 'Alta'
        
        # Medium confidence
        if len(components) >= 2:
            return 'Média'
        
        return 'Baixa'
    
    def _calculate_component_confidence(self, data_point: EconomicDataPoint, 
                                       config: Dict) -> float:
        """Calcula fator de confiança do componente"""
        confidence = 1.0
        
        # Reduce if no consensus
        if data_point.consensus is None:
            confidence *= 0.7
        
        # Reduce if very old data (placeholder logic)
        # This would check against current date in real implementation
        
        return confidence
    
    def _generate_scenarios(self, components: List[ComponentScore], 
                           score: float, classification: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Gera cenários base e alternativo"""
        
        # Base scenario (aligned with score)
        base_prob = 65
        if abs(score) >= 1.5:
            base_prob = 75
        elif abs(score) <= 0.5:
            base_prob = 55
        
        alt_prob = 100 - base_prob
        
        # Generate descriptions based on components
        inflation_components = [c for c in components if 'CPI' in c.indicator or 'PCE' in c.indicator]
        employment_components = [c for c in components if c.indicator in ['NFP', 'UNEMPLOYMENT', 'AHE', 'CLAIMS']]
        activity_components = [c for c in components if 'ISM' in c.indicator]
        
        base_description = self._generate_scenario_description(
            inflation_components, employment_components, activity_components, classification, True
        )
        
        alt_description = self._generate_scenario_description(
            inflation_components, employment_components, activity_components, classification, False
        )
        
        base_scenario = {
            'probability': base_prob,
            'description': base_description,
            'key_factors': self._extract_key_factors(components, True)
        }
        
        alternative_scenario = {
            'probability': alt_prob,
            'description': alt_description,
            'key_factors': self._extract_key_factors(components, False)
        }
        
        return base_scenario, alternative_scenario
    
    def _generate_scenario_description(self, inflation_comps: List, employment_comps: List,
                                     activity_comps: List, classification: str, is_base: bool) -> str:
        """Gera descrição do cenário"""
        
        if is_base:
            # Base scenario aligns with classification
            if 'Forte' in classification:
                return "Dados confirmam fortalecimento do USD com Fed mantendo postura hawkish"
            elif 'Fraco' in classification:
                return "Dados sugerem enfraquecimento do USD com pressão para Fed dovish"
            else:
                return "Dados mistos mantêm USD em range, aguardando catalisadores"
        else:
            # Alternative scenario (contrarian)
            if 'Forte' in classification:
                return "Dados podem ser temporários, mercado antecipa reversão dovish do Fed"
            elif 'Fraco' in classification:
                return "Fraqueza nos dados pode ser transitória, Fed mantém hawkishness"
            else:
                return "Volatilidade pode gerar breakout em qualquer direção"
    
    def _extract_key_factors(self, components: List[ComponentScore], align_with_score: bool) -> List[str]:
        """Extrai fatores-chave da análise"""
        factors = []
        
        for comp in components:
            if align_with_score:
                if comp.component_score > 0:
                    factors.append(f"{comp.indicator} surpreendeu positivamente")
                elif comp.component_score < 0:
                    factors.append(f"{comp.indicator} decepcionou")
            else:
                # Contrarian factors
                factors.append(f"Revisões futuras de {comp.indicator} podem alterar cenário")
        
        return factors[:3]  # Limit to top 3
    
    def _create_empty_analysis(self) -> USDAnalysis:
        """Cria análise vazia para casos de erro"""
        return USDAnalysis(
            timestamp=datetime.now(),
            indicators=[],
            raw_score=0,
            score=0,
            classification='Neutro',
            confidence='Baixa',
            base_scenario={'probability': 50, 'description': 'Dados insuficientes', 'key_factors': []},
            alternative_scenario={'probability': 50, 'description': 'Aguardando dados', 'key_factors': []},
            directional_suggestion='Aguardar dados confirmatórios',
            suggested_pairs=['EUR/USD', 'USD/JPY']
        )