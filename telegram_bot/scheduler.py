"""
Economic Scheduler - Sistema de agendamento inteligente
Gerencia cronogramas dos releases econômicos com timezone NY
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import calendar
import pytz
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ScheduleRule:
    """Regra de agendamento de um indicador"""
    indicator: str
    cron_expression: str
    release_time: str
    validation_required: bool
    retry_intervals: List[int]  # minutes after initial release

class EconomicScheduler:
    """Sistema de agendamento inteligente para releases econômicos"""
    
    def __init__(self):
        self.ny_tz = pytz.timezone('America/New_York')
        
        # US Market holidays (simplified - would use external calendar in production)
        self.us_holidays_2024 = [
            datetime(2024, 1, 1),   # New Year's Day
            datetime(2024, 1, 15),  # MLK Day
            datetime(2024, 2, 19),  # Presidents Day
            datetime(2024, 3, 29),  # Good Friday
            datetime(2024, 5, 27),  # Memorial Day
            datetime(2024, 6, 19),  # Juneteenth
            datetime(2024, 7, 4),   # Independence Day
            datetime(2024, 9, 2),   # Labor Day
            datetime(2024, 10, 14), # Columbus Day
            datetime(2024, 11, 11), # Veterans Day
            datetime(2024, 11, 28), # Thanksgiving
            datetime(2024, 12, 25), # Christmas
        ]
        
        # Schedule rules for each indicator
        self.schedule_rules = {
            'NFP': ScheduleRule(
                indicator='NFP',
                cron_expression='30 8 1-7 * 5',  # First Friday 08:30
                release_time='08:30',
                validation_required=True,
                retry_intervals=[3, 5, 10]
            ),
            'ADP': ScheduleRule(
                indicator='ADP',
                cron_expression='15 8 * * 3',  # Wednesday 08:15
                release_time='08:15',
                validation_required=True,
                retry_intervals=[3, 5]
            ),
            'CPI': ScheduleRule(
                indicator='CPI',
                cron_expression='30 8 10-16 * *',  # Mid-month 08:30
                release_time='08:30',
                validation_required=True,
                retry_intervals=[3, 5, 10]
            ),
            'PCE': ScheduleRule(
                indicator='PCE',
                cron_expression='30 8 25-31 * *',  # End-month 08:30
                release_time='08:30',
                validation_required=True,
                retry_intervals=[3, 5, 10]
            ),
            'ISM_MFG': ScheduleRule(
                indicator='ISM_MFG',
                cron_expression='0 10 1 * *',  # 1st of month 10:00
                release_time='10:00',
                validation_required=True,
                retry_intervals=[5, 10]
            ),
            'ISM_SERVICES': ScheduleRule(
                indicator='ISM_SERVICES',
                cron_expression='0 10 3-9 * *',  # 3rd+ business day 10:00
                release_time='10:00',
                validation_required=True,
                retry_intervals=[5, 10]
            ),
            'CLAIMS': ScheduleRule(
                indicator='CLAIMS',
                cron_expression='30 8 * * 4',  # Thursday 08:30
                release_time='08:30',
                validation_required=True,
                retry_intervals=[3, 5]
            ),
            'FOMC': ScheduleRule(
                indicator='FOMC',
                cron_expression='0 14 * * *',  # 14:00 (dynamic validation)
                release_time='14:00',
                validation_required=True,
                retry_intervals=[5, 15, 30]
            )
        }
    
    def get_next_release_date(self, indicator: str) -> Optional[datetime]:
        """Calcula próxima data de release para um indicador"""
        try:
            rule = self.schedule_rules.get(indicator)
            if not rule:
                return None
            
            now = datetime.now(self.ny_tz)
            
            if indicator == 'NFP':
                return self._get_first_friday(now)
            elif indicator == 'ADP':
                return self._get_next_weekday(now, 2)  # Wednesday = 2
            elif indicator == 'CPI':
                return self._get_mid_month_date(now)
            elif indicator == 'PCE':
                return self._get_end_month_date(now)
            elif indicator == 'ISM_MFG':
                return self._get_first_business_day(now)
            elif indicator == 'ISM_SERVICES':
                return self._get_third_business_day(now)
            elif indicator == 'CLAIMS':
                return self._get_next_weekday(now, 3)  # Thursday = 3
            elif indicator == 'FOMC':
                return self._get_next_fomc_date(now)
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao calcular próximo release para {indicator}: {e}")
            return None
    
    def should_process_today(self, indicator: str) -> bool:
        """Verifica se deve processar um indicador hoje"""
        try:
            today = datetime.now(self.ny_tz).date()
            
            # Check if it's a holiday
            if self._is_holiday(today):
                logger.info(f"Skipping {indicator} - holiday")
                return False
            
            next_release = self.get_next_release_date(indicator)
            if next_release and next_release.date() == today:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erro ao verificar processamento para {indicator}: {e}")
            return False
    
    def get_retry_schedule(self, indicator: str, initial_time: datetime) -> List[datetime]:
        """Retorna horários de retry para um indicador"""
        rule = self.schedule_rules.get(indicator)
        if not rule:
            return []
        
        retry_times = []
        for interval in rule.retry_intervals:
            retry_time = initial_time + timedelta(minutes=interval)
            retry_times.append(retry_time)
        
        return retry_times
    
    def _get_first_friday(self, from_date: datetime) -> datetime:
        """Calcula primeira sexta-feira do mês"""
        # Start with first day of current month
        first_day = from_date.replace(day=1)
        
        # If we're past the first Friday, go to next month
        first_friday = self._get_first_weekday_of_month(first_day, 4)  # Friday = 4
        
        if from_date.date() > first_friday.date():
            # Go to next month
            if first_day.month == 12:
                next_month = first_day.replace(year=first_day.year + 1, month=1)
            else:
                next_month = first_day.replace(month=first_day.month + 1)
            
            first_friday = self._get_first_weekday_of_month(next_month, 4)
        
        # Set time to 08:30
        return first_friday.replace(hour=8, minute=30, second=0, microsecond=0)
    
    def _get_first_weekday_of_month(self, date: datetime, weekday: int) -> datetime:
        """Encontra primeira ocorrência de um dia da semana no mês"""
        first_day = date.replace(day=1)
        days_ahead = weekday - first_day.weekday()
        
        if days_ahead < 0:
            days_ahead += 7
        
        return first_day + timedelta(days=days_ahead)
    
    def _get_next_weekday(self, from_date: datetime, weekday: int) -> datetime:
        """Próxima ocorrência de um dia da semana"""
        days_ahead = weekday - from_date.weekday()
        
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        
        target_date = from_date + timedelta(days=days_ahead)
        
        # Adjust for holidays
        while self._is_holiday(target_date.date()):
            target_date += timedelta(days=7)  # Next week
        
        return target_date.replace(second=0, microsecond=0)
    
    def _get_mid_month_date(self, from_date: datetime) -> datetime:
        """Data típica de CPI (meio do mês)"""
        # CPI is usually released around 10th-16th
        target_day = 13  # Typical release day
        
        if from_date.day > target_day:
            # Go to next month
            if from_date.month == 12:
                next_month = from_date.replace(year=from_date.year + 1, month=1, day=target_day)
            else:
                next_month = from_date.replace(month=from_date.month + 1, day=target_day)
            target_date = next_month
        else:
            target_date = from_date.replace(day=target_day)
        
        # Adjust to business day
        while target_date.weekday() >= 5 or self._is_holiday(target_date.date()):
            target_date += timedelta(days=1)
        
        return target_date.replace(hour=8, minute=30, second=0, microsecond=0)
    
    def _get_end_month_date(self, from_date: datetime) -> datetime:
        """Data típica de PCE (final do mês)"""
        # PCE is usually released around 27th-31st
        
        # Get last business day of month
        if from_date.month == 12:
            next_month = from_date.replace(year=from_date.year + 1, month=1, day=1)
        else:
            next_month = from_date.replace(month=from_date.month + 1, day=1)
        
        # Go back to last day of current month
        last_day = next_month - timedelta(days=1)
        
        # Find last business day
        while last_day.weekday() >= 5 or self._is_holiday(last_day.date()):
            last_day -= timedelta(days=1)
        
        # PCE is typically released 3-4 business days before end of month
        pce_date = last_day - timedelta(days=3)
        
        # Adjust to business day
        while pce_date.weekday() >= 5 or self._is_holiday(pce_date.date()):
            pce_date += timedelta(days=1)
        
        if from_date.date() > pce_date.date():
            # Calculate for next month
            return self._get_end_month_date(next_month)
        
        return pce_date.replace(hour=8, minute=30, second=0, microsecond=0)
    
    def _get_first_business_day(self, from_date: datetime) -> datetime:
        """Primeiro dia útil do mês"""
        first_day = from_date.replace(day=1)
        
        if from_date.day > 1:
            # Go to next month
            if first_day.month == 12:
                first_day = first_day.replace(year=first_day.year + 1, month=1)
            else:
                first_day = first_day.replace(month=first_day.month + 1)
        
        # Adjust to business day
        while first_day.weekday() >= 5 or self._is_holiday(first_day.date()):
            first_day += timedelta(days=1)
        
        return first_day.replace(hour=10, minute=0, second=0, microsecond=0)
    
    def _get_third_business_day(self, from_date: datetime) -> datetime:
        """Terceiro dia útil do mês"""
        first_business = self._get_first_business_day(from_date)
        
        business_days_count = 1
        current_date = first_business
        
        while business_days_count < 3:
            current_date += timedelta(days=1)
            
            if current_date.weekday() < 5 and not self._is_holiday(current_date.date()):
                business_days_count += 1
        
        return current_date.replace(hour=10, minute=0, second=0, microsecond=0)
    
    def _get_next_fomc_date(self, from_date: datetime) -> Optional[datetime]:
        """Próxima data do FOMC (aproximada)"""
        # FOMC meets ~8 times per year, roughly every 6-8 weeks
        # This is a simplified approximation - in production would use FRED calendar
        
        fomc_meetings_2024 = [
            datetime(2024, 1, 31, 14, 0),   # Jan 30-31
            datetime(2024, 3, 20, 14, 0),   # Mar 19-20
            datetime(2024, 5, 1, 14, 0),    # Apr 30-May 1
            datetime(2024, 6, 12, 14, 0),   # Jun 11-12
            datetime(2024, 7, 31, 14, 0),   # Jul 30-31
            datetime(2024, 9, 18, 14, 0),   # Sep 17-18
            datetime(2024, 11, 7, 14, 0),   # Nov 6-7
            datetime(2024, 12, 18, 14, 0),  # Dec 17-18
        ]
        
        # Find next meeting
        for meeting_date in fomc_meetings_2024:
            meeting_date_ny = self.ny_tz.localize(meeting_date)
            if meeting_date_ny > from_date:
                return meeting_date_ny
        
        # If no more meetings this year, return None (would calculate next year in production)
        return None
    
    def _is_holiday(self, date) -> bool:
        """Verifica se é feriado nos EUA"""
        if isinstance(date, datetime):
            date = date.date()
        
        for holiday in self.us_holidays_2024:
            if holiday.date() == date:
                return True
        
        return False
    
    def get_all_upcoming_releases(self, days_ahead: int = 14) -> List[Dict]:
        """Retorna todos os próximos releases em ordem cronológica"""
        upcoming = []
        
        for indicator in self.schedule_rules.keys():
            next_date = self.get_next_release_date(indicator)
            if next_date:
                rule = self.schedule_rules[indicator]
                upcoming.append({
                    'indicator': indicator,
                    'date': next_date,
                    'time': rule.release_time,
                    'cron': rule.cron_expression,
                    'validation_required': rule.validation_required
                })
        
        # Sort by date
        upcoming.sort(key=lambda x: x['date'])
        
        # Filter by date range
        cutoff = datetime.now(self.ny_tz) + timedelta(days=days_ahead)
        upcoming = [item for item in upcoming if item['date'] <= cutoff]
        
        return upcoming